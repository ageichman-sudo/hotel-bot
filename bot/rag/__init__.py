# bot/rag/__init__.py
from .search import find_relevant_faq_entries, rag_ask_ollama

__all__ = ["find_relevant_faq_entries", "rag_ask_ollama"]