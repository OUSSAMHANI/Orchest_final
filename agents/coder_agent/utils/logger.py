"""
Request-level context logger.

Creates one structured log file per incoming request inside the ``Logs/``
directory at the project root.  The file captures a snapshot of the raw
context (GraphState), an estimated token footprint, and the current agent
at the moment the request enters the pipeline.

File naming convention
----------------------
    log-YYYY-MM-DD-HH-mm-ss.log

Sections
--------
1. **HEADER**           – timestamp, endpoint, HTTP method
2. **RAW CONTEXT**      – the full initial GraphState dict
3. **TOKEN ESTIMATE**   – per-field and total character/token estimates
4. **CURRENT AGENT**    – entry-point agent info + registered graph nodes
5. **TOOL REGISTRY**    – all tools declared across agents (lazy-loaded references)
6. **ENVIRONMENT**      – selected env vars (model name, API base, etc.)
"""

import json
import os
import math
from datetime import datetime, timezone
from typing import Any


# ── Constants ────────────────────────────────────────────────────────────────
_LOGS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "Logs")
)
_CHAT_LOGS_DIR = os.path.join(_LOGS_DIR, "chatLogs")

_CHARS_PER_TOKEN = 4  # rough heuristic (OpenAI / Gemini average)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ensure_logs_dir() -> None:
    """Create the Logs/ and chatLogs/ directory if it doesn't already exist."""
    os.makedirs(_LOGS_DIR, exist_ok=True)
    os.makedirs(_CHAT_LOGS_DIR, exist_ok=True)


def _estimate_tokens(text: str) -> int:
    """Return a rough token estimate based on character count."""
    return math.ceil(len(text) / _CHARS_PER_TOKEN)


def _pretty_json(obj: Any) -> str:
    """Return a pretty-printed JSON string, falling back to repr."""
    try:
        return json.dumps(obj, indent=2, default=str)
    except (TypeError, ValueError):
        return repr(obj)


def _build_token_breakdown(state: dict) -> dict:
    """
    Return a dict mapping each state key to its estimated token count,
    plus a ``_total`` key for the aggregate.
    """
    breakdown: dict[str, int] = {}
    total = 0
    for key, value in state.items():
        serialised = json.dumps(value, default=str)
        tokens = _estimate_tokens(serialised)
        breakdown[key] = tokens
        total += tokens
    breakdown["_total"] = total
    return breakdown


def _collect_tool_registry() -> dict[str, list[str]]:
    """
    Enumerate tools that each agent *declares* it can use.

    Tools are instantiated lazily inside their respective agent nodes, so
    here we only import the factory functions and list the tool names they
    produce — without actually invoking the LLM.
    """
    registry: dict[str, list[str]] = {}
    try:
        from tools.files import get_file_tools
        workspace = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "workspace")
        )
        registry["file_tools"] = [t.name for t in get_file_tools(workspace)]
    except Exception as exc:
        registry["file_tools"] = [f"<error: {exc}>"]

    try:
        from tools.search import get_search_tools
        registry["search_tools"] = [t.name for t in get_search_tools()]
    except Exception as exc:
        registry["search_tools"] = [f"<error: {exc}>"]

    try:
        from tools.linter import get_linter_tools
        registry["linter_tools"] = [t.name for t in get_linter_tools()]
    except Exception as exc:
        registry["linter_tools"] = [f"<error: {exc}>"]

    try:
        from tools.ast_analysis import get_ast_tools
        registry["ast_tools"] = [t.name for t in get_ast_tools()]
    except Exception as exc:
        registry["ast_tools"] = [f"<error: {exc}>"]

    try:
        from tools.graph_rag import get_graph_rag_tools
        registry["graph_rag_tools"] = [t.name for t in get_graph_rag_tools()]
    except Exception as exc:
        registry["graph_rag_tools"] = [f"<error: {exc}>"]

    return registry


def _collect_env_snapshot() -> dict[str, str | None]:
    """Capture a selection of relevant environment variables."""
    keys = [
        "MODEL_NAME",
        "GOOGLE_API_KEY",
        "GITHUB_TOKEN",
        "GITLAB_TOKEN",
        "NEO4J_URI",
    ]
    snapshot: dict[str, str | None] = {}
    for k in keys:
        val = os.getenv(k)
        if val is not None:
            # Mask secrets: show first 4 and last 4 chars only
            if any(secret in k.upper() for secret in ("KEY", "TOKEN", "SECRET")):
                if len(val) > 10:
                    val = val[:4] + "****" + val[-4:]
                else:
                    val = "****"
        snapshot[k] = val
    return snapshot


# ── Public API ───────────────────────────────────────────────────────────────

def log_request_start(
    *,
    endpoint: str,
    http_method: str,
    initial_state: dict,
    entry_agent: str,
    graph_nodes: list[str] | None = None,
) -> tuple[str, str]:
    """
    Write a structured log file for a new request.

    Returns
    -------
    tuple[str, str]
        (log_path, chat_log_path)
    """
    _ensure_logs_dir()

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%d-%H-%M-%S")
    
    # Request log
    filename = f"log-{timestamp}.log"
    filepath = os.path.join(_LOGS_DIR, filename)

    # Chat log
    chat_filename = f"chatLog-{timestamp}.log"
    chat_filepath = os.path.join(_CHAT_LOGS_DIR, chat_filename)

    token_breakdown = _build_token_breakdown(initial_state)
    tool_registry = _collect_tool_registry()
    env_snapshot = _collect_env_snapshot()

    lines: list[str] = []
    # ── 1. HEADER ────────────────────────────────────────────────────────
    lines.append("=" * 80)
    lines.append(f"  REQUEST LOG — {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"endpoint       = {endpoint}")
    lines.append(f"http_method    = {http_method}")
    lines.append(f"timestamp_utc  = {now.isoformat()}")
    lines.append("")

    # ── 2. RAW CONTEXT ───────────────────────────────────────────────────
    lines.append("-" * 80)
    lines.append("  SECTION 1: RAW CONTEXT (GraphState)")
    lines.append("-" * 80)
    lines.append("")
    lines.append(f"context = {_pretty_json(initial_state)}")
    lines.append("")

    # ── 3. TOKEN ESTIMATE ────────────────────────────────────────────────
    lines.append("-" * 80)
    lines.append("  SECTION 2: TOKEN ESTIMATE")
    lines.append("-" * 80)
    lines.append("")
    lines.append(f"current_tokens_in_context = {_pretty_json(token_breakdown)}")
    lines.append("")

    # ── 4. CURRENT AGENT ─────────────────────────────────────────────────
    lines.append("-" * 80)
    lines.append("  SECTION 3: CURRENT AGENT")
    lines.append("-" * 80)
    lines.append("")
    agent_info = {
        "entry_point": entry_agent,
        "graph_nodes": graph_nodes or [],
    }
    lines.append(f"current_agent = {_pretty_json(agent_info)}")
    lines.append("")

    # ── 5. TOOL REGISTRY ─────────────────────────────────────────────────
    lines.append("-" * 80)
    lines.append("  SECTION 4: TOOL REGISTRY")
    lines.append("-" * 80)
    lines.append("")
    lines.append(f"tool_registry = {_pretty_json(tool_registry)}")
    lines.append("")

    # ── 6. ENVIRONMENT ───────────────────────────────────────────────────
    lines.append("-" * 80)
    lines.append("  SECTION 5: ENVIRONMENT")
    lines.append("-" * 80)
    lines.append("")
    lines.append(f"environment = {_pretty_json(env_snapshot)}")
    lines.append("")
    lines.append("=" * 80)
    lines.append("  END OF REQUEST LOG")
    lines.append("=" * 80)

    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    # Initiate empty chat log
    with open(chat_filepath, "w", encoding="utf-8") as fh:
        fh.write(f"# Chat Log — {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")

    print(f"[Logger] Request log initiated -> {filepath}")
    print(f"[Logger] Chat log initiated -> {chat_filepath}")
    return filepath, chat_filepath


def log_llm_interaction(
    filepath: str,
    agent_name: str,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    """
    Append an LLM interaction section to an existing request log.
    """
    if not filepath or not os.path.exists(filepath):
        return

    now = datetime.now(timezone.utc)
    total = prompt_tokens + completion_tokens

    lines: list[str] = []
    lines.append("")
    lines.append("-" * 80)
    lines.append(f"  LLM INTERACTION — {agent_name} — {now.strftime('%H:%M:%S UTC')}")
    lines.append("-" * 80)
    lines.append(f"model_name        = {model_name}")
    lines.append(f"prompt_tokens     = {prompt_tokens}")
    lines.append(f"completion_tokens = {completion_tokens}")
    lines.append(f"total_tokens      = {total}")
    lines.append("-" * 80)

    with open(filepath, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"[Logger] LLM interaction logged for {agent_name} in {os.path.basename(filepath)}")


def log_chat_interaction(filepath: str, agent_name: str, prompt: Any) -> None:
    """
    Log the full prompt for an agent interaction in JSON format.
    Format: Agent { "name":"Agent Name", "prompt":"..." }
    """
    if not filepath or not os.path.exists(filepath):
        return

    entry = {
        "name": agent_name,
        "prompt": prompt
    }
    
    # Format according to user request: Agent { ... }
    log_entry = f"Agent {json.dumps(entry, indent=2, default=str)}\n\n"

    with open(filepath, "a", encoding="utf-8") as fh:
        fh.write(log_entry)

    print(f"[Logger] Chat prompt logged for {agent_name} in {os.path.basename(filepath)}")
