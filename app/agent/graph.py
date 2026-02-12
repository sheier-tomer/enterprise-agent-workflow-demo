"""
LangGraph state machine definition and workflow compilation.
Defines the graph structure and routing logic.
"""

import logging
from typing import Literal
from uuid import UUID

from langgraph.graph import StateGraph, END, START
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.nodes import (
    WorkflowContext,
    ingest_transactions,
    detect_anomalies,
    retrieve_policies,
    draft_explanation,
    evaluate_confidence,
    escalate,
    finalize,
)
from app.agent.state import WorkflowState
from app.audit.logger import AuditLogger
from app.config import settings
from app.guardrails.enforcement import GuardrailEnforcer
from app.tools.registry import ToolRegistry
from app.tools.transaction_analyzer import TransactionAnalyzer
from app.tools.anomaly_detector import AnomalyDetector
from app.tools.explanation_drafter import ExplanationDrafter

logger = logging.getLogger(__name__)


def confidence_router(state: WorkflowState) -> Literal["escalate", "finalize"]:
    """
    Routing function for conditional edge from evaluate_confidence node.
    
    Routes to:
    - "escalate" if confidence is below threshold
    - "finalize" if confidence is acceptable
    """
    if state.get("is_escalated", False):
        return "escalate"
    else:
        return "finalize"


def create_workflow() -> StateGraph:
    """
    Create and compile the LangGraph workflow.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create state graph
    graph = StateGraph(WorkflowState)
    
    # Add nodes (must be async functions that accept state and return state updates)
    graph.add_node("ingest_transactions", ingest_transactions)
    graph.add_node("detect_anomalies", detect_anomalies)
    graph.add_node("retrieve_policies", retrieve_policies)
    graph.add_node("draft_explanation", draft_explanation)
    graph.add_node("evaluate_confidence", evaluate_confidence)
    graph.add_node("escalate", escalate)
    graph.add_node("finalize", finalize)
    
    # Add edges (define workflow flow)
    graph.add_edge(START, "ingest_transactions")
    graph.add_edge("ingest_transactions", "detect_anomalies")
    graph.add_edge("detect_anomalies", "retrieve_policies")
    graph.add_edge("retrieve_policies", "draft_explanation")
    graph.add_edge("draft_explanation", "evaluate_confidence")
    
    # Conditional routing based on confidence
    graph.add_conditional_edges(
        "evaluate_confidence",
        confidence_router,
        {
            "escalate": "escalate",
            "finalize": "finalize",
        },
    )
    
    # Both escalate and finalize converge
    graph.add_edge("escalate", "finalize")
    graph.add_edge("finalize", END)
    
    # Compile the graph
    workflow = graph.compile()
    
    logger.info("Workflow graph compiled successfully")
    
    return workflow


async def execute_workflow(
    workflow_run_id: UUID,
    customer_id: UUID,
    input_params: dict,
    session: AsyncSession,
) -> dict:
    """
    Execute the workflow for a customer.
    
    Args:
        workflow_run_id: Unique ID for this workflow execution
        customer_id: Customer to analyze
        input_params: Input parameters (e.g., analysis_window_days, anomaly_threshold)
        session: Database session
        
    Returns:
        Final workflow result dictionary
    """
    logger.info(f"Starting workflow {workflow_run_id} for customer {customer_id}")
    
    # Initialize context components
    audit_logger = AuditLogger(session, workflow_run_id)
    guardrail_enforcer = GuardrailEnforcer()
    tool_registry = ToolRegistry(session, workflow_run_id, audit_logger, guardrail_enforcer)
    
    # Register tools
    transaction_analyzer = TransactionAnalyzer(session)
    anomaly_detector = AnomalyDetector(session)
    explanation_drafter = ExplanationDrafter()
    
    tool_registry.register_tool("transaction_analyzer", transaction_analyzer.execute)
    tool_registry.register_tool("anomaly_detector", anomaly_detector.execute)
    tool_registry.register_tool("explanation_drafter", explanation_drafter.execute)
    
    # Create workflow context
    context = WorkflowContext(
        session=session,
        tool_registry=tool_registry,
        audit_logger=audit_logger,
        guardrail_enforcer=guardrail_enforcer,
    )
    
    # Initialize state
    initial_state: WorkflowState = {
        "workflow_run_id": str(workflow_run_id),
        "customer_id": str(customer_id),
        "input_params": input_params,
        "transactions": [],
        "transaction_summary": {},
        "anomalies": [],
        "anomaly_count": 0,
        "retrieved_policies": [],
        "explanation": "",
        "confidence_score": 0.0,
        "recommended_actions": [],
        "is_escalated": False,
        "escalation_reason": "",
        "final_result": {},
        "errors": [],
    }
    
    # Create and compile workflow
    workflow = create_workflow()
    
    # Execute workflow with context injected into each node
    # We need to wrap nodes to inject context
    async def wrapped_node(node_func):
        async def wrapper(state):
            return await node_func(state, context)
        return wrapper
    
    # Execute by invoking each node manually with our context
    # LangGraph's ainvoke doesn't support passing additional args, so we use config
    config = {"configurable": {"context": context}}
    
    try:
        # For LangGraph 1.0, we need a different approach to pass context
        # We'll use a closure-based approach instead
        
        # Recreate graph with context-bound nodes
        graph = StateGraph(WorkflowState)
        
        # Create closures that capture context
        async def node_ingest(state):
            return await ingest_transactions(state, context)
        
        async def node_detect(state):
            return await detect_anomalies(state, context)
        
        async def node_retrieve(state):
            return await retrieve_policies(state, context)
        
        async def node_draft(state):
            return await draft_explanation(state, context)
        
        async def node_evaluate(state):
            return await evaluate_confidence(state, context)
        
        async def node_escalate(state):
            return await escalate(state, context)
        
        async def node_finalize(state):
            return await finalize(state, context)
        
        # Add nodes with closures
        graph.add_node("ingest_transactions", node_ingest)
        graph.add_node("detect_anomalies", node_detect)
        graph.add_node("retrieve_policies", node_retrieve)
        graph.add_node("draft_explanation", node_draft)
        graph.add_node("evaluate_confidence", node_evaluate)
        graph.add_node("escalate", node_escalate)
        graph.add_node("finalize", node_finalize)
        
        # Add edges
        graph.add_edge(START, "ingest_transactions")
        graph.add_edge("ingest_transactions", "detect_anomalies")
        graph.add_edge("detect_anomalies", "retrieve_policies")
        graph.add_edge("retrieve_policies", "draft_explanation")
        graph.add_edge("draft_explanation", "evaluate_confidence")
        graph.add_conditional_edges(
            "evaluate_confidence",
            confidence_router,
            {"escalate": "escalate", "finalize": "finalize"},
        )
        graph.add_edge("escalate", "finalize")
        graph.add_edge("finalize", END)
        
        # Compile and invoke
        compiled_workflow = graph.compile()
        final_state = await compiled_workflow.ainvoke(initial_state)
        
        logger.info(f"Workflow {workflow_run_id} completed successfully")
        
        return final_state.get("final_result", {})
        
    except Exception as e:
        logger.error(f"Workflow {workflow_run_id} failed: {e}")
        await audit_logger.log_error("workflow", e, initial_state)
        
        return {
            "status": "failed",
            "error": str(e),
            "customer_id": str(customer_id),
        }
