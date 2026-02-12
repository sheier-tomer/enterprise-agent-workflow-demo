"""
FastAPI router with workflow execution endpoints.
"""

import logging
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import execute_workflow
from app.api.schemas import (
    RunTaskRequest,
    RunTaskResponse,
    GetTaskResponse,
    GetAuditResponse,
    AuditEventSummary,
    WorkflowResult,
    HealthResponse,
)
from app.config import settings
from app.db import get_session
from app.db.models import WorkflowRun, WorkflowStatus, AuditEvent, Customer
from app.guardrails.enforcement import validate_workflow_input

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/tasks/run", response_model=RunTaskResponse, status_code=202)
async def run_task(
    request: RunTaskRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Start a workflow execution for a customer.
    
    This endpoint:
    1. Validates the input
    2. Creates a WorkflowRun record
    3. Executes the LangGraph workflow
    4. Updates the WorkflowRun with results
    5. Returns the task ID
    """
    try:
        # Validate input
        validate_workflow_input({"customer_id": request.customer_id})
        
        # Check if customer exists
        customer_id = UUID(request.customer_id)
        customer_result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = customer_result.scalars().first()
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Create workflow run record
        workflow_run = WorkflowRun(
            id=uuid4(),
            customer_id=customer_id,
            status=WorkflowStatus.RUNNING,
            input_params={
                "analysis_window_days": request.analysis_window_days,
                "anomaly_threshold": request.anomaly_threshold,
            },
        )
        
        session.add(workflow_run)
        await session.commit()
        await session.refresh(workflow_run)
        
        logger.info(f"Created workflow run {workflow_run.id} for customer {customer_id}")
        
        # Execute workflow (async in background for real app, but synchronous here for simplicity)
        try:
            result = await execute_workflow(
                workflow_run_id=workflow_run.id,
                customer_id=customer_id,
                input_params=workflow_run.input_params,
                session=session,
            )
            
            # Update workflow run with result
            workflow_run.result = result
            workflow_run.status = (
                WorkflowStatus.ESCALATED
                if result.get("is_escalated")
                else WorkflowStatus.COMPLETED
            )
            workflow_run.completed_at = datetime.now()
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            workflow_run.status = WorkflowStatus.FAILED
            workflow_run.error_message = str(e)
            workflow_run.completed_at = datetime.now()
            await session.commit()
            raise
        
        return RunTaskResponse(
            task_id=str(workflow_run.id),
            customer_id=str(customer_id),
            status=workflow_run.status.value,
            created_at=workflow_run.created_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=GetTaskResponse)
async def get_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get workflow run status and result.
    """
    try:
        # Parse task ID
        workflow_run_id = UUID(task_id)
        
        # Query workflow run
        result = await session.execute(
            select(WorkflowRun).where(WorkflowRun.id == workflow_run_id)
        )
        workflow_run = result.scalars().first()
        
        if not workflow_run:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Count audit events
        audit_result = await session.execute(
            select(AuditEvent).where(AuditEvent.workflow_run_id == workflow_run_id)
        )
        audit_events = list(audit_result.scalars().all())
        
        # Calculate duration
        duration_ms = None
        if workflow_run.completed_at:
            duration = workflow_run.completed_at - workflow_run.created_at
            duration_ms = int(duration.total_seconds() * 1000)
        
        # Parse result
        workflow_result = None
        if workflow_run.result:
            workflow_result = WorkflowResult(**workflow_run.result)
        
        return GetTaskResponse(
            task_id=str(workflow_run.id),
            customer_id=str(workflow_run.customer_id),
            status=workflow_run.status.value,
            created_at=workflow_run.created_at,
            completed_at=workflow_run.completed_at,
            input_params=workflow_run.input_params,
            result=workflow_result,
            audit_event_count=len(audit_events),
            duration_ms=duration_ms,
        )
        
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    except Exception as e:
        logger.error(f"Error getting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/audit", response_model=GetAuditResponse)
async def get_task_audit(
    task_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get full audit trail for a workflow run.
    """
    try:
        # Parse task ID
        workflow_run_id = UUID(task_id)
        
        # Query workflow run (to verify it exists)
        workflow_result = await session.execute(
            select(WorkflowRun).where(WorkflowRun.id == workflow_run_id)
        )
        workflow_run = workflow_result.scalars().first()
        
        if not workflow_run:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Query audit events
        audit_result = await session.execute(
            select(AuditEvent)
            .where(AuditEvent.workflow_run_id == workflow_run_id)
            .order_by(AuditEvent.timestamp)
        )
        audit_events = list(audit_result.scalars().all())
        
        # Convert to summary format
        event_summaries = [
            AuditEventSummary(
                id=str(event.id),
                node_name=event.node_name,
                tool_name=event.tool_name,
                duration_ms=event.duration_ms,
                timestamp=event.timestamp,
            )
            for event in audit_events
        ]
        
        return GetAuditResponse(
            task_id=task_id,
            total_events=len(event_summaries),
            events=event_summaries,
        )
        
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    except Exception as e:
        logger.error(f"Error getting audit trail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_session)):
    """
    Health check endpoint.
    """
    try:
        # Test database connection
        await session.execute(select(1))
        database_connected = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        database_connected = False
    
    return HealthResponse(
        status="healthy" if database_connected else "degraded",
        app_name=settings.app_name,
        version=settings.app_version,
        database_connected=database_connected,
        embedding_provider=settings.embedding_provider,
        mock_mode=settings.use_mock_llm,
    )
