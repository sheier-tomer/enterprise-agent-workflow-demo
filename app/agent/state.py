"""
LangGraph state definition for workflow execution.
The state is shared across all nodes in the workflow.
"""

from typing import TypedDict, List


class WorkflowState(TypedDict):
    """
    Shared state for the workflow execution.
    
    Each node receives this state, performs operations, and returns
    updates to be merged back into the state.
    """

    # Workflow metadata
    workflow_run_id: str
    customer_id: str
    input_params: dict
    
    # Transaction data
    transactions: list[dict]
    transaction_summary: dict
    
    # Anomaly detection
    anomalies: list[dict]
    anomaly_count: int
    
    # RAG retrieval
    retrieved_policies: list[dict]
    
    # Explanation generation
    explanation: str
    confidence_score: float
    recommended_actions: list[str]
    
    # Decision tracking
    is_escalated: bool
    escalation_reason: str
    
    # Final result
    final_result: dict
    
    # Error tracking
    errors: list[str]
