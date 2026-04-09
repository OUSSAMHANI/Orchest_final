"""
Plan Validator Module
Validates plan structure, dependencies, and agent references.
"""

import logging
from typing import Dict, Any, List, Set

from .planner import AGENT_REGISTRY


# =========================
# LOGGING SETUP
# =========================

logger = logging.getLogger(__name__)


# =========================
# PLAN VALIDATION
# =========================

def validate_plan(plan: Dict[str, Any]) -> bool:
    """
    Validate plan structure.
    
    Checks:
    - Plan is a dict
    - Contains 'steps' key as list
    - Each step has required fields: id, agent, depends_on, critical, description
    - Step IDs are unique
    """
    if not isinstance(plan, dict):
        logger.error("Plan is not a dictionary")
        return False
    
    if "steps" not in plan:
        logger.error("Plan missing 'steps' key")
        return False
    
    steps = plan.get("steps", [])
    if not isinstance(steps, list):
        logger.error("Plan 'steps' is not a list")
        return False
    
    if len(steps) == 0:
        logger.error("Plan has no steps")
        return False
    
    step_ids: Set[str] = set()
    
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            logger.error(f"Step {idx} is not a dictionary")
            return False
        
        # Check required fields
        required_fields = ["id", "agent", "depends_on", "critical", "description"]
        for field in required_fields:
            if field not in step:
                logger.error(f"Step {idx} missing required field: {field}")
                return False
        
        # Check field types
        step_id = step.get("id")
        if not isinstance(step_id, str):
            logger.error(f"Step {idx} 'id' must be a string")
            return False
        
        if step_id in step_ids:
            logger.error(f"Duplicate step id: {step_id}")
            return False
        step_ids.add(step_id)
        
        agent = step.get("agent")
        if not isinstance(agent, str):
            logger.error(f"Step {idx} 'agent' must be a string")
            return False
        
        depends_on = step.get("depends_on")
        if not isinstance(depends_on, list):
            logger.error(f"Step {idx} 'depends_on' must be a list")
            return False
        
        critical = step.get("critical")
        if not isinstance(critical, bool):
            logger.error(f"Step {idx} 'critical' must be a boolean")
            return False
        
        description = step.get("description")
        if not isinstance(description, str):
            logger.error(f"Step {idx} 'description' must be a string")
            return False
    
    logger.info(f"Plan validation passed: {len(steps)} steps")
    return True


def validate_dependencies(plan: Dict[str, Any]) -> bool:
    """
    Validate that all dependencies reference existing steps.
    
    Checks:
    - Every step in depends_on exists in the plan
    """
    steps = plan.get("steps", [])
    
    # Build set of all step IDs
    step_ids: Set[str] = {step.get("id") for step in steps if "id" in step}
    
    for step in steps:
        step_id = step.get("id")
        depends_on = step.get("depends_on", [])
        
        for dep_id in depends_on:
            if dep_id not in step_ids:
                logger.error(f"Step '{step_id}' depends on non-existent step '{dep_id}'")
                return False
            
            # Prevent self-dependency
            if dep_id == step_id:
                logger.error(f"Step '{step_id}' depends on itself")
                return False
    
    logger.info("Dependency validation passed")
    return True


def has_circular_dependencies(plan: Dict[str, Any]) -> bool:
    """
    Detect circular dependencies in the plan.
    
    Uses DFS to detect cycles in the dependency graph.
    Returns True if circular dependency found.
    """
    steps = plan.get("steps", [])
    
    # Build dependency graph
    graph: Dict[str, List[str]] = {}
    for step in steps:
        step_id = step.get("id")
        depends_on = step.get("depends_on", [])
        graph[step_id] = depends_on
    
    # DFS cycle detection
    visited: Set[str] = set()
    recursion_stack: Set[str] = set()
    
    def has_cycle(node: str) -> bool:
        visited.add(node)
        recursion_stack.add(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in recursion_stack:
                logger.error(f"Circular dependency detected involving: {node} -> {neighbor}")
                return True
        
        recursion_stack.remove(node)
        return False
    
    for node in graph:
        if node not in visited:
            if has_cycle(node):
                return True
    
    logger.info("No circular dependencies found")
    return False


def validate_agent_ids(plan: Dict[str, Any]) -> bool:
    """
    Validate that all agent IDs exist in the agent registry.
    """
    steps = plan.get("steps", [])
    valid_agents = set(AGENT_REGISTRY.keys())
    
    for step in steps:
        agent_id = step.get("agent")
        if agent_id not in valid_agents:
            logger.error(f"Invalid agent ID: '{agent_id}'. Valid agents: {valid_agents}")
            return False
    
    logger.info("Agent ID validation passed")
    return True


def validate_plan_complete(plan: Dict[str, Any]) -> bool:
    """
    Run all validations and return combined result.
    """
    if not validate_plan(plan):
        return False
    
    if not validate_dependencies(plan):
        return False
    
    if has_circular_dependencies(plan):
        return False
    
    if not validate_agent_ids(plan):
        return False
    
    return True


# =========================
# STEP HELPERS
# =========================

def get_step_by_id(plan: Dict[str, Any], step_id: str) -> Dict[str, Any]:
    """Get a step by its ID."""
    for step in plan.get("steps", []):
        if step.get("id") == step_id:
            return step
    return {}


def get_step_dependencies(plan: Dict[str, Any], step_id: str) -> List[str]:
    """Get dependencies for a specific step."""
    step = get_step_by_id(plan, step_id)
    return step.get("depends_on", [])


def get_steps_by_agent(plan: Dict[str, Any], agent_id: str) -> List[Dict[str, Any]]:
    """Get all steps assigned to a specific agent."""
    return [
        step for step in plan.get("steps", [])
        if step.get("agent") == agent_id
    ]


def get_execution_order(plan: Dict[str, Any]) -> List[str]:
    """
    Get topological order of steps (respecting dependencies).
    Returns empty list if circular dependencies exist.
    """
    if has_circular_dependencies(plan):
        return []
    
    steps = plan.get("steps", [])
    graph: Dict[str, List[str]] = {}
    for step in steps:
        step_id = step.get("id")
        depends_on = step.get("depends_on", [])
        graph[step_id] = depends_on
    
    # Kahn's algorithm for topological sort
    in_degree: Dict[str, int] = {node: 0 for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            if dep in in_degree:
                in_degree[dep] += 1
    
    queue = [node for node, degree in in_degree.items() if degree == 0]
    result = []
    
    while queue:
        node = queue.pop(0)
        result.append(node)
        
        # Find all steps that depend on this node
        for candidate, deps in graph.items():
            if node in deps:
                in_degree[candidate] -= 1
                if in_degree[candidate] == 0:
                    queue.append(candidate)
    
    return result if len(result) == len(graph) else []