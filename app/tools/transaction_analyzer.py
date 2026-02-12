"""
Transaction analyzer tool.
Analyzes customer transactions and generates statistical summaries.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Transaction

logger = logging.getLogger(__name__)


class AnalyzeTransactionsInput(BaseModel):
    """Input schema for transaction analysis."""

    customer_id: str = Field(description="Customer UUID to analyze")
    window_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days to look back",
    )
    include_anomalies: bool = Field(
        default=True,
        description="Include transactions marked as anomalies",
    )


class TimeRange(BaseModel):
    """Time range for transaction analysis."""

    start: datetime
    end: datetime
    days: int


class AnalyzeTransactionsOutput(BaseModel):
    """Output schema for transaction analysis."""

    customer_id: str
    transaction_count: int
    total_amount: float
    average_amount: float
    min_amount: float
    max_amount: float
    currency: str
    category_breakdown: dict[str, float]
    merchant_list: List[str]
    time_range: TimeRange
    anomaly_count: int


class TransactionAnalyzer:
    """
    Tool for analyzing customer transaction patterns.
    
    Provides statistical analysis of transactions including:
    - Total/average/min/max amounts
    - Category breakdown
    - Merchant list
    - Anomaly count
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, input_data: dict) -> dict:
        """
        Execute transaction analysis.
        
        Args:
            input_data: Dictionary matching AnalyzeTransactionsInput schema
            
        Returns:
            Dictionary matching AnalyzeTransactionsOutput schema
        """
        # Validate input
        validated_input = AnalyzeTransactionsInput.model_validate(input_data)
        
        # Parse customer ID
        customer_id = UUID(validated_input.customer_id)
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=validated_input.window_days)
        
        # Query transactions
        stmt = select(Transaction).where(
            Transaction.customer_id == customer_id,
            Transaction.timestamp >= start_time,
            Transaction.timestamp <= end_time,
        )
        
        if not validated_input.include_anomalies:
            stmt = stmt.where(Transaction.is_anomaly == False)
        
        result = await self.session.execute(stmt)
        transactions = list(result.scalars().all())
        
        if not transactions:
            # Return empty analysis
            output = AnalyzeTransactionsOutput(
                customer_id=validated_input.customer_id,
                transaction_count=0,
                total_amount=0.0,
                average_amount=0.0,
                min_amount=0.0,
                max_amount=0.0,
                currency="USD",
                category_breakdown={},
                merchant_list=[],
                time_range=TimeRange(
                    start=start_time,
                    end=end_time,
                    days=validated_input.window_days,
                ),
                anomaly_count=0,
            )
        else:
            # Calculate statistics
            amounts = [t.amount for t in transactions]
            total_amount = sum(amounts)
            
            # Category breakdown
            category_breakdown = {}
            for t in transactions:
                category_breakdown[t.category] = (
                    category_breakdown.get(t.category, 0.0) + t.amount
                )
            
            # Unique merchants (limit to 20 for brevity)
            merchants = list(set(t.merchant for t in transactions))[:20]
            
            # Count anomalies
            anomaly_count = sum(1 for t in transactions if t.is_anomaly)
            
            output = AnalyzeTransactionsOutput(
                customer_id=validated_input.customer_id,
                transaction_count=len(transactions),
                total_amount=round(total_amount, 2),
                average_amount=round(total_amount / len(transactions), 2),
                min_amount=round(min(amounts), 2),
                max_amount=round(max(amounts), 2),
                currency=transactions[0].currency,
                category_breakdown={
                    k: round(v, 2) for k, v in category_breakdown.items()
                },
                merchant_list=merchants,
                time_range=TimeRange(
                    start=start_time,
                    end=end_time,
                    days=validated_input.window_days,
                ),
                anomaly_count=anomaly_count,
            )
        
        # Validate output
        return output.model_dump()
