import chromadb
from chromadb.config import Settings
import yaml
from time import time, sleep
from uuid import uuid4
import requests
import json


def save_yaml(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as file:
        yaml.dump(data, file, allow_unicode=True)


def save_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(content)


def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as infile:
        return infile.read()


def call_model(user_message):
    retry = 0
    max_retry = 7
    # conversation = list()
    model = "llama3.1:8b"
    # user_message = input("\n\nSend a message: ")
    # conversation.append({"role": "user", "content": user_message})
    stream = False
    url = "http://localhost:11434/api/chat"

    headers = {
        "Content-Type": "application/json"
        }

    data = {}
    data["model"] = model
    data["messages"] = user_message
    data["stream"] = stream

    try:
        request_response = requests.post(url=url, headers=headers, data=json.dumps(data))
        #print(f"Response code: {request_response}")
        if request_response.status_code == 200:
            response_text = request_response.text
            #print(response_text)
            data = json.loads(response_text)
            #print(f"DEBUG\nData: {data}")
            response = data["message"]["content"]
            save_yaml('api_logs/convo_%s.yaml' % time(), response)
            # if response['usage']['total_tokens'] >= 7000:
            #     a = messages.pop(1)
    except Exception as e:
        print(f'\n\nError communicating with Ollama: "{e}"')
        if 'maximum context length' in str(e):
            a = messages.pop(1)
            print('\n\n DEBUG: Trimming oldest message')
            # continue
        retry += 1
        if retry >= max_retry:
            print(f"\n\nExiting due to excessive errors in API: {e}")
            exit(1)
        print(f'\n\nRetrying in {2 ** (retry - 1) * 5} seconds...')
        sleep(2 ** (retry - 1) * 5)      
    return response


def kb_create(main_scratchpad):
    kb_convo_string = ''
    kb_convo = list()
    kb_convo.append({'role': 'system', 'content': open_file('./system_messages/system_instantiate_new_kb.txt')})
    kb_convo.append({'role': 'user', 'content': main_scratchpad})
    kb_convo.append({"role": "assistant", "content": ""})
    kb_convo_string = stringify_convo_json(kb_convo)
    #print(f"Input to model: {kb_convo}")
    article = call_model(kb_convo)
    #print(f"DEBUG: \nArticle created: {article}")
    new_id = str(uuid4())
    collection.add(documents=[article],ids=[new_id])
    save_file('db_logs/log_%s_add.txt' % time(), 'Added document %s:\n%s' % (new_id, article))


def kb_split(article):
    kb_len = len(article.split(' '))
    if kb_len > 1000:
        kb_convo = list()
        kb_convo.append({'role': 'system', 'content': open_file('./system_messages/system_split_kb.txt')})
        kb_convo.append({'role': 'user', 'content': article})
        kb_convo_string = stringify_convo_json(kb_convo)
        #print(f"Input to model: {kb_convo}")
        articles = call_model(kb_convo).split('ARTICLE 2:')
        print(f"DEBUG: \nArticles: {articles}\n")
        a1 = articles[0].replace('ARTICLE 1:', '').strip()
        print(f"Article 1 {a1}")
        a2 = articles[1].strip()
        print(f"Article 2 {a2}")
        collection.update(ids=[kb_id],documents=[a1])
        new_id = str(uuid4())
        collection.add(documents=[a2],ids=[new_id])
        save_file('db_logs/log_%s_split.txt' % time(), 'Split document %s, added %s:\n%s\n\n%s' % (kb_id, new_id, a1, a2))


def kb_update(kb, main_scratchpad, collection):
    kb_convo_string = ''
    kb_convo = list()
    kb_convo.append({'role': 'system', 'content': open_file('./system_messages/system_update_existing_kb.txt').replace('<<KB>>', kb)})
    kb_convo.append({'role': 'user', 'content': main_scratchpad})
    kb_convo_string = stringify_convo_json(kb_convo)
    article = call_model(kb_convo)
    collection.update(ids=[kb_id],documents=[article])
    save_file('db_logs/log_%s_update.txt' % time(), 'Updated document %s:\n%s' % (kb_id, article))
    return article


def get_current_user_profile():
    current_profile = open_file('./system_messages/user_profile.txt')
    return current_profile

def update_user_profile():
    current_profile = get_current_user_profile()
    print('\n\nUpdating user profile...')
    profile_length = len(current_profile.split(' '))
    profile_conversation = list()
    profile_conversation.append({'role': 'system', 'content': open_file('./system_messages/system_update_user_profile.txt').replace('<<UPD>>', current_profile).replace('<<WORDS>>', str(profile_length))})
    profile_conversation.append({'role': 'user', 'content': user_scratchpad})
    profile_conversation_string = stringify_convo_json(profile_conversation)
        
    profile = call_model(profile_conversation)
    save_file('./system_messages/user_profile.txt', profile)

def update_scratchpad(messages, pad, max):
    if len(messages) > max:
        messages.pop(0)
    pad = '\n\n'.join(messages).strip()
    return pad


def stringify_convo_json(role_content_json):
    for item in role_content_json:
        stringified_json = ''.join(f"Role: {item['role']}, Content: {item['content']}")
    return stringified_json




if __name__ == '__main__':
    # instantiate ChromaDB
    persist_directory = "chromadb"
    chroma_client = chromadb.PersistentClient(path=persist_directory)
    collection = chroma_client.get_or_create_collection(name="c_sharp_docs")


    # instantiate chatbot
    conversation_string = ''
    conversation = list()
    conversation.append({'role': 'system', 'content': open_file('./system_messages/system_default.txt')})
    user_messages = list()
    all_messages = list()
    main_scratchpad = ''
    user_scratchpad = ''
    
    while True:
        # get user input
        text = input('\n\nUSER: ')
        user_messages.append(text)
        all_messages.append('USER: %s' % text)
        conversation.append({'role': 'user', 'content': text})
        save_file('chat_logs/chat_%s_user.txt' % time(), text)


        # update main scratchpad
        main_scratchpad = update_scratchpad(messages=all_messages, pad=main_scratchpad, max=5)

        # search KB, update default system
        current_profile = get_current_user_profile()
        kb = 'No KB articles yet'
        if collection.count() > 0:
            #Example results: {'ids': [['7d6d594a-5871-4707-8b5a-536cb04ebbe4']], 'distances': [[1.204876888885644]], 'metadatas': [[None]], 'embeddings': None, 'documents': [['USER: como vai?']], 'uris': None, 'data': None, 'included': ['metadatas', 'documents', 'distances']}
            results = collection.query(query_texts=[main_scratchpad], n_results=1)
            kb = results['documents'][0][0]
            print('\n\nDEBUG: Found results %s' % results)
        default_system = open_file('./system_messages/system_default.txt').replace('<<PROFILE>>', current_profile).replace('<<KB>>', kb)
        #print('SYSTEM: %s' % default_system)
        conversation[0]['content'] = default_system
        conversation_string = stringify_convo_json(conversation)


        # generate a response
        #print(f"DEBUG:\nPrompt: {conversation}")
        response = call_model(conversation)
        # print(f"Response: {response}")
        save_file('chat_logs/chat_%s_chatbot.txt' % time(), response)
        conversation.append({'role': 'assistant', 'content': response})
        all_messages.append('CHATBOT: %s' % response)
        print('\n\nCHATBOT: %s' % response)


        # update user scratchpad
        user_scratchpad = update_scratchpad(messages=user_messages, pad=user_scratchpad, max=3)

        # update user profile
        update_user_profile()

        # update main scratchpad
        main_scratchpad = update_scratchpad(messages=all_messages, pad=main_scratchpad, max=5)

        # Update the knowledge base
        print('\n\nUpdating KB...')
        if collection.count() == 0:
            # yay first KB!
            kb_create(main_scratchpad)

        else:
            results = collection.query(query_texts=[main_scratchpad], n_results=1)
            kb = results['documents'][0][0]
            kb_id = results['ids'][0][0]

            # Expand current KB
            article = kb_update(kb, main_scratchpad, collection)

            # Split KB if too large
            kb_split(article)

        # chroma_client.persist()