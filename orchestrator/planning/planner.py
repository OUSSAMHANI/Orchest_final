"""
Planner Module
Generates execution plans using LLM (dynamic, no hardcoded intent mapping).
"""# At the very top of planner.py, before any other imports
import sys
import types

# Patch langchain.debug
try:
    import langchain
    if not hasattr(langchain, 'debug'):
        langchain.debug = False
        print("[PATCH] langchain.debug fixed in orchestrator")
except ImportError:
    pass

import json
import re
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..state.schema import OrchestratorState



# =========================
# LOGGING SETUP
# =========================

logger = logging.getLogger(__name__)


# =========================
# AGENT REGISTRY
# =========================

AGENT_REGISTRY = {
    "spec": {
        "description": "Generates detailed technical specifications from requirements",
        "capabilities": ["requirement analysis", "scope definition", "technical writing"],
        "requires_input": "User request or high-level goal",
        "produces": "Structured specification document",
        "can_run_first": True,
        "critical": True
    },
    "coder": {
        "description": "Generates production-ready code based on specifications",
        "capabilities": ["code generation", "syntax validation", "documentation"],
        "requires_input": "Specification or clear requirements",
        "produces": "Source code files",
        "can_run_first": False,
        "critical": True
    },
    "tester": {
        "description": "Creates and runs comprehensive test suites",
        "capabilities": ["unit testing", "integration testing", "coverage analysis"],
        "requires_input": "Source code and specifications",
        "produces": "Test results and coverage report",
        "can_run_first": False,
        "critical": False
    },
    "reviewer": {
        "description": "Reviews code quality, security, and best practices",
        "capabilities": ["code review", "security audit", "performance analysis"],
        "requires_input": "Source code and test results",
        "produces": "Review report with suggestions",
        "can_run_first": False,
        "critical": False
    }
}


# =========================
# LLM SAFE CALL
# =========================

def _safe_generate_json(
    llm_client, 
    prompt: str, 
    state: OrchestratorState,
    retries: int = 2
) -> Dict[str, Any]:
    """
    Generate JSON with retries and intelligent fallback.
    Production-ready with multiple parsing strategies.
    """
    import re
    
    for attempt in range(retries):
        try:
            result = llm_client.generate_json(prompt)
            content = getattr(result, 'content', str(result))
            
            # Strategy 1: Direct parse
            if isinstance(content, dict):
                return content
            
            if isinstance(content, str):
                # Strategy 2: Extract from markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                # Strategy 3: Find JSON object using regex
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                
                # Fix: Handle Python dict string format (single quotes)
                try:
                    return json.loads(content.strip())
                except json.JSONDecodeError:
                    # Try using ast.literal_eval as fallback for Python dict format
                    try:
                        import ast
                        parsed = ast.literal_eval(content)
                        return json.loads(json.dumps(parsed))
                    except:
                        pass
                    
                    # Last resort: simple quote replacement
                    content = content.replace("'", '"')
                    return json.loads(content.strip())
                
        except json.JSONDecodeError as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} JSON parse failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            continue
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            continue
    
    # Final fallback: Generate plan without LLM
    logger.error("LLM failed to generate valid JSON, using intelligent fallback")
    return _create_fallback_plan(state)

# =========================
# MAIN PLANNER
# =========================

def generate_plan(state: OrchestratorState) -> OrchestratorState:
    """Generate plan using LLM first, fallback to default on failure."""
    try:
        # Get LLM client from state metadata or default
        config = state.get("metadata", {}).get("config", {})
        
        # Import LLM client (lazy import to avoid circular deps)
        from shared.llm.client import get_llm_client
        
        if config and "llm" in config:
            llm_client = get_llm_client(**config["llm"])
        else:
            llm_client = get_llm_client()
        
        # Create dynamic prompt based on ticket
        prompt = _create_plan_prompt(state)
        
        # Generate plan via LLM
        plan_json = _safe_generate_json(llm_client, prompt, state)
        
        # Validate plan
        if not _is_valid_full_plan(plan_json):
            logger.warning(f"LLM plan invalid, using fallback plan")
            plan_json = _create_fallback_plan(state)
        
        logger.info(f"Plan generated with {len(plan_json.get('steps', []))} steps")
        
        return {
            **state,
            "plan": plan_json,
            "status": "executing",
            "current_step_index": 0
        }
        
    except Exception as e:
        logger.error(f"LLM plan generation failed: {e}", exc_info=True)
        fallback_plan = _create_fallback_plan(state)
        
        return {
            **state,
            "plan": fallback_plan,
            "status": "executing",
            "current_step_index": 0,
            "errors": state["errors"] + [{
                "step": "planning",
                "error": str(e),
                "timestamp": _get_timestamp()
            }]
        }


# =========================
# PLAN REGENERATION
# =========================

def regenerate_plan(
    state: OrchestratorState,
    error_context: Optional[str] = None
) -> OrchestratorState:
    """Regenerate plan using LLM with error context."""
    
    MAX_REGENERATIONS = 3
    current_count = state.get("regeneration_count", 0)
    
    if current_count >= MAX_REGENERATIONS:
        logger.warning(f"Max regenerations ({MAX_REGENERATIONS}) reached")
        return {
            **state,
            "status": "failed",
            "adaptation_reason": f"Max regenerations ({MAX_REGENERATIONS}) exceeded",
            "errors": state["errors"] + [{
                "step": "plan_regeneration",
                "error": f"Max regenerations ({MAX_REGENERATIONS}) reached",
                "timestamp": _get_timestamp()
            }]
        }
    
    try:
        # Get LLM client
        config = state.get("metadata", {}).get("config", {})
        
        from shared.llm.client import get_llm_client
        
        if config and "llm" in config:
            llm_client = get_llm_client(**config["llm"])
        else:
            llm_client = get_llm_client()
        
        # Create regeneration prompt with error context
        prompt = _create_regeneration_prompt(state, state.get("errors", []), error_context)
        
        # Generate new plan via LLM
        plan_json = _safe_generate_json(llm_client, prompt, state)
        
        # Validate
        if not _is_valid_full_plan(plan_json):
            logger.warning("Regenerated plan invalid, using fallback")
            plan_json = _create_fallback_plan(state)
        
        return {
            **state,
            "plan": plan_json,
            "status": "executing",
            "current_step_index": 0,
            "regeneration_count": current_count + 1,
            "adaptation_reason": f"Plan regenerated due to: {error_context or 'previous errors'}",
            "errors": state["errors"] + [{
                "step": "plan_regeneration",
                "message": "Plan regenerated successfully",
                "timestamp": _get_timestamp()
            }]
        }
        
    except Exception as e:
        logger.error(f"Plan regeneration failed: {e}")
        fallback_plan = _create_fallback_plan(state)
        
        return {
            **state,
            "plan": fallback_plan,
            "status": "executing",
            "current_step_index": 0,
            "errors": state["errors"] + [{
                "step": "plan_regeneration",
                "error": str(e),
                "timestamp": _get_timestamp()
            }],
            "adaptation_reason": f"Regeneration failed, using fallback plan: {str(e)}"
        }


# =========================
# VALIDATION
# =========================

def _is_valid_full_plan(plan: Dict[str, Any]) -> bool:
    """Validate plan structure, dependencies, and agent IDs."""
    from .plan_validator import validate_plan, validate_dependencies, has_circular_dependencies
    
    if not validate_plan(plan):
        logger.warning("Plan failed structure validation")
        return False
    
    if not validate_dependencies(plan):
        logger.warning("Plan failed dependency validation")
        return False
    
    if has_circular_dependencies(plan):
        logger.warning("Plan has circular dependencies")
        return False
    
    # Validate all agent IDs exist in registry
    for step in plan.get("steps", []):
        agent_id = step.get("agent")
        if agent_id not in AGENT_REGISTRY:
            logger.warning(f"Invalid agent ID in plan: {agent_id}")
            return False
    
    return True


# =========================
# DYNAMIC PROMPTS
# =========================

def _create_plan_prompt(state: OrchestratorState) -> str:
    """Create dynamic LLM prompt based on full ticket content."""
    
    ticket = state.get("ticket", {})
    workspace_path = state.get("workspace_path", "Not provided")
    
    # Serialize ticket as JSON for LLM
    ticket_json = json.dumps(ticket, indent=2, default=str)
    
    agent_catalog = _generate_agent_catalog()
    agent_ids = list(AGENT_REGISTRY.keys())
    
    return f"""You are an AI orchestrator for an automated code modification system.

WORKSPACE PATH: {workspace_path}

COMPLETE TICKET (JSON):
{ticket_json}

AVAILABLE AGENTS:
{agent_catalog}

VALID AGENT IDs: {agent_ids}

YOUR TASK:
Analyze the ticket above and create an optimal execution plan.

PLAN STRUCTURE:
Return JSON with a "steps" array. Each step has:
- "id": Unique identifier (e.g., "step_1", "spec_analysis", etc.)
- "agent": One of the valid agent IDs
- "depends_on": Array of step IDs that must finish first (empty [] if none)
- "critical": true if failure should stop execution, false if optional
- "description": What this step does for THIS specific request

IMPORTANT RULES:
1. ONLY use agents that are actually needed for this request
2. "spec" is the only agent that can run first without dependencies
3. Consider the ticket's intent, scope, description, and acceptance criteria
4. Create a minimal but complete plan
5. Return ONLY valid JSON, no markdown, no explanations

Return the plan:"""


def _create_regeneration_prompt(
    state: OrchestratorState,
    errors: List[Dict[str, Any]],
    error_context: Optional[str] = None
) -> str:
    """Create prompt for regenerating plan after failures."""
    
    ticket = state.get("ticket", {})
    ticket_json = json.dumps(ticket, indent=2, default=str)
    
    current_plan = state.get("plan", {})
    current_plan_json = json.dumps(current_plan, indent=2, default=str)
    
    # Format errors
    error_summary = "\n".join([
        f"- Step: {e.get('step', 'unknown')}, Error: {e.get('error', 'unknown')}"
        for e in errors[-5:]
    ])
    
    agent_catalog = _generate_agent_catalog()
    agent_ids = list(AGENT_REGISTRY.keys())
    
    return f"""You are an AI orchestrator. The previous plan failed. Create a CORRECTED plan.

COMPLETE TICKET (JSON):
{ticket_json}

PREVIOUS PLAN THAT FAILED:
{current_plan_json}

ERRORS ENCOUNTERED:
{error_summary}

ERROR CONTEXT: {error_context or "Not provided"}

AVAILABLE AGENTS:
{agent_catalog}

VALID AGENT IDs: {agent_ids}

YOUR TASK:
Analyze what failed and create a corrected plan. You can:
- Use fewer agents (minimal set needed)
- Use more agents (if missing caused failure)
- Change the order
- Change dependencies
- Mark failing steps as non-critical (critical: false)

Return ONLY valid JSON with the same structure as before. No markdown, no explanations.

Corrected plan:"""


# =========================
# AGENT CATALOG
# =========================

def _generate_agent_catalog() -> str:
    """Generate comprehensive agent catalog for the LLM prompt."""
    catalog_parts = []
    
    for agent_id, info in AGENT_REGISTRY.items():
        catalog_parts.append(f"""
Agent ID: "{agent_id}"
- Description: {info['description']}
- Capabilities: {', '.join(info['capabilities'])}
- Requires: {info['requires_input']}
- Produces: {info['produces']}
- Can run first: {'Yes' if info['can_run_first'] else 'No'}
- Critical if used: {'Yes' if info['critical'] else 'No'}
""")
    
    return "\n".join(catalog_parts)


# =========================
# FALLBACK PLAN (Last Resort)
# =========================

def _create_fallback_plan(state: OrchestratorState) -> Dict[str, Any]:
    """
    ULTIMATE FALLBACK — only when LLM completely fails.
    Generic plan that should work for any ticket.
    """
    ticket = state.get("ticket", {})
    intent = ticket.get("intent", "unknown")
    
    # Generic fallback based on intent (last resort)
    if intent == "fix":
        steps = [
            {"id": "analyze", "agent": "coder", "depends_on": [], "critical": True, "description": "Analyze and fix the issue"},
            {"id": "verify", "agent": "tester", "depends_on": ["analyze"], "critical": False, "description": "Verify the fix"}
        ]
    elif intent == "feature":
        steps = [
            {"id": "spec", "agent": "spec", "depends_on": [], "critical": True, "description": "Create specification"},
            {"id": "code", "agent": "coder", "depends_on": ["spec"], "critical": True, "description": "Implement feature"},
            {"id": "test", "agent": "tester", "depends_on": ["code"], "critical": False, "description": "Test feature"},
            {"id": "review", "agent": "reviewer", "depends_on": ["test"], "critical": False, "description": "Review code"}
        ]
    else:
        steps = [
            {"id": "spec", "agent": "spec", "depends_on": [], "critical": True, "description": "Analyze and document requirements"},
            {"id": "code", "agent": "coder", "depends_on": ["spec"], "critical": True, "description": "Implement solution"},
            {"id": "review", "agent": "reviewer", "depends_on": ["code"], "critical": False, "description": "Review implementation"}
        ]
    
    return {
        "steps": steps,
        "metadata": {
            "generated_by": "fallback_planner",
            "reason": "LLM plan generation failed",
            "intent": intent
        }
    }


_create_default_plan = _create_fallback_plan


# =========================
# UTILS
# =========================

def _get_timestamp() -> str:
    return datetime.utcnow().isoformat()


def get_agent_registry() -> Dict[str, Any]:
    """Return agent registry for external use."""
    return AGENT_REGISTRY