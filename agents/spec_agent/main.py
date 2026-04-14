"""
Spec Agent - Generates technical specifications from tickets.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to sys.path to allow importing 'shared'
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI
from shared.schemas.agent_io import AgentInput, AgentOutput
from .handler import SpecHandler
from dotenv import load_dotenv
load_dotenv()  # Force load .env file

logger = logging.getLogger(__name__)

app = FastAPI(title="Spec Agent", version="1.0.0")
handler = SpecHandler()


@app.post("/execute")
async def execute(request: AgentInput) -> AgentOutput:
    """Generate technical specification from ticket."""
    try:
        result = handler.process(request)
        return AgentOutput(
            status="success",
            output=result,
            confidence=result.get("confidence", 0.85),
            metadata={
                "agent": "spec",
                "step_id": request.step_id,
                "language": result.get("language"),
                "fallback_locations": result.get("fallback_locations", [])
            }
        )
    except Exception as e:
        logger.error(f"Spec agent failed: {e}", exc_info=True)
        return AgentOutput(
            status="failed",
            output={},
            confidence=0.0,
            error=str(e),
            metadata={"agent": "spec", "step_id": request.step_id}
        )


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "spec"}


@app.get("/ready")
async def ready():
    return {"status": "ready", "agent": "spec"}