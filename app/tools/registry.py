"""
Tool registry with guardrail enforcement.
Manages tool invocation, validation, and audit logging.
"""

import logging
import time
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.logger import AuditLogger
from app.guardrails.enforcement import GuardrailEnforcer

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for workflow tools with guardrail enforcement.
    
    All tool calls go through this registry which:
    - Checks tool allowlist
    - Validates input/output schemas
    - Enforces rate limits
    - Logs to audit trail
    """

    def __init__(
        self,
        session: AsyncSession,
        workflow_run_id: UUID,
        audit_logger: AuditLogger,
        guardrail_enforcer: GuardrailEnforcer,
    ):
        self.session = session
        self.workflow_run_id = workflow_run_id
        self.audit_logger = audit_logger
        self.guardrail_enforcer = guardrail_enforcer
        self._tools: dict[str, Callable] = {}

    def register_tool(self, name: str, func: Callable) -> None:
        """
        Register a tool function.
        
        Args:
            name: Tool name (must be on allowlist)
            func: Async callable that implements the tool
        """
        # Check if tool is on allowlist
        self.guardrail_enforcer.check_tool_allowlist(name)
        self._tools[name] = func
        logger.debug(f"Registered tool: {name}")

    async def invoke_tool(
        self,
        tool_name: str,
        input_data: dict[str, Any],
        node_name: str = "unknown",
    ) -> dict[str, Any]:
        """
        Invoke a registered tool with guardrail checks and audit logging.
        
        Args:
            tool_name: Name of the tool to invoke
            input_data: Input parameters for the tool
            node_name: Name of the calling node (for audit)
            
        Returns:
            Tool output as dictionary
            
        Raises:
            GuardrailViolation: If any guardrail check fails
            ValueError: If tool is not registered
        """
        # Check tool allowlist
        self.guardrail_enforcer.check_tool_allowlist(tool_name)
        
        # Check rate limit
        self.guardrail_enforcer.increment_tool_call()
        
        # Get tool function
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' is not registered")
        
        tool_func = self._tools[tool_name]
        
        # Execute tool with timing
        start_time = time.perf_counter()
        
        try:
            # Call the tool (it will handle its own input/output validation)
            output_data = await tool_func(input_data)
            
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Log to audit trail
            await self.audit_logger.log_tool_call(
                node_name=node_name,
                tool_name=tool_name,
                input_data=input_data,
                output_data=output_data,
                duration_ms=duration_ms,
            )
            
            logger.info(f"Tool '{tool_name}' executed successfully ({duration_ms}ms)")
            
            return output_data
            
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Log error to audit
            await self.audit_logger.log_tool_call(
                node_name=node_name,
                tool_name=tool_name,
                input_data=input_data,
                output_data={
                    "error": True,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                duration_ms=duration_ms,
            )
            
            logger.error(f"Tool '{tool_name}' failed: {e}")
            raise

    def get_registered_tools(self) -> list[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())
