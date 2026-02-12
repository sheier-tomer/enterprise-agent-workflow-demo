"""
Policy document loader utilities.
Provides functions to load and retrieve policy documents.
"""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PolicyDocument

logger = logging.getLogger(__name__)


async def load_policy_by_id(
    session: AsyncSession,
    policy_id: UUID,
) -> Optional[PolicyDocument]:
    """
    Load a single policy document by ID.
    
    Args:
        session: Database session
        policy_id: Policy document UUID
        
    Returns:
        PolicyDocument instance or None if not found
    """
    result = await session.execute(
        select(PolicyDocument).where(PolicyDocument.id == policy_id)
    )
    
    return result.scalars().first()


async def load_policies_by_category(
    session: AsyncSession,
    category: str,
    limit: int = 10,
) -> List[PolicyDocument]:
    """
    Load policy documents by category.
    
    Args:
        session: Database session
        category: Policy category to filter by
        limit: Maximum number of policies to return
        
    Returns:
        List of PolicyDocument instances
    """
    result = await session.execute(
        select(PolicyDocument)
        .where(PolicyDocument.category == category)
        .limit(limit)
    )
    
    return list(result.scalars().all())


async def load_all_policies(
    session: AsyncSession,
    limit: int = 100,
) -> List[PolicyDocument]:
    """
    Load all policy documents.
    
    Args:
        session: Database session
        limit: Maximum number of policies to return
        
    Returns:
        List of PolicyDocument instances
    """
    result = await session.execute(
        select(PolicyDocument).limit(limit)
    )
    
    return list(result.scalars().all())


async def get_policy_categories(session: AsyncSession) -> List[str]:
    """
    Get all distinct policy categories.
    
    Args:
        session: Database session
        
    Returns:
        List of category names
    """
    result = await session.execute(
        select(PolicyDocument.category).distinct()
    )
    
    return [row[0] for row in result.fetchall()]
