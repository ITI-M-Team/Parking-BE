from .vector_store import ManualVectorStore
from openai import OpenAI
import os

store = ManualVectorStore(os.path.join("ragchat", "data", "parking_manual.txt"))
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

def ask_with_context(question):
    chunks = store.search(question)
    context = "\n\n".join(chunks)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant for the Smart Parking App user manual. Provide professional, clearly formatted answers."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ],
        max_tokens=500
    )
    return response.choices[0].message.content.strip()
