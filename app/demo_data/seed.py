"""
Master seeding orchestrator.
Coordinates generation and insertion of all synthetic data.
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Customer, Transaction, PolicyDocument
from app.demo_data.customers import generate_customers
from app.demo_data.transactions import generate_transactions
from app.demo_data.policies import generate_policy_documents

logger = logging.getLogger(__name__)


async def seed_database(session: AsyncSession) -> dict[str, int]:
    """
    Seed the database with synthetic data.
    
    This function:
    1. Checks if data already exists
    2. Generates synthetic customers
    3. Generates synthetic transactions
    4. Generates synthetic policy documents
    5. Inserts all data into the database
    
    Args:
        session: Database session
        
    Returns:
        Dictionary with counts of created records
    """
    # Check if database already has data
    existing_customers = await session.execute(select(Customer))
    if existing_customers.scalars().first() is not None:
        logger.info("Database already contains data, skipping seeding")
        return {"customers": 0, "transactions": 0, "policies": 0}
    
    logger.info("Starting database seeding...")
    
    # Generate customers
    logger.info(f"Generating {settings.seed_customers_count} customers...")
    customers = generate_customers(count=settings.seed_customers_count)
    session.add_all(customers)
    await session.flush()  # Flush to get customer IDs
    logger.info(f"Created {len(customers)} customers")
    
    # Generate transactions
    logger.info(f"Generating {settings.seed_transactions_count} transactions...")
    transactions = generate_transactions(
        customers=customers,
        total_count=settings.seed_transactions_count,
        anomaly_rate=0.05,
    )
    session.add_all(transactions)
    await session.flush()
    logger.info(f"Created {len(transactions)} transactions ({sum(1 for t in transactions if t.is_anomaly)} anomalies)")
    
    # Generate policy documents
    logger.info(f"Generating policy documents...")
    policies = generate_policy_documents()
    session.add_all(policies)
    await session.flush()
    logger.info(f"Created {len(policies)} policy documents")
    
    # Commit all changes
    await session.commit()
    
    logger.info("Database seeding completed successfully")
    
    return {
        "customers": len(customers),
        "transactions": len(transactions),
        "policies": len(policies),
    }


async def check_seed_status(session: AsyncSession) -> dict[str, int]:
    """
    Check the current seed status of the database.
    
    Args:
        session: Database session
        
    Returns:
        Dictionary with current counts of records
    """
    customer_count = (await session.execute(select(Customer))).scalars().all()
    transaction_count = (await session.execute(select(Transaction))).scalars().all()
    policy_count = (await session.execute(select(PolicyDocument))).scalars().all()
    
    return {
        "customers": len(customer_count),
        "transactions": len(transaction_count),
        "policies": len(policy_count),
    }
