"""
Unit tests for workflow components.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Customer
from app.tools.transaction_analyzer import TransactionAnalyzer, AnalyzeTransactionsInput
from app.tools.anomaly_detector import AnomalyDetector, DetectAnomaliesInput
from app.tools.explanation_drafter import ExplanationDrafter, DraftExplanationInput
from app.guardrails.enforcement import GuardrailEnforcer, GuardrailViolation


@pytest.mark.asyncio
async def test_transaction_analyzer(seeded_session: AsyncSession):
    """Test transaction analyzer tool."""
    # Get a customer
    customers = await seeded_session.execute(
        "SELECT id FROM customers LIMIT 1"
    )
    customer_id = customers.scalar()
    
    if not customer_id:
        pytest.skip("No customers in test database")
    
    analyzer = TransactionAnalyzer(seeded_session)
    
    input_data = {
        "customer_id": str(customer_id),
        "window_days": 30,
        "include_anomalies": True,
    }
    
    result = await analyzer.execute(input_data)
    
    assert "customer_id" in result
    assert "transaction_count" in result
    assert "total_amount" in result
    assert isinstance(result["transaction_count"], int)


@pytest.mark.asyncio
async def test_anomaly_detector(seeded_session: AsyncSession):
    """Test anomaly detector tool."""
    # Get a customer
    customers = await seeded_session.execute(
        "SELECT id FROM customers LIMIT 1"
    )
    customer_id = customers.scalar()
    
    if not customer_id:
        pytest.skip("No customers in test database")
    
    detector = AnomalyDetector(seeded_session)
    
    input_data = {
        "customer_id": str(customer_id),
        "window_days": 30,
        "threshold": 0.8,
    }
    
    result = await detector.execute(input_data)
    
    assert "customer_id" in result
    assert "total_transactions" in result
    assert "anomalies_detected" in result
    assert "anomalies" in result
    assert isinstance(result["anomalies"], list)


@pytest.mark.asyncio
async def test_explanation_drafter():
    """Test explanation drafter tool."""
    drafter = ExplanationDrafter()
    
    input_data = {
        "customer_id": "test-customer-123",
        "anomalies": [
            {
                "transaction_id": "tx-1",
                "amount": 5000.0,
                "merchant": "Test Merchant",
                "anomaly_score": 0.9,
                "reasons": ["Large amount"],
            }
        ],
        "transaction_summary": {
            "transaction_count": 50,
            "total_amount": 10000.0,
        },
        "policies": [
            {
                "id": "policy-1",
                "title": "Test Policy",
                "category": "fraud_detection",
            }
        ],
        "use_mock": True,
    }
    
    result = await drafter.execute(input_data)
    
    assert "customer_id" in result
    assert "explanation" in result
    assert "confidence_score" in result
    assert "recommended_actions" in result
    assert isinstance(result["explanation"], str)
    assert 0.0 <= result["confidence_score"] <= 1.0


def test_guardrail_tool_allowlist():
    """Test guardrail tool allowlist enforcement."""
    enforcer = GuardrailEnforcer()
    
    # Should allow registered tools
    enforcer.check_tool_allowlist("transaction_analyzer")
    enforcer.check_tool_allowlist("anomaly_detector")
    
    # Should reject unregistered tools
    with pytest.raises(GuardrailViolation):
        enforcer.check_tool_allowlist("malicious_tool")


def test_guardrail_content_safety():
    """Test guardrail content safety checks."""
    enforcer = GuardrailEnforcer()
    
    # Should allow safe content
    safe_text = "This is a normal transaction analysis for a customer account."
    enforcer.check_content_safety(safe_text)
    
    # Should block prohibited patterns
    with pytest.raises(GuardrailViolation):
        enforcer.check_content_safety("Contact Wells Fargo immediately")
    
    with pytest.raises(GuardrailViolation):
        enforcer.check_content_safety("SSN: 123-45-6789")


def test_guardrail_rate_limiting():
    """Test guardrail rate limiting."""
    enforcer = GuardrailEnforcer()
    
    # Should allow calls up to limit
    for _ in range(enforcer.max_tool_calls):
        enforcer.increment_tool_call()
    
    # Should reject after limit
    with pytest.raises(GuardrailViolation):
        enforcer.increment_tool_call()


@pytest.mark.asyncio
async def test_input_validation():
    """Test Pydantic input validation."""
    # Valid input
    valid_input = {
        "customer_id": "12345678-1234-1234-1234-123456789012",
        "window_days": 30,
        "include_anomalies": True,
    }
    
    validated = AnalyzeTransactionsInput.model_validate(valid_input)
    assert validated.customer_id == valid_input["customer_id"]
    
    # Invalid input - window_days out of range
    invalid_input = {
        "customer_id": "12345678-1234-1234-1234-123456789012",
        "window_days": 500,  # > 365
        "include_anomalies": True,
    }
    
    with pytest.raises(Exception):
        AnalyzeTransactionsInput.model_validate(invalid_input)
