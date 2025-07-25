from django.urls import path
from .views import rag_chat

urlpatterns = [
    path("ask/", rag_chat),
]
