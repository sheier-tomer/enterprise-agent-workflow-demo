"""
Synthetic customer data generator.
Creates fake customers with realistic attributes.
"""

import random
from datetime import datetime, timedelta
from uuid import uuid4

from faker import Faker

from app.db.models import Customer

fake = Faker()
Faker.seed(42)  # Consistent seed for reproducibility


ACCOUNT_TYPES = ["checking", "savings", "business"]


def generate_customers(count: int = 50) -> list[Customer]:
    """
    Generate synthetic customer records.
    
    Args:
        count: Number of customers to generate
        
    Returns:
        List of Customer model instances
    """
    customers = []
    
    for i in range(count):
        # Generate a fake person
        name = fake.name()
        email = fake.unique.email()
        account_type = random.choice(ACCOUNT_TYPES)
        
        # Random creation date within last 2 years
        created_at = datetime.now() - timedelta(days=random.randint(0, 730))
        
        customer = Customer(
            id=uuid4(),
            name=name,
            email=email,
            account_type=account_type,
            created_at=created_at,
        )
        
        customers.append(customer)
    
    return customers
