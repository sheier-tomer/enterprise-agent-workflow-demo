"""
Pytest fixtures and configuration for testing.
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.db.base import Base
from app.db.models import Customer, Transaction, PolicyDocument
from app.main import create_app
from app.demo_data.customers import generate_customers
from app.demo_data.transactions import generate_transactions
from app.demo_data.policies import generate_policy_documents


# Override database URL for testing (use in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def seeded_session(test_session: AsyncSession) -> AsyncSession:
    """Create session with seeded test data."""
    # Generate and add test data
    customers = generate_customers(count=10)
    test_session.add_all(customers)
    await test_session.flush()
    
    transactions = generate_transactions(customers=customers, total_count=100)
    test_session.add_all(transactions)
    await test_session.flush()
    
    policies = generate_policy_documents()
    test_session.add_all(policies)
    await test_session.flush()
    
    await test_session.commit()
    
    return test_session


@pytest_asyncio.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    app = create_app()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def test_customer(test_session: AsyncSession) -> Customer:
    """Create a single test customer."""
    customer = Customer(
        name="Test Customer",
        email="test@example.com",
        account_type="checking",
    )
    test_session.add(customer)
    await test_session.commit()
    await test_session.refresh(customer)
    return customer
