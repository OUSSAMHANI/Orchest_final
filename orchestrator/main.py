"""
Orchestrator Main Entry Point
FastAPI application for the multi-agent orchestrator.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .models.ticket import Ticket
from .graph.builder import run_orchestrator, run_orchestrator_with_config
from .state.context import StateContextManager
from shared.config.settings import get_settings, Settings


# =========================
# LOGGING SETUP
# =========================

logger = logging.getLogger(__name__)


# =========================
# LIFESPAN MANAGER
# =========================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.
    - Startup: Initialize connections, state manager
    - Shutdown: Clean up resources
    """
    # Startup
    logger.info("Starting Orchestrator API...")
    
    # Initialize global state manager
    app.state.context_manager = StateContextManager()
    
    # Optional: Start Kafka consumer in background
    # from .consumers.kafka_consumer import start_kafka_consumer
    # app.state.consumer = start_kafka_consumer(...)
    
    logger.info("Orchestrator API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Orchestrator API...")
    
    # Stop Kafka consumer if running
    # if hasattr(app.state, 'consumer'):
    #     app.state.consumer.stop()
    
    logger.info("Orchestrator API shutdown complete")


# =========================
# FASTAPI APP
# =========================

app = FastAPI(
    title="Multi-Agent Orchestrator API",
    description="Orchestrates spec, coder, tester, and reviewer agents for automated code changes",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# DEPENDENCIES
# =========================

def get_settings_dep() -> Settings:
    """Dependency to get settings."""
    return get_settings()


# =========================
# HEALTH ENDPOINTS
# =========================

@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Liveness probe for container orchestration.
    Returns 200 if the service is running.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@app.get("/ready", tags=["Health"])
async def readiness_check(
    settings: Settings = Depends(get_settings_dep),
) -> Dict[str, Any]:
    """
    Readiness probe checks if dependencies are available.
    """
    statuses = {
        "api": "ready",
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # Check agent availability (optional)
    # agents_healthy = check_agents_health()
    # statuses["agents"] = "healthy" if agents_healthy else "degraded"
    
    return statuses


# =========================
# TICKET ENDPOINTS
# =========================

@app.post(
    "/ticket",
    tags=["Orchestration"],
    status_code=status.HTTP_202_ACCEPTED,
    response_model=Dict[str, Any],
)
async def submit_ticket(
    ticket: Ticket,
    background_tasks: BackgroundTasks,
    sync: bool = False,
    settings: Settings = Depends(get_settings_dep),
) -> Dict[str, Any]:
    """
    Submit a ticket for orchestration.
    
    - **sync=false** (default): Process in background, return ticket ID
    - **sync=true**: Process synchronously, return full result
    
    Args:
        ticket: Ticket data from Kafka/GitLab
        background_tasks: FastAPI background tasks
        sync: Whether to process synchronously
    
    Returns:
        Ticket acceptance or full result
    """
    try:
        ticket_dict = ticket.dict()
        ticket_id = ticket_dict.get("event_id") or ticket_dict.get("issue_id")
        
        logger.info(f"Received ticket: {ticket_id}")
        
        if sync:
            # Synchronous processing (blocks until complete)
            result = run_orchestrator(ticket_dict)
            return {
                "ticket_id": ticket_id,
                "status": result.get("status"),
                "result": result,
                "mode": "sync",
            }
        else:
            # Asynchronous processing (background)
            background_tasks.add_task(_process_ticket_background, ticket_dict)
            
            return {
                "ticket_id": ticket_id,
                "status": "accepted",
                "message": "Ticket accepted for processing",
                "mode": "async",
                "timestamp": datetime.utcnow().isoformat(),
            }
            
    except Exception as e:
        logger.error(f"Failed to submit ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process ticket: {str(e)}",
        )


@app.post(
    "/ticket/sync",
    tags=["Orchestration"],
    response_model=Dict[str, Any],
)
async def submit_ticket_sync(
    ticket: Ticket,
    settings: Settings = Depends(get_settings_dep),
) -> Dict[str, Any]:
    """
    Submit a ticket and wait for complete result (synchronous).
    Useful for debugging and testing.
    """
    try:
        ticket_dict = ticket.dict()
        ticket_id = ticket_dict.get("event_id") or ticket_dict.get("issue_id")
        
        logger.info(f"Processing ticket synchronously: {ticket_id}")
        
        result = run_orchestrator(ticket_dict)
        
        return {
            "ticket_id": ticket_id,
            "status": result.get("status"),
            "result": result,
        }
        
    except Exception as e:
        logger.error(f"Sync ticket processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.post(
    "/ticket/configured",
    tags=["Orchestration"],
    response_model=Dict[str, Any],
)
async def submit_ticket_with_config(
    ticket: Ticket,
    config: Dict[str, Any],
    settings: Settings = Depends(get_settings_dep),
) -> Dict[str, Any]:
    """
    Submit a ticket with custom runtime configuration.
    Overrides default settings for this execution only.
    """
    try:
        ticket_dict = ticket.dict()
        ticket_id = ticket_dict.get("event_id") or ticket_dict.get("issue_id")
        
        logger.info(f"Processing ticket with custom config: {ticket_id}")
        
        result = run_orchestrator_with_config(ticket_dict, config)
        
        return {
            "ticket_id": ticket_id,
            "status": result.get("status"),
            "result": result,
        }
        
    except Exception as e:
        logger.error(f"Configured ticket processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# =========================
# STATUS ENDPOINTS
# =========================

@app.get(
    "/status/{ticket_id}",
    tags=["Status"],
    response_model=Dict[str, Any],
)
async def get_ticket_status(
    ticket_id: str,
    settings: Settings = Depends(get_settings_dep),
) -> Dict[str, Any]:
    """
    Get the status of a previously submitted ticket.
    """
    context_manager = app.state.context_manager
    context = context_manager.get(ticket_id)
    
    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )
    
    state = context.get_state()
    
    return {
        "ticket_id": ticket_id,
        "status": state.get("status"),
        "current_step": state.get("current_step"),
        "steps_completed": len([r for r in state.get("results", {}).values() if r.get("status") == "success"]),
        "steps_failed": len([r for r in state.get("results", {}).values() if r.get("status") == "failed"]),
        "has_errors": len(state.get("errors", [])) > 0,
        "updated_at": datetime.utcnow().isoformat(),
    }


@app.get(
    "/status/{ticket_id}/result",
    tags=["Status"],
    response_model=Dict[str, Any],
)
async def get_ticket_result(
    ticket_id: str,
    settings: Settings = Depends(get_settings_dep),
) -> Dict[str, Any]:
    """
    Get the final result of a completed ticket.
    """
    context_manager = app.state.context_manager
    context = context_manager.get(ticket_id)
    
    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )
    
    state = context.get_state()
    
    if state.get("status") not in ["completed", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail=f"Ticket {ticket_id} is still processing",
        )
    
    return {
        "ticket_id": ticket_id,
        "status": state.get("status"),
        "result": state.get("final_output"),
        "errors": state.get("errors", []),
        "completed_at": datetime.utcnow().isoformat(),
    }


# =========================
# METRICS ENDPOINT
# =========================

@app.get(
    "/metrics",
    tags=["Monitoring"],
    include_in_schema=False,  # Hide from OpenAPI docs
)
async def get_metrics() -> Dict[str, Any]:
    """
    Prometheus metrics endpoint (simplified).
    For production, use prometheus_client library.
    """
    # This is a placeholder. Use prometheus_client for real metrics.
    return {
        "service": "orchestrator",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


# =========================
# BACKGROUND TASKS
# =========================

async def _process_ticket_background(ticket_dict: Dict[str, Any]) -> None:
    """
    Background task for async ticket processing.
    """
    ticket_id = ticket_dict.get("event_id") or ticket_dict.get("issue_id")
    
    try:
        logger.info(f"Background processing started for: {ticket_id}")
        
        result = run_orchestrator(ticket_dict)
        
        logger.info(f"Background processing completed for: {ticket_id}, status: {result.get('status')}")
        
    except Exception as e:
        logger.error(f"Background processing failed for {ticket_id}: {e}")


# =========================
# ERROR HANDLERS
# =========================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# =========================
# ROOT ENDPOINT
# =========================

@app.get("/", tags=["Info"])
async def root() -> Dict[str, Any]:
    """
    API information endpoint.
    """
    return {
        "service": "Multi-Agent Orchestrator",
        "version": "2.0.0",
        "endpoints": [
            {"path": "/ticket", "method": "POST", "description": "Submit ticket"},
            {"path": "/ticket/sync", "method": "POST", "description": "Submit ticket (sync)"},
            {"path": "/status/{ticket_id}", "method": "GET", "description": "Get status"},
            {"path": "/health", "method": "GET", "description": "Health check"},
            {"path": "/ready", "method": "GET", "description": "Readiness check"},
        ],
        "documentation": "/docs",
    }


# =========================
# RUN (for local development)
# =========================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "orchestrator.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )