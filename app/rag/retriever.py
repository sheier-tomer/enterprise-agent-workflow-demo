"""
Vector similarity search using pgvector.
Retrieves relevant policy documents based on semantic similarity.
"""

import logging
from typing import List, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PolicyDocument
from app.rag.embeddings import get_embedding_provider

logger = logging.getLogger(__name__)


async def retrieve_relevant_policies(
    session: AsyncSession,
    query: str,
    top_k: int = 3,
    category_filter: Optional[str] = None,
) -> List[PolicyDocument]:
    """
    Retrieve relevant policy documents using vector similarity search.
    
    Uses cosine similarity with pgvector to find the most relevant documents
    based on the query text.
    
    Args:
        session: Database session
        query: Query text to search for
        top_k: Number of top results to return (default: 3)
        category_filter: Optional category to filter results
        
    Returns:
        List of PolicyDocument instances, ordered by relevance
    """
    # Generate embedding for query
    embedding_provider = get_embedding_provider()
    query_embedding = await embedding_provider.embed_text(query)
    
    # Build query with vector similarity
    # Using cosine distance (1 - cosine_similarity) with <=> operator
    stmt = select(PolicyDocument)
    
    if category_filter:
        stmt = stmt.where(PolicyDocument.category == category_filter)
    
    # Order by cosine distance (lower is more similar)
    stmt = stmt.order_by(
        text(f"embedding <=> CAST(:query_vector AS vector)")
    ).limit(top_k)
    
    # Execute query with embedding as parameter
    # Convert list to string format expected by pgvector: '[1,2,3]'
    vector_str = f"[{','.join(map(str, query_embedding))}]"
    
    result = await session.execute(
        stmt,
        {"query_vector": vector_str}
    )
    
    policies = list(result.scalars().all())
    
    logger.info(
        f"Retrieved {len(policies)} policies for query (top_k={top_k}, "
        f"category={category_filter or 'all'})"
    )
    
    return policies


async def retrieve_policies_by_category(
    session: AsyncSession,
    category: str,
    limit: int = 5,
) -> List[PolicyDocument]:
    """
    Retrieve policy documents by category (no vector search).
    
    Args:
        session: Database session
        category: Category to filter by
        limit: Maximum number of results
        
    Returns:
        List of PolicyDocument instances
    """
    result = await session.execute(
        select(PolicyDocument)
        .where(PolicyDocument.category == category)
        .limit(limit)
    )
    
    return list(result.scalars().all())


async def get_all_policy_categories(session: AsyncSession) -> List[str]:
    """
    Get all distinct policy categories in the database.
    
    Args:
        session: Database session
        
    Returns:
        List of category names
    """
    result = await session.execute(
        select(PolicyDocument.category).distinct()
    )
    
    return [row[0] for row in result.fetchall()]
