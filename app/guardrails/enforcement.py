"""
Guardrail enforcement for workflow safety and compliance.
Provides tool allowlisting, schema validation, and content filtering.
"""

import logging
import re
from typing import Any, Set

from pydantic import BaseModel, ValidationError

from app.config import settings

logger = logging.getLogger(__name__)


class GuardrailViolation(Exception):
    """Exception raised when a guardrail check fails."""

    def __init__(self, message: str, violation_type: str):
        self.message = message
        self.violation_type = violation_type
        super().__init__(self.message)


class GuardrailEnforcer:
    """
    Enforces guardrails for workflow execution.
    
    Guardrails include:
    - Tool allowlist: Only approved tools can be invoked
    - Schema validation: All tool inputs/outputs must conform to schemas
    - Content filtering: Blocks outputs with prohibited patterns
    - Rate limiting: Limits number of tool calls per workflow
    """

    # Approved tools that can be invoked
    ALLOWED_TOOLS: Set[str] = {
        "transaction_analyzer",
        "anomaly_detector",
        "explanation_drafter",
        "policy_retriever",
    }

    # Prohibited patterns in explanations (real institution names, PII patterns, etc.)
    PROHIBITED_PATTERNS = [
        # Real financial institutions (examples - this is a demo, so using common ones)
        r"\b(Wells Fargo|Bank of America|Chase|Citibank|Capital One|HSBC|Barclays)\b",
        
        # Real social security numbers pattern
        r"\b\d{3}-\d{2}-\d{4}\b",
        
        # Real credit card patterns (simplified)
        r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
        
        # Financial advice language
        r"\b(buy|sell|invest in|purchase|guaranteed returns)\b",
        
        # Legal claims
        r"\b(guaranteed|promise|warranty|legally binding)\b",
        
        # Regulatory compliance claims
        r"\b(PCI DSS|SOC 2|GDPR compliant|certified by)\b",
    ]

    def __init__(self):
        self.tool_call_count = 0
        self.max_tool_calls = settings.max_tool_calls_per_workflow

    def check_tool_allowlist(self, tool_name: str) -> None:
        """
        Verify that a tool is on the allowlist.
        
        Args:
            tool_name: Name of the tool to check
            
        Raises:
            GuardrailViolation: If tool is not allowed
        """
        if tool_name not in self.ALLOWED_TOOLS:
            raise GuardrailViolation(
                f"Tool '{tool_name}' is not on the allowlist. "
                f"Allowed tools: {', '.join(sorted(self.ALLOWED_TOOLS))}",
                violation_type="tool_not_allowed"
            )

    def validate_input_schema(
        self,
        input_data: Any,
        schema_class: type[BaseModel],
    ) -> BaseModel:
        """
        Validate input data against a Pydantic schema.
        
        Args:
            input_data: Input data to validate
            schema_class: Pydantic model class to validate against
            
        Returns:
            Validated Pydantic model instance
            
        Raises:
            GuardrailViolation: If validation fails
        """
        try:
            return schema_class.model_validate(input_data)
        except ValidationError as e:
            raise GuardrailViolation(
                f"Input validation failed: {e}",
                violation_type="invalid_input_schema"
            )

    def validate_output_schema(
        self,
        output_data: Any,
        schema_class: type[BaseModel],
    ) -> BaseModel:
        """
        Validate output data against a Pydantic schema.
        
        Args:
            output_data: Output data to validate
            schema_class: Pydantic model class to validate against
            
        Returns:
            Validated Pydantic model instance
            
        Raises:
            GuardrailViolation: If validation fails
        """
        try:
            return schema_class.model_validate(output_data)
        except ValidationError as e:
            raise GuardrailViolation(
                f"Output validation failed: {e}",
                violation_type="invalid_output_schema"
            )

    def check_content_safety(self, text: str) -> None:
        """
        Check text content for prohibited patterns.
        
        Args:
            text: Text to check
            
        Raises:
            GuardrailViolation: If prohibited patterns are found
        """
        for pattern in self.PROHIBITED_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raise GuardrailViolation(
                    f"Content contains prohibited pattern: {match.group()}. "
                    f"This is a demo project and must not reference real institutions, "
                    f"PII, financial advice, or compliance claims.",
                    violation_type="prohibited_content"
                )

    def increment_tool_call(self) -> None:
        """
        Increment tool call counter and check rate limit.
        
        Raises:
            GuardrailViolation: If rate limit is exceeded
        """
        self.tool_call_count += 1
        
        if self.tool_call_count > self.max_tool_calls:
            raise GuardrailViolation(
                f"Tool call limit exceeded: {self.tool_call_count}/{self.max_tool_calls}. "
                f"This prevents infinite loops and excessive API usage.",
                violation_type="rate_limit_exceeded"
            )

    def get_tool_call_stats(self) -> dict:
        """
        Get statistics about tool calls in this workflow.
        
        Returns:
            Dictionary with tool call statistics
        """
        return {
            "tool_calls_made": self.tool_call_count,
            "max_tool_calls": self.max_tool_calls,
            "remaining_calls": max(0, self.max_tool_calls - self.tool_call_count),
            "at_limit": self.tool_call_count >= self.max_tool_calls,
        }

    def reset(self) -> None:
        """Reset tool call counter for a new workflow."""
        self.tool_call_count = 0


def sanitize_for_demo(text: str) -> str:
    """
    Sanitize text to ensure it's appropriate for a public demo.
    
    Replaces any potentially problematic content with safe alternatives.
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text
    """
    # Replace real institution names with generic ones
    institution_replacements = {
        "Wells Fargo": "Example Bank",
        "Bank of America": "Demo Financial",
        "Chase": "Sample Trust",
        "Citibank": "Mock Banking Corp",
        "Capital One": "Test Financial Services",
    }
    
    result = text
    for real_name, demo_name in institution_replacements.items():
        result = re.sub(
            rf"\b{re.escape(real_name)}\b",
            demo_name,
            result,
            flags=re.IGNORECASE
        )
    
    # Redact SSN patterns
    result = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "XXX-XX-XXXX", result)
    
    # Redact credit card patterns
    result = re.sub(
        r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
        "XXXX-XXXX-XXXX-XXXX",
        result
    )
    
    return result


def validate_workflow_input(input_params: dict) -> None:
    """
    Validate workflow input parameters.
    
    Args:
        input_params: Input parameters to validate
        
    Raises:
        GuardrailViolation: If validation fails
    """
    required_fields = ["customer_id"]
    
    for field in required_fields:
        if field not in input_params:
            raise GuardrailViolation(
                f"Required field '{field}' missing from input parameters",
                violation_type="invalid_workflow_input"
            )
    
    # Validate customer_id format (should be UUID string)
    customer_id = input_params.get("customer_id")
    if customer_id:
        import uuid
        try:
            uuid.UUID(customer_id)
        except (ValueError, AttributeError):
            raise GuardrailViolation(
                f"Invalid customer_id format: {customer_id}. Must be a valid UUID.",
                violation_type="invalid_workflow_input"
            )
