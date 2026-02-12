"""
LangGraph node functions for workflow execution.
Each node performs a specific task in the workflow pipeline.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import WorkflowState
from app.audit.logger import AuditLogger
from app.config import settings
from app.guardrails.enforcement import GuardrailEnforcer
from app.rag.retriever import retrieve_relevant_policies
from app.tools.registry import ToolRegistry
from app.tools.transaction_analyzer import TransactionAnalyzer
from app.tools.anomaly_detector import AnomalyDetector
from app.tools.explanation_drafter import ExplanationDrafter

logger = logging.getLogger(__name__)


class WorkflowContext:
    """
    Context object passed to nodes containing shared resources.
    """

    def __init__(
        self,
        session: AsyncSession,
        tool_registry: ToolRegistry,
        audit_logger: AuditLogger,
        guardrail_enforcer: GuardrailEnforcer,
    ):
        self.session = session
        self.tool_registry = tool_registry
        self.audit_logger = audit_logger
        self.guardrail_enforcer = guardrail_enforcer


async def ingest_transactions(state: WorkflowState, context: WorkflowContext) -> dict:
    """
    Node 1: Ingest and analyze customer transactions.
    
    Uses the TransactionAnalyzer tool to get transaction statistics.
    """
    node_name = "ingest_transactions"
    await context.audit_logger.log_node_start(node_name, state)
    
    try:
        # Prepare tool input
        tool_input = {
            "customer_id": state["customer_id"],
            "window_days": state["input_params"].get("analysis_window_days", 30),
            "include_anomalies": True,
        }
        
        # Invoke tool
        result = await context.tool_registry.invoke_tool(
            tool_name="transaction_analyzer",
            input_data=tool_input,
            node_name=node_name,
        )
        
        # Extract transaction details for downstream nodes
        transactions = []
        
        # Update state
        updates = {
            "transactions": transactions,
            "transaction_summary": result,
        }
        
        await context.audit_logger.log_node_completion(
            node_name, output_data=updates, input_data=tool_input
        )
        
        return updates
        
    except Exception as e:
        logger.error(f"Error in {node_name}: {e}")
        await context.audit_logger.log_error(node_name, e, state)
        return {"errors": state.get("errors", []) + [f"{node_name}: {str(e)}"]}


async def detect_anomalies(state: WorkflowState, context: WorkflowContext) -> dict:
    """
    Node 2: Detect anomalous transactions.
    
    Uses the AnomalyDetector tool to identify suspicious patterns.
    """
    node_name = "detect_anomalies"
    await context.audit_logger.log_node_start(node_name, state)
    
    try:
        # Prepare tool input
        tool_input = {
            "customer_id": state["customer_id"],
            "window_days": state["input_params"].get("analysis_window_days", 30),
            "threshold": state["input_params"].get("anomaly_threshold", 0.8),
        }
        
        # Invoke tool
        result = await context.tool_registry.invoke_tool(
            tool_name="anomaly_detector",
            input_data=tool_input,
            node_name=node_name,
        )
        
        # Update state
        updates = {
            "anomalies": result.get("anomalies", []),
            "anomaly_count": result.get("anomalies_detected", 0),
        }
        
        await context.audit_logger.log_node_completion(
            node_name, output_data=updates, input_data=tool_input
        )
        
        return updates
        
    except Exception as e:
        logger.error(f"Error in {node_name}: {e}")
        await context.audit_logger.log_error(node_name, e, state)
        return {"errors": state.get("errors", []) + [f"{node_name}: {str(e)}"]}


async def retrieve_policies(state: WorkflowState, context: WorkflowContext) -> dict:
    """
    Node 3: Retrieve relevant policy documents via RAG.
    
    Uses pgvector similarity search to find applicable policies.
    """
    node_name = "retrieve_policies"
    await context.audit_logger.log_node_start(node_name, state)
    
    try:
        # Build query from anomaly information
        anomaly_count = state.get("anomaly_count", 0)
        
        if anomaly_count > 0:
            query = (
                f"Transaction anomalies detected for customer. "
                f"Found {anomaly_count} suspicious transactions. "
                f"What policies apply to fraud detection and escalation?"
            )
        else:
            query = "Normal transaction monitoring policies"
        
        # Retrieve policies
        policies = await retrieve_relevant_policies(
            session=context.session,
            query=query,
            top_k=3,
        )
        
        # Convert to dict format
        policy_dicts = [
            {
                "id": str(policy.id),
                "title": policy.title,
                "content": policy.content[:500],  # Truncate for brevity
                "category": policy.category,
            }
            for policy in policies
        ]
        
        # Update state
        updates = {
            "retrieved_policies": policy_dicts,
        }
        
        await context.audit_logger.log_node_completion(
            node_name, output_data=updates, input_data={"query": query}
        )
        
        return updates
        
    except Exception as e:
        logger.error(f"Error in {node_name}: {e}")
        await context.audit_logger.log_error(node_name, e, state)
        return {
            "retrieved_policies": [],
            "errors": state.get("errors", []) + [f"{node_name}: {str(e)}"],
        }


async def draft_explanation(state: WorkflowState, context: WorkflowContext) -> dict:
    """
    Node 4: Draft natural language explanation of findings.
    
    Uses the ExplanationDrafter tool to generate a human-readable report.
    """
    node_name = "draft_explanation"
    await context.audit_logger.log_node_start(node_name, state)
    
    try:
        # Prepare tool input
        tool_input = {
            "customer_id": state["customer_id"],
            "anomalies": state.get("anomalies", []),
            "transaction_summary": state.get("transaction_summary", {}),
            "policies": state.get("retrieved_policies", []),
            "use_mock": settings.use_mock_llm,
        }
        
        # Invoke tool
        result = await context.tool_registry.invoke_tool(
            tool_name="explanation_drafter",
            input_data=tool_input,
            node_name=node_name,
        )
        
        # Check content safety
        explanation = result.get("explanation", "")
        try:
            context.guardrail_enforcer.check_content_safety(explanation)
        except Exception as e:
            logger.warning(f"Content safety check failed: {e}")
            explanation = "Analysis completed. Please contact support for details."
        
        # Update state
        updates = {
            "explanation": explanation,
            "confidence_score": result.get("confidence_score", 0.5),
            "recommended_actions": result.get("recommended_actions", []),
        }
        
        await context.audit_logger.log_node_completion(
            node_name, output_data=updates, input_data=tool_input
        )
        
        return updates
        
    except Exception as e:
        logger.error(f"Error in {node_name}: {e}")
        await context.audit_logger.log_error(node_name, e, state)
        return {
            "explanation": "Error generating explanation",
            "confidence_score": 0.0,
            "errors": state.get("errors", []) + [f"{node_name}: {str(e)}"],
        }


async def evaluate_confidence(state: WorkflowState, context: WorkflowContext) -> dict:
    """
    Node 5: Evaluate confidence and determine if escalation is needed.
    
    This is a decision node that routes to either escalate or finalize.
    """
    node_name = "evaluate_confidence"
    await context.audit_logger.log_node_start(node_name, state)
    
    try:
        confidence = state.get("confidence_score", 0.0)
        threshold = settings.confidence_threshold
        
        # Determine if escalation is needed
        needs_escalation = confidence < threshold
        
        updates = {
            "is_escalated": needs_escalation,
        }
        
        if needs_escalation:
            updates["escalation_reason"] = (
                f"Confidence score {confidence:.2f} below threshold {threshold:.2f}"
            )
        
        await context.audit_logger.log_node_completion(
            node_name, output_data=updates, input_data={"confidence": confidence}
        )
        
        return updates
        
    except Exception as e:
        logger.error(f"Error in {node_name}: {e}")
        await context.audit_logger.log_error(node_name, e, state)
        return {
            "is_escalated": True,
            "escalation_reason": f"Error in confidence evaluation: {str(e)}",
            "errors": state.get("errors", []) + [f"{node_name}: {str(e)}"],
        }


async def escalate(state: WorkflowState, context: WorkflowContext) -> dict:
    """
    Node 6a: Escalate case for human review.
    
    Logs escalation and prepares case for analyst review.
    """
    node_name = "escalate"
    await context.audit_logger.log_node_start(node_name, state)
    
    try:
        escalation_data = {
            "reason": state.get("escalation_reason", "Low confidence"),
            "confidence_score": state.get("confidence_score", 0.0),
            "anomaly_count": state.get("anomaly_count", 0),
            "escalated_at": "now",  # Would be actual timestamp
        }
        
        updates = {
            "final_result": {
                "status": "escalated",
                "escalation_data": escalation_data,
            }
        }
        
        await context.audit_logger.log_node_completion(
            node_name, output_data=updates, input_data=escalation_data
        )
        
        return updates
        
    except Exception as e:
        logger.error(f"Error in {node_name}: {e}")
        await context.audit_logger.log_error(node_name, e, state)
        return {"errors": state.get("errors", []) + [f"{node_name}: {str(e)}"]}


async def finalize(state: WorkflowState, context: WorkflowContext) -> dict:
    """
    Node 6b/7: Finalize workflow execution.
    
    Assembles final result with all findings.
    """
    node_name = "finalize"
    await context.audit_logger.log_node_start(node_name, state)
    
    try:
        # Build final result
        final_result = {
            "status": "escalated" if state.get("is_escalated") else "completed",
            "customer_id": state["customer_id"],
            "anomalies_detected": state.get("anomaly_count", 0),
            "confidence_score": state.get("confidence_score", 0.0),
            "is_escalated": state.get("is_escalated", False),
            "explanation": state.get("explanation", ""),
            "matched_policies": [
                p.get("title") for p in state.get("retrieved_policies", [])
            ],
            "recommended_actions": state.get("recommended_actions", []),
        }
        
        if state.get("is_escalated"):
            final_result["escalation_reason"] = state.get("escalation_reason", "")
        
        if state.get("errors"):
            final_result["errors"] = state["errors"]
        
        updates = {"final_result": final_result}
        
        await context.audit_logger.log_node_completion(
            node_name, output_data=updates, input_data={}
        )
        
        return updates
        
    except Exception as e:
        logger.error(f"Error in {node_name}: {e}")
        await context.audit_logger.log_error(node_name, e, state)
        return {
            "final_result": {
                "status": "failed",
                "error": str(e),
            },
            "errors": state.get("errors", []) + [f"{node_name}: {str(e)}"],
        }
