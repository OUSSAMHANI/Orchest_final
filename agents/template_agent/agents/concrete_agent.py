"""
agents/concrete_agent.py

ConcreteAgent — the generated implementation class.
Override build_context, get_tools, build_report, and extra_state_updates
to implement your agent's logic.
"""
from __future__ import annotations

import os
from typing import Any

from agents.base_agent import BaseAgent
from config.paths import AGENTS
from state import AgentReport, GraphState
from tools.files.file_tools import get_file_tools
from tools.folders.folder_tools import initiate_directory
from utils.language_detector import detect_language

# ── Add your tool imports below ───────────────────────────────────────────────
# from tools.git.git_tools import clone_or_pull_repo, create_branch, commit_and_push
# from tools.docker.sandbox import run_tests_in_sandbox
# from tools.search.tools import search
# ─────────────────────────────────────────────────────────────────────────────


class ConcreteAgent(BaseAgent):

    agent_name = "template_agent"   # replaced by generator
    uses_tests = False              # replaced by generator: True = Executor, False = Thinker

    # ── Required: build the context dict passed to the prompt ─────────────────

    async def build_context(self, state: GraphState) -> dict[str, Any]:
        workspace_dir       = self._workspace_dir(state)
        language, framework = self._detect(state, workspace_dir)

        self._cached_workspace = workspace_dir
        self._cached_lang      = language
        self._cached_fw        = framework

        profile    = state.get("model_profile", {})
        max_spec   = int(profile.get("max_spec",     1_500))
        max_ticket = int(profile.get("max_ticket",     800))

        ticket = state.get("ticket_text", "")
        spec   = state.get("spec", "")

        return dict(
            detected_language  = language,
            detected_framework = framework,
            file_list_str      = self._file_list(
                workspace_dir, int(profile.get("max_files", 30))
            ),
            ticket_text = (
                ticket if len(ticket) <= max_ticket
                else ticket[:max_ticket] + "\n...[ticket truncated]"
            ),
            spec_text = (
                spec if len(spec) <= max_spec
                else spec[:max_spec] + "\n...[spec truncated]"
            ),
        )

    # ── Required: return the tools the agent can use ──────────────────────────

    async def get_tools(self, state: GraphState) -> list:
        workspace_dir = self._workspace_dir(state)
        initiate_directory(workspace_dir)

        # ── Register selected tools below ─────────────────────────────────────
        # Example:
        #   @tool
        #   def my_tool(arg: str) -> str:
        #       """Tool description."""
        #       return some_function(arg)
        # ── End tool registration ─────────────────────────────────────────────

        return get_file_tools(workspace_dir)

    # ── Optional: enrich the AgentReport returned to the orchestrator ─────────

    async def build_report(
        self,
        *,
        status: str,
        summary: str,
        state: GraphState,
        tokens: int,
    ) -> AgentReport:
        base = await super().build_report(
            status=status, summary=summary, state=state, tokens=tokens,
        )
        # Add custom fields to the report here, e.g.:
        # base["files_written"] = self._files_written
        return base

    # ── Optional: push extra keys back into the graph state ──────────────────

    async def extra_state_updates(self, state: GraphState) -> dict[str, Any]:
        return {
            "detected_language":  self._cached_lang,
            "detected_framework": self._cached_fw,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _workspace_dir(state: GraphState) -> str:
        from config.paths import PROJECT_ROOT
        
        # 1. Prioritize explicit workspace_path from GraphState (usually passed by orchestrator)
        explicit_path = state.get("workspace_path")
        if explicit_path:
            return str(explicit_path)
            
        # 2. Fallback to repo-based calculation
        repo_url = state.get("repo_url", "")
        base = PROJECT_ROOT / "workspace"
        return str(
            base / repo_url.split("/")[-1].replace(".git", "")
            if repo_url else base
        )

    @staticmethod
    def _detect(state: GraphState, workspace_dir: str) -> tuple[str, str]:
        language  = state.get("detected_language") or ""
        framework = state.get("detected_framework") or ""
        if not language or language == "Unknown":
            info      = detect_language(workspace_dir)
            language  = info.get("language", "Unknown")
            framework = info.get("framework", "Unknown")
        return language, framework

    @staticmethod
    def _file_list(workspace_dir: str, max_files: int) -> str:
        ignore = {".git", "__pycache__", "node_modules", ".venv"}
        files  = []
        if os.path.exists(workspace_dir):
            for root, dirs, fs in os.walk(workspace_dir):
                dirs[:] = [d for d in dirs if d not in ignore]
                for f in fs:
                    files.append(
                        os.path.relpath(os.path.join(root, f), workspace_dir)
                    )
        if len(files) > max_files:
            files = files[:max_files] + [
                f"... ({len(files) - max_files} more not shown)"
            ]
        return "\n".join(f"- {f}" for f in files)


# ── LangGraph node entrypoint ─────────────────────────────────────────────────

async def template_agent_node(state: GraphState) -> dict:
    return await ConcreteAgent().run(state)
