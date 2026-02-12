"""
Policy document indexing for RAG.
Generates and stores embeddings for policy documents.
"""

import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PolicyDocument
from app.rag.embeddings import get_embedding_provider

logger = logging.getLogger(__name__)


async def index_policy_documents(
    session: AsyncSession,
    batch_size: int = 10,
) -> int:
    """
    Generate and store embeddings for all policy documents without embeddings.
    
    This function:
    1. Finds all PolicyDocuments with null embeddings
    2. Generates embeddings using the configured provider
    3. Updates the documents with their embeddings
    4. Commits the changes
    
    Args:
        session: Database session
        batch_size: Number of documents to process in each batch
        
    Returns:
        Number of documents indexed
    """
    # Find documents without embeddings
    result = await session.execute(
        select(PolicyDocument).where(PolicyDocument.embedding.is_(None))
    )
    policies = list(result.scalars().all())
    
    if not policies:
        logger.info("All policy documents already have embeddings")
        return 0
    
    logger.info(f"Indexing {len(policies)} policy documents...")
    
    # Get embedding provider
    embedding_provider = get_embedding_provider()
    
    # Process in batches
    indexed_count = 0
    for i in range(0, len(policies), batch_size):
        batch = policies[i:i + batch_size]
        
        # Generate embeddings for batch
        texts = [
            f"{policy.title}\n\n{policy.content}"
            for policy in batch
        ]
        
        try:
            embeddings = await embedding_provider.embed_batch(texts)
            
            # Update policy documents with embeddings
            for policy, embedding in zip(batch, embeddings):
                # pgvector expects the embedding as a list
                policy.embedding = embedding
            
            # Flush to database
            await session.flush()
            indexed_count += len(batch)
            
            logger.info(f"Indexed batch {i//batch_size + 1}: {len(batch)} documents")
            
        except Exception as e:
            logger.error(f"Error indexing batch {i//batch_size + 1}: {e}")
            # Continue with next batch
            continue
    
    # Commit all changes
    await session.commit()
    
    logger.info(f"Successfully indexed {indexed_count} policy documents")
    
    return indexed_count


async def reindex_all_policies(
    session: AsyncSession,
    batch_size: int = 10,
) -> int:
    """
    Regenerate embeddings for ALL policy documents (even those with existing embeddings).
    
    Useful when changing embedding models or dimensions.
    
    Args:
        session: Database session
        batch_size: Number of documents to process in each batch
        
    Returns:
        Number of documents reindexed
    """
    # Get all policy documents
    result = await session.execute(select(PolicyDocument))
    policies = list(result.scalars().all())
    
    if not policies:
        logger.info("No policy documents to reindex")
        return 0
    
    logger.info(f"Reindexing {len(policies)} policy documents...")
    
    # Clear existing embeddings
    for policy in policies:
        policy.embedding = None
    
    await session.flush()
    
    # Use the regular indexing function
    return await index_policy_documents(session, batch_size)


async def get_indexing_status(session: AsyncSession) -> dict:
    """
    Get the current indexing status of policy documents.
    
    Args:
        session: Database session
        
    Returns:
        Dictionary with indexing statistics
    """
    # Total policies
    total_result = await session.execute(select(PolicyDocument))
    total = len(list(total_result.scalars().all()))
    
    # Policies with embeddings
    indexed_result = await session.execute(
        select(PolicyDocument).where(PolicyDocument.embedding.is_not(None))
    )
    indexed = len(list(indexed_result.scalars().all()))
    
    # Policies without embeddings
    unindexed = total - indexed
    
    return {
        "total_policies": total,
        "indexed": indexed,
        "unindexed": unindexed,
        "percentage_indexed": (indexed / total * 100) if total > 0 else 0,
    }
