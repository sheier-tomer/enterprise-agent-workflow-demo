"""
RAG (Retrieval-Augmented Generation) module.
Provides embedding generation, vector similarity search, and document indexing.
"""

from app.rag.embeddings import get_embedding_provider
from app.rag.retriever import retrieve_relevant_policies
from app.rag.indexer import index_policy_documents

__all__ = [
    "get_embedding_provider",
    "retrieve_relevant_policies",
    "index_policy_documents",
]
