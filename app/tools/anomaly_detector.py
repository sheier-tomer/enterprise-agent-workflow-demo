"""
Anomaly detector tool.
Identifies anomalous transactions using rule-based heuristics.
"""

import logging
from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Transaction

logger = logging.getLogger(__name__)


class DetectAnomaliesInput(BaseModel):
    """Input schema for anomaly detection."""

    customer_id: str = Field(description="Customer UUID to analyze")
    window_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days to look back",
    )
    threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Anomaly score threshold (0-1)",
    )


class AnomalyDetails(BaseModel):
    """Details of a detected anomaly."""

    transaction_id: str
    amount: float
    merchant: str
    category: str
    timestamp: datetime
    anomaly_score: float
    reasons: List[str]


class DetectAnomaliesOutput(BaseModel):
    """Output schema for anomaly detection."""

    customer_id: str
    total_transactions: int
    anomalies_detected: int
    anomalies: List[AnomalyDetails]
    detection_threshold: float


class AnomalyDetector:
    """
    Tool for detecting anomalous transactions.
    
    Uses rule-based heuristics:
    - Unusually large amounts (>5x average)
    - Transactions at odd hours (2-5 AM)
    - Foreign merchants (indicated by country prefix)
    - Pre-labeled anomalies (is_anomaly flag)
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _calculate_anomaly_score(
        self,
        transaction: Transaction,
        avg_amount: float,
        std_amount: float,
    ) -> tuple[float, List[str]]:
        """
        Calculate anomaly score and reasons for a transaction.
        
        Returns:
            Tuple of (score, reasons) where score is 0-1
        """
        score = 0.0
        reasons = []
        
        # Check amount deviation (30% weight)
        if avg_amount > 0:
            z_score = abs((transaction.amount - avg_amount) / (std_amount + 0.01))
            if z_score > 3:
                score += 0.3
                reasons.append(f"Amount {z_score:.1f} standard deviations from mean")
        
        # Check time of day (20% weight)
        hour = transaction.timestamp.hour
        if 2 <= hour <= 5:
            score += 0.2
            reasons.append(f"Transaction at unusual hour ({hour}:00)")
        
        # Check for foreign merchant (15% weight)
        if any(transaction.merchant.startswith(prefix) for prefix in ["UK-", "FR-", "DE-", "JP-", "AU-"]):
            score += 0.15
            reasons.append("Foreign merchant")
        
        # Check database label (35% weight)
        if transaction.is_anomaly:
            score += 0.35
            reasons.append("Flagged in database as anomaly")
        
        # Check unusually large amount (additional factor)
        if transaction.amount > avg_amount * 5:
            score += 0.1
            reasons.append(f"Amount >5x average (${avg_amount:.2f})")
        
        # Cap at 1.0
        score = min(score, 1.0)
        
        return score, reasons

    async def execute(self, input_data: dict) -> dict:
        """
        Execute anomaly detection.
        
        Args:
            input_data: Dictionary matching DetectAnomaliesInput schema
            
        Returns:
            Dictionary matching DetectAnomaliesOutput schema
        """
        # Validate input
        validated_input = DetectAnomaliesInput.model_validate(input_data)
        
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
        
        result = await self.session.execute(stmt)
        transactions = list(result.scalars().all())
        
        if not transactions:
            # No transactions to analyze
            output = DetectAnomaliesOutput(
                customer_id=validated_input.customer_id,
                total_transactions=0,
                anomalies_detected=0,
                anomalies=[],
                detection_threshold=validated_input.threshold,
            )
            return output.model_dump()
        
        # Calculate baseline statistics
        amounts = [t.amount for t in transactions]
        avg_amount = sum(amounts) / len(amounts)
        
        # Calculate standard deviation
        variance = sum((x - avg_amount) ** 2 for x in amounts) / len(amounts)
        std_amount = variance ** 0.5
        
        # Detect anomalies
        anomalies = []
        for transaction in transactions:
            score, reasons = self._calculate_anomaly_score(
                transaction, avg_amount, std_amount
            )
            
            if score >= validated_input.threshold:
                anomaly = AnomalyDetails(
                    transaction_id=str(transaction.id),
                    amount=transaction.amount,
                    merchant=transaction.merchant,
                    category=transaction.category,
                    timestamp=transaction.timestamp,
                    anomaly_score=round(score, 3),
                    reasons=reasons,
                )
                anomalies.append(anomaly)
        
        # Sort by score (highest first)
        anomalies.sort(key=lambda a: a.anomaly_score, reverse=True)
        
        output = DetectAnomaliesOutput(
            customer_id=validated_input.customer_id,
            total_transactions=len(transactions),
            anomalies_detected=len(anomalies),
            anomalies=anomalies,
            detection_threshold=validated_input.threshold,
        )
        
        # Validate output
        return output.model_dump()
