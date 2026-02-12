"""
Pydantic schemas for API request/response models.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RunTaskRequest(BaseModel):
    """Request to run a workflow for a customer."""

    customer_id: str = Field(
        description="Customer UUID to analyze",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
    )
    analysis_window_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days to look back for transaction analysis",
    )
    anomaly_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Anomaly detection threshold (0-1)",
    )


class RunTaskResponse(BaseModel):
    """Response after starting a workflow."""

    task_id: str = Field(description="Workflow run ID")
    customer_id: str = Field(description="Customer ID")
    status: str = Field(description="Workflow status")
    created_at: datetime = Field(description="Workflow creation timestamp")


class WorkflowResult(BaseModel):
    """Workflow execution result."""

    status: str
    customer_id: str
    anomalies_detected: int = 0
    confidence_score: float = 0.0
    is_escalated: bool = False
    explanation: str = ""
    matched_policies: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    escalation_reason: Optional[str] = None
    errors: Optional[List[str]] = None


class GetTaskResponse(BaseModel):
    """Response for workflow status query."""

    task_id: str
    customer_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    input_params: dict
    result: Optional[WorkflowResult]
    audit_event_count: int
    duration_ms: Optional[int]


class AuditEventSummary(BaseModel):
    """Summary of an audit event."""

    id: str
    node_name: str
    tool_name: Optional[str]
    duration_ms: int
    timestamp: datetime


class GetAuditResponse(BaseModel):
    """Response for audit trail query."""

    task_id: str
    total_events: int
    events: List[AuditEventSummary]


class CustomerSummary(BaseModel):
    """Summary of a customer record."""

    id: str = Field(description="Customer UUID")
    name: str = Field(description="Customer name")
    email: str = Field(description="Customer email")
    account_type: str = Field(description="Account type: checking, savings, or business")


class ListCustomersResponse(BaseModel):
    """Response for listing customers."""

    customers: List[CustomerSummary] = Field(description="List of customers")
    total: int = Field(description="Total number of customers returned")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    app_name: str
    version: str
    database_connected: bool
    embedding_provider: str
    mock_mode: bool
