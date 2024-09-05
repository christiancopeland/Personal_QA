import chromadb
from chromadb.config import Settings
from uuid import uuid4
import os
import argparse

def get_args():
    parser = argparse.ArgumentParser() 
    parser.add_argument("-p", "--path", dest="docsPath", help="Specify target path to folder of docs you want to upload")

    args = parser.parse_args()
    return args


def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as infile:
        return infile.read()



if __name__ == '__main__':

    args = get_args()
    docs_path = args.docsPath

    persist_directory = "chromadb"
    chroma_client = chromadb.PersistentClient(path=persist_directory)
    collection = chroma_client.get_or_create_collection(name="csharp_docs")

    if docs_path:
        try:
            articles = os.listdir(f"{docs_path}")
            print(f"{articles}\n")
        except FileNotFoundError as e:
            print(f"You may not have formatted the path to '{docs_path}' correctly.")
            print(f"Error: {e}\n")
        except Exception as e:
            print(f"Error {e}")

    articles = os.listdir("c_sharp_docs/")
    print(f"Articles to upload: {articles}\n")

    # for article in articles:
    #     text = open_file("c_sharp_docs/%s" % article)
    #     new_id = str(uuid4())
    #     collection.add(documents=[text],ids=[new_id])

    # results = collection.query(query_texts="coroutines", n_results=1)
    # print(f"Results: {results['documents'][0][0]}")