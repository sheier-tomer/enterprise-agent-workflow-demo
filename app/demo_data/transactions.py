"""
Synthetic transaction data generator with injected anomalies.
Creates realistic transaction patterns with ~5% anomalies.
"""

import random
from datetime import datetime, timedelta
from uuid import uuid4

from faker import Faker

from app.db.models import Customer, Transaction

fake = Faker()
Faker.seed(42)  # Consistent seed for reproducibility


# Transaction categories with typical amount ranges
TRANSACTION_CATEGORIES = {
    "groceries": (15.0, 150.0),
    "restaurants": (20.0, 100.0),
    "gas": (30.0, 80.0),
    "utilities": (50.0, 200.0),
    "entertainment": (10.0, 100.0),
    "shopping": (25.0, 300.0),
    "travel": (100.0, 500.0),
    "healthcare": (50.0, 400.0),
    "insurance": (100.0, 500.0),
    "online_services": (5.0, 50.0),
}

# Merchants by category
MERCHANTS = {
    "groceries": ["FreshMart", "GreenGrocer", "QuickStop Market", "Whole Foods Co"],
    "restaurants": ["The Local Bistro", "Pizza Palace", "Sushi Express", "Cafe Corner"],
    "gas": ["Shell Station", "QuickFuel", "EcoGas", "MainStreet Fuel"],
    "utilities": ["City Power Co", "Water Works", "Internet Services Inc", "Gas Company"],
    "entertainment": ["Cinema Plus", "StreamFlix", "GameZone", "Concert Hall"],
    "shopping": ["MegaMart", "Fashion Outlet", "Tech Store", "Home Goods"],
    "travel": ["Skyline Airlines", "Grand Hotel", "RentACar Pro", "Travel Agency"],
    "healthcare": ["City Medical Center", "Pharmacy Plus", "Dental Care", "Vision Center"],
    "insurance": ["SafeGuard Insurance", "Health Shield", "Auto Protect", "Life Secure"],
    "online_services": ["CloudStorage Co", "Software Suite", "Music Streaming", "News Portal"],
}


def generate_transactions(
    customers: list[Customer],
    total_count: int = 500,
    anomaly_rate: float = 0.05,
) -> list[Transaction]:
    """
    Generate synthetic transaction records with injected anomalies.
    
    Anomalies include:
    - Unusually large amounts (10x typical)
    - Transactions at odd hours (2-5 AM)
    - Foreign merchant patterns
    - High frequency in short time
    
    Args:
        customers: List of customer records to attach transactions to
        total_count: Total number of transactions to generate
        anomaly_rate: Fraction of transactions that should be anomalies (default 5%)
        
    Returns:
        List of Transaction model instances
    """
    transactions = []
    num_anomalies = int(total_count * anomaly_rate)
    
    # Generate normal transactions
    for i in range(total_count - num_anomalies):
        customer = random.choice(customers)
        category = random.choice(list(TRANSACTION_CATEGORIES.keys()))
        min_amount, max_amount = TRANSACTION_CATEGORIES[category]
        
        amount = round(random.uniform(min_amount, max_amount), 2)
        merchant = random.choice(MERCHANTS[category])
        
        # Random timestamp within last 90 days, during normal hours (6 AM - 11 PM)
        days_ago = random.randint(0, 90)
        hour = random.randint(6, 23)
        minute = random.randint(0, 59)
        
        timestamp = datetime.now() - timedelta(days=days_ago, hours=hour, minutes=minute)
        
        transaction = Transaction(
            id=uuid4(),
            customer_id=customer.id,
            amount=amount,
            currency="USD",
            merchant=merchant,
            category=category,
            timestamp=timestamp,
            is_anomaly=False,
        )
        
        transactions.append(transaction)
    
    # Generate anomalous transactions
    for i in range(num_anomalies):
        customer = random.choice(customers)
        anomaly_type = random.choice(["large_amount", "odd_hour", "foreign", "high_frequency"])
        
        category = random.choice(list(TRANSACTION_CATEGORIES.keys()))
        min_amount, max_amount = TRANSACTION_CATEGORIES[category]
        
        if anomaly_type == "large_amount":
            # 10x typical amount
            amount = round(random.uniform(min_amount * 10, max_amount * 15), 2)
            merchant = random.choice(MERCHANTS[category])
            hour = random.randint(6, 23)
            
        elif anomaly_type == "odd_hour":
            # Transaction at 2-5 AM
            amount = round(random.uniform(min_amount, max_amount), 2)
            merchant = random.choice(MERCHANTS[category])
            hour = random.randint(2, 5)
            
        elif anomaly_type == "foreign":
            # Foreign merchant (prefixed with country code)
            amount = round(random.uniform(min_amount * 2, max_amount * 3), 2)
            country = random.choice(["UK", "FR", "DE", "JP", "AU"])
            merchant = f"{country}-{random.choice(MERCHANTS[category])}"
            hour = random.randint(6, 23)
            
        else:  # high_frequency
            # Multiple transactions in short time (this is just one of them)
            amount = round(random.uniform(min_amount, max_amount * 0.5), 2)
            merchant = random.choice(MERCHANTS[category])
            hour = random.randint(6, 23)
        
        days_ago = random.randint(0, 90)
        minute = random.randint(0, 59)
        timestamp = datetime.now() - timedelta(days=days_ago, hours=hour, minutes=minute)
        
        transaction = Transaction(
            id=uuid4(),
            customer_id=customer.id,
            amount=amount,
            currency="USD",
            merchant=merchant,
            category=category,
            timestamp=timestamp,
            is_anomaly=True,  # Mark as anomaly for demo purposes
        )
        
        transactions.append(transaction)
    
    # Sort by timestamp
    transactions.sort(key=lambda t: t.timestamp)
    
    return transactions
