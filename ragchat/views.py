from rest_framework.decorators import api_view
from rest_framework.response import Response
from .utils import ask_with_context

@api_view(["POST"])
def rag_chat(request):
    question = request.data.get("question")
    if not question:
        return Response({"error": "Missing 'question'"}, status=400)
    answer = ask_with_context(question)
    return Response({"answer": answer})
