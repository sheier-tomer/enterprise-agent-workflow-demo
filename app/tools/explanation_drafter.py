"""
Explanation drafter tool.
Drafts natural language explanations of anomaly findings.
"""

import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


class PolicyReference(BaseModel):
    """Reference to a policy document."""

    policy_id: str
    title: str
    category: str


class DraftExplanationInput(BaseModel):
    """Input schema for drafting explanations."""

    customer_id: str = Field(description="Customer UUID")
    anomalies: List[dict] = Field(description="List of detected anomalies")
    transaction_summary: dict = Field(description="Transaction analysis summary")
    policies: List[dict] = Field(
        default_factory=list,
        description="Retrieved policy documents",
    )
    use_mock: bool = Field(
        default=True,
        description="Use deterministic mock explanation",
    )


class DraftExplanationOutput(BaseModel):
    """Output schema for drafted explanations."""

    customer_id: str
    explanation: str
    policy_references: List[PolicyReference]
    recommended_actions: List[str]
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the explanation",
    )


class ExplanationDrafter:
    """
    Tool for drafting natural language explanations of transaction anomalies.
    
    In mock mode (default): Uses template-based generation
    In real mode: Uses OpenAI API for LLM-generated explanations
    """

    def __init__(self):
        self.use_mock = settings.use_mock_llm

    def _draft_mock_explanation(
        self,
        customer_id: str,
        anomalies: List[dict],
        transaction_summary: dict,
        policies: List[dict],
    ) -> DraftExplanationOutput:
        """Generate deterministic mock explanation."""
        
        num_anomalies = len(anomalies)
        total_transactions = transaction_summary.get("transaction_count", 0)
        
        # Build explanation
        explanation_parts = []
        
        explanation_parts.append(
            f"Analysis of {total_transactions} transactions identified "
            f"{num_anomalies} potential {'anomaly' if num_anomalies == 1 else 'anomalies'}."
        )
        
        if anomalies:
            explanation_parts.append("\n\nDetected anomalies include:")
            for i, anomaly in enumerate(anomalies[:3], 1):  # Limit to top 3
                amount = anomaly.get("amount", 0)
                merchant = anomaly.get("merchant", "Unknown")
                score = anomaly.get("anomaly_score", 0)
                reasons = anomaly.get("reasons", [])
                
                explanation_parts.append(
                    f"\n{i}. Transaction of ${amount:.2f} at {merchant} "
                    f"(score: {score:.2f})"
                )
                if reasons:
                    explanation_parts.append(f"   Reasons: {', '.join(reasons)}")
        
        # Add policy context
        if policies:
            explanation_parts.append(
                f"\n\nThis analysis references {len(policies)} relevant internal policies "
                f"regarding transaction monitoring and fraud detection."
            )
        
        # Recommendations
        recommendations = []
        if num_anomalies == 0:
            recommendations.append("continue_normal_monitoring")
            confidence = 0.95
        elif num_anomalies <= 2:
            recommendations.append("flag_for_review")
            recommendations.append("notify_customer")
            confidence = 0.85
        else:
            recommendations.append("escalate_to_analyst")
            recommendations.append("notify_customer")
            recommendations.append("enhanced_monitoring")
            confidence = 0.65
        
        # Build policy references
        policy_refs = []
        for policy in policies[:3]:  # Top 3 policies
            policy_refs.append(
                PolicyReference(
                    policy_id=policy.get("id", "unknown"),
                    title=policy.get("title", "Unknown Policy"),
                    category=policy.get("category", "general"),
                )
            )
        
        explanation = "".join(explanation_parts)
        
        return DraftExplanationOutput(
            customer_id=customer_id,
            explanation=explanation,
            policy_references=policy_refs,
            recommended_actions=recommendations,
            confidence_score=round(confidence, 2),
        )

    async def _draft_llm_explanation(
        self,
        customer_id: str,
        anomalies: List[dict],
        transaction_summary: dict,
        policies: List[dict],
    ) -> DraftExplanationOutput:
        """Generate LLM-based explanation (requires OpenAI API key)."""
        
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            
            # Build prompt
            prompt_parts = [
                f"You are an AI analyst reviewing transaction data for customer {customer_id}.",
                f"\nTransaction Summary: {transaction_summary}",
                f"\nDetected Anomalies: {anomalies}",
            ]
            
            if policies:
                policy_context = "\n".join([
                    f"- {p.get('title', 'Unknown')}: {p.get('content', '')[:200]}..."
                    for p in policies
                ])
                prompt_parts.append(f"\nRelevant Policies:\n{policy_context}")
            
            prompt_parts.append(
                "\nProvide a concise explanation of the findings and recommend actions. "
                "Keep it professional and factual. This is a DEMO with SYNTHETIC data."
            )
            
            prompt = "".join(prompt_parts)
            
            # Call OpenAI
            response = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a financial transaction analyst."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            
            explanation = response.choices[0].message.content
            
            # Determine recommendations based on anomaly count
            num_anomalies = len(anomalies)
            if num_anomalies == 0:
                recommendations = ["continue_normal_monitoring"]
                confidence = 0.95
            elif num_anomalies <= 2:
                recommendations = ["flag_for_review", "notify_customer"]
                confidence = 0.85
            else:
                recommendations = ["escalate_to_analyst", "notify_customer"]
                confidence = 0.70
            
            # Build policy references
            policy_refs = [
                PolicyReference(
                    policy_id=p.get("id", "unknown"),
                    title=p.get("title", "Unknown"),
                    category=p.get("category", "general"),
                )
                for p in policies[:3]
            ]
            
            return DraftExplanationOutput(
                customer_id=customer_id,
                explanation=explanation,
                policy_references=policy_refs,
                recommended_actions=recommendations,
                confidence_score=round(confidence, 2),
            )
            
        except Exception as e:
            logger.warning(f"LLM explanation failed, falling back to mock: {e}")
            return self._draft_mock_explanation(
                customer_id, anomalies, transaction_summary, policies
            )

    async def execute(self, input_data: dict) -> dict:
        """
        Execute explanation drafting.
        
        Args:
            input_data: Dictionary matching DraftExplanationInput schema
            
        Returns:
            Dictionary matching DraftExplanationOutput schema
        """
        # Validate input
        validated_input = DraftExplanationInput.model_validate(input_data)
        
        # Choose generation method
        use_mock = validated_input.use_mock or self.use_mock or not settings.openai_api_key
        
        if use_mock:
            output = self._draft_mock_explanation(
                customer_id=validated_input.customer_id,
                anomalies=validated_input.anomalies,
                transaction_summary=validated_input.transaction_summary,
                policies=validated_input.policies,
            )
        else:
            output = await self._draft_llm_explanation(
                customer_id=validated_input.customer_id,
                anomalies=validated_input.anomalies,
                transaction_summary=validated_input.transaction_summary,
                policies=validated_input.policies,
            )
        
        # Validate output
        return output.model_dump()
