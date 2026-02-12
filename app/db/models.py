"""
SQLAlchemy ORM models for all database tables.
Includes: Customer, Transaction, PolicyDocument, WorkflowRun, AuditEvent
"""

import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WorkflowStatus(str, enum.Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"


class Customer(Base):
    """Synthetic customer data for demo purposes."""

    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # checking, savings, business
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    workflow_runs: Mapped[list["WorkflowRun"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name={self.name}, email={self.email})>"


class Transaction(Base):
    """Synthetic transaction data with optional anomaly labels."""

    __tablename__ = "transactions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    merchant: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # groceries, travel, etc.
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # Demo label

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, amount={self.amount}, merchant={self.merchant})>"


class PolicyDocument(Base):
    """Mock policy documents with vector embeddings for RAG."""

    __tablename__ = "policy_documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # fraud, limits, escalation, etc.
    embedding: Mapped[Optional[Vector]] = mapped_column(
        Vector(384), nullable=True
    )  # 384-dim for all-MiniLM-L6-v2
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<PolicyDocument(id={self.id}, title={self.title}, category={self.category})>"


class WorkflowRun(Base):
    """Tracks workflow execution runs and their results."""

    __tablename__ = "workflow_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, native_enum=False, length=20),
        nullable=False,
        default=WorkflowStatus.PENDING,
    )
    input_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="workflow_runs")
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="workflow_run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<WorkflowRun(id={self.id}, status={self.status}, customer_id={self.customer_id})>"


class AuditEvent(Base):
    """Append-only audit log of all workflow steps and tool calls."""

    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False
    )
    node_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    workflow_run: Mapped["WorkflowRun"] = relationship(back_populates="audit_events")

    def __repr__(self) -> str:
        return f"<AuditEvent(id={self.id}, node={self.node_name}, tool={self.tool_name})>"
