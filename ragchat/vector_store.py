import os
import numpy as np
import faiss
from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
EMBED_MODEL = "text-embedding-ada-002"

def get_embeddings(texts):
    result = client.embeddings.create(input=texts, model=EMBED_MODEL)
    return [np.array(e.embedding, dtype='float32') for e in result.data]

class ManualVectorStore:
    def __init__(self, txt_path):
        self.txt_path = txt_path
        self.chunks = self.split_text(self.load_text())
        self.embeddings = get_embeddings(self.chunks)
        self.index = faiss.IndexFlatL2(len(self.embeddings[0]))
        self.index.add(np.array(self.embeddings))

    def load_text(self):
        with open(self.txt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def split_text(self, text, chunk_size=500):
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    def search(self, query, k=3):
        query_vec = get_embeddings([query])[0]
        D, I = self.index.search(np.array([query_vec]), k)
        return [self.chunks[i] for i in I[0]]
