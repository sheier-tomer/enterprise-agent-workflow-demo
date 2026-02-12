"""
Append-only audit logger for workflow events.
Every node execution and tool call is logged to the database.
"""

import hashlib
import json
import time
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEvent


class AuditLogger:
    """
    Append-only audit logger that records workflow execution details.
    
    All events are persisted to the audit_events table with:
    - Workflow run ID
    - Node name
    - Tool name (if applicable)
    - Input data (sanitized)
    - Output data (sanitized)
    - Duration in milliseconds
    - Timestamp
    """

    def __init__(self, session: AsyncSession, workflow_run_id: UUID):
        """
        Initialize audit logger for a specific workflow run.
        
        Args:
            session: Database session
            workflow_run_id: ID of the workflow run to audit
        """
        self.session = session
        self.workflow_run_id = workflow_run_id
        self._start_times: dict[str, float] = {}

    def start_timer(self, key: str) -> None:
        """
        Start a timer for measuring duration.
        
        Args:
            key: Unique identifier for this timer
        """
        self._start_times[key] = time.perf_counter()

    def stop_timer(self, key: str) -> int:
        """
        Stop a timer and return elapsed milliseconds.
        
        Args:
            key: Unique identifier for the timer
            
        Returns:
            Elapsed time in milliseconds
        """
        if key not in self._start_times:
            return 0
        elapsed = time.perf_counter() - self._start_times[key]
        del self._start_times[key]
        return int(elapsed * 1000)

    @staticmethod
    def _sanitize_data(data: Any) -> dict:
        """
        Sanitize data for audit logging.
        
        - Converts to JSON-serializable format
        - Truncates very large strings
        - Removes sensitive fields
        
        Args:
            data: Data to sanitize
            
        Returns:
            Sanitized dictionary
        """
        if data is None:
            return {}

        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Skip sensitive fields
                if key.lower() in {"password", "api_key", "token", "secret"}:
                    sanitized[key] = "***REDACTED***"
                    continue

                # Truncate long strings
                if isinstance(value, str) and len(value) > 1000:
                    sanitized[key] = value[:1000] + "... (truncated)"
                elif isinstance(value, (dict, list)):
                    sanitized[key] = AuditLogger._sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized

        if isinstance(data, list):
            return [AuditLogger._sanitize_data(item) for item in data[:100]]  # Limit to 100 items

        if isinstance(data, (str, int, float, bool)):
            return {"value": data}

        # For other types, attempt JSON serialization
        try:
            return {"value": str(data)}
        except Exception:
            return {"value": "<non-serializable>"}

    @staticmethod
    def _hash_input(data: dict) -> str:
        """
        Create a hash of input data for deduplication checking.
        
        Args:
            data: Input data
            
        Returns:
            SHA256 hash of the data
        """
        try:
            data_str = json.dumps(data, sort_keys=True)
            return hashlib.sha256(data_str.encode()).hexdigest()[:16]
        except Exception:
            return "unknown"

    async def log_node_start(
        self,
        node_name: str,
        input_data: Any = None,
    ) -> None:
        """
        Log the start of a node execution.
        
        Args:
            node_name: Name of the node being executed
            input_data: Input data for the node
        """
        timer_key = f"node_{node_name}"
        self.start_timer(timer_key)

    async def log_node_completion(
        self,
        node_name: str,
        output_data: Any = None,
        input_data: Any = None,
    ) -> None:
        """
        Log the completion of a node execution.
        
        Args:
            node_name: Name of the node that completed
            output_data: Output data from the node
            input_data: Input data for the node (for audit record)
        """
        timer_key = f"node_{node_name}"
        duration_ms = self.stop_timer(timer_key)

        audit_event = AuditEvent(
            workflow_run_id=self.workflow_run_id,
            node_name=node_name,
            tool_name=None,
            input_data=self._sanitize_data(input_data),
            output_data=self._sanitize_data(output_data),
            duration_ms=duration_ms,
        )

        self.session.add(audit_event)
        await self.session.flush()

    async def log_tool_call(
        self,
        node_name: str,
        tool_name: str,
        input_data: Any,
        output_data: Any,
        duration_ms: int = 0,
    ) -> None:
        """
        Log a tool invocation.
        
        Args:
            node_name: Name of the node that called the tool
            tool_name: Name of the tool that was called
            input_data: Input parameters for the tool
            output_data: Output from the tool
            duration_ms: Duration of tool execution in milliseconds
        """
        audit_event = AuditEvent(
            workflow_run_id=self.workflow_run_id,
            node_name=node_name,
            tool_name=tool_name,
            input_data=self._sanitize_data(input_data),
            output_data=self._sanitize_data(output_data),
            duration_ms=duration_ms,
        )

        self.session.add(audit_event)
        await self.session.flush()

    async def log_error(
        self,
        node_name: str,
        error: Exception,
        input_data: Any = None,
    ) -> None:
        """
        Log an error that occurred during workflow execution.
        
        Args:
            node_name: Name of the node where error occurred
            error: The exception that was raised
            input_data: Input data that caused the error
        """
        timer_key = f"node_{node_name}"
        duration_ms = self.stop_timer(timer_key) if timer_key in self._start_times else 0

        audit_event = AuditEvent(
            workflow_run_id=self.workflow_run_id,
            node_name=node_name,
            tool_name=None,
            input_data=self._sanitize_data(input_data),
            output_data={
                "error": True,
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
            duration_ms=duration_ms,
        )

        self.session.add(audit_event)
        await self.session.flush()

    async def get_audit_trail(self) -> list[AuditEvent]:
        """
        Retrieve all audit events for this workflow run.
        
        Returns:
            List of audit events ordered by timestamp
        """
        result = await self.session.execute(
            select(AuditEvent)
            .where(AuditEvent.workflow_run_id == self.workflow_run_id)
            .order_by(AuditEvent.timestamp)
        )
        return list(result.scalars().all())

    async def get_event_count(self) -> int:
        """
        Get the number of audit events for this workflow run.
        
        Returns:
            Count of audit events
        """
        events = await self.get_audit_trail()
        return len(events)
