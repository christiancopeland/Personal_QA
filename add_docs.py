import chromadb
from chromadb.config import Settings
from uuid import uuid4
import os


def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as infile:
        return infile.read()



if __name__ == '__main__':
    persist_directory = "chromadb"
    chroma_client = chromadb.PersistentClient(path=persist_directory)
    collection = chroma_client.get_or_create_collection(name="csharp_docs")

    articles = os.listdir("c_sharp_docs/")
    print(f"articles\n")

    for article in articles:
        text = open_file("c_sharp_docs/%s" % article)
        new_id = str(uuid4())
        collection.add(documents=[text],ids=[new_id])

    results = collection.query(query_texts="coroutines", n_results=1)
    print(f"Results: {results['documents'][0][0]}")