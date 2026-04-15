"""
src/agents/testing_agent.py

TestingAgent — uses_tests=False (it writes tests but does not run them).
Updated to async build_context / get_tools / extra_state_updates for v2 BaseAgent.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import yaml

from agents.base_agent import BaseAgent
from config.agent_config import AgentConfig
from config.language_config import get_docker_image, get_hints
from config.paths import AGENTS
from state import AgentReport, GraphState
from tools.docker.sandbox import run_tests_in_sandbox
from tools.files import get_file_tools
from tools.folders import initiate_directory
from utils.language_detector import detect_language
from langchain_core.tools import tool


@lru_cache(maxsize=None)
def _qa_tools() -> dict[str, dict]:
    path = AGENTS / "testing_agent" / "prompts" / "qa_tools.yaml"
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@lru_cache(maxsize=None)
def _language_runners() -> dict[str, dict]:
    path = AGENTS / "testing_agent" / "prompts" / "language_runners.yaml"
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# testing_agent.py — replace both catalogue builders

def _build_catalogue(verbose: bool) -> str:
    tools = _qa_tools()
    if verbose:
        lines = []
        for key, meta in tools.items():
            block = (
                f"[{key}]\n"
                f"  Concern      : {meta['concern']}\n"
                f"  Install      : {meta['install']}\n"
                f"  Teardown     : {meta.get('teardown_hint', 'rm -rf tests/ .gitignore script.sh')}\n"
                f"  script.sh    :\n"
            )
            block += "\n".join(f"    {line}" for line in meta["script_hint"].splitlines())
            lines.append(block)
        return "\n\n".join(lines)
    # compact: one line per tool, still show teardown hint so the LLM uses it
    return "\n".join(
        f"  • [{key}] {meta['concern']}  "
        f"[teardown: {meta.get('teardown_hint', 'rm -rf tests/ .gitignore script.sh')}]"
        for key, meta in tools.items()
    )

class TestingAgent(BaseAgent):

    agent_name = "testing_agent"
    uses_tests = True   # participates in the "run tests" nudge

    # ── Required: context dict ────────────────────────────────────────────────

    # testing_agent.py — replace build_context
# testing_agent.py — add instance variables in __init__ and two new methods

    def __init__(self) -> None:
        super().__init__()
        self._has_unit_tests:    bool = False
        self._has_coverage_flag: bool = False
        self._last_written_paths: list[str] = []

    async def on_tool_result(
        self, tool_name: str, result: str, state: GraphState
    ) -> None:
        await super().on_tool_result(tool_name, result, state)

        if tool_name == "write_file":
            # Track which sub-dirs have been written
            lower = result.lower()
            if "tests/unit" in lower:
                self._has_unit_tests = True
            if any(flag in lower for flag in ["--cov", "-cover", "--coverage", "jacocoTest"]):
                self._has_coverage_flag = True
            # Collect path hints for the report
            for token in result.split():
                if token.startswith("tests/") or token in ("script.sh", ".gitignore"):
                    self._last_written_paths.append(token)

        if tool_name == "run_tests":
            # Flag coverage shortfall so post_tool_nudge can act on next turn
            lower = result.lower()
            if "coverage" in lower and any(
                phrase in lower for phrase in
                ["below", "fail", "short", "missing", "required"]
            ):
                self._issues.append("coverage_shortfall_detected")
            if any(
                phrase in lower for phrase in
                ["performance", "too slow", "threshold exceeded", "time limit"]
            ):
                self._issues.append("performance_regression_detected")

    async def post_tool_nudge(
        self, tools_called_this_turn: list[dict], state: GraphState
    ) -> str | None:
        cfg = AgentConfig(self.agent_name)
        profile = state.get("model_profile", {})
        verbose = bool(profile.get("system_verbose"))

        # Coverage shortfall — fires after run_tests reported a gap
        if "coverage_shortfall_detected" in self._issues:
            self._issues.remove("coverage_shortfall_detected")
            return cfg.suffix("coverage_shortfall")

        # Performance regression — fires after run_tests reported a perf failure
        if "performance_regression_detected" in self._issues:
            self._issues.remove("performance_regression_detected")
            return cfg.suffix("performance_regression")

        # Coverage flag missing — fires after script.sh is written without --cov
        wrote_script = any(
            c["name"] == "write_file" and "script.sh" in str(c.get("args", {}))
            for c in tools_called_this_turn
        )
        if wrote_script and not self._has_coverage_flag:
            return cfg.nudge(verbose, kind="coverage")

        # Pyramid nudge — fires after test files written but no unit/ sub-dir yet
        wrote_tests = any(
            c["name"] == "write_file" and "tests/" in str(c.get("args", {}))
            for c in tools_called_this_turn
        )
        if wrote_tests and not self._has_unit_tests:
            return cfg.nudge(verbose, kind="pyramid")

        return None
    
    async def build_context(self, state: GraphState) -> dict[str, Any]:
        workspace_dir       = self._workspace_dir(state)
        language, framework = self._detect(state, workspace_dir)
        self._cached_workspace = workspace_dir
        self._cached_lang      = language
        self._cached_fw        = framework

        hints    = get_hints(language)
        profile  = state.get("model_profile", {})
        verbose  = bool(profile.get("system_verbose"))
        cfg      = AgentConfig(self.agent_name)

        # ── Pull the new fields from language_runners.yaml ────────────────────
        runners      = _language_runners()
        lang_runner  = runners.get(language, {})
        coverage_flag  = lang_runner.get("coverage_flag", "")
        mutation_hint  = lang_runner.get("mutation_hint", "")
        runner_cmd     = lang_runner.get("runner", hints.get("framework", ""))
        # file_pattern from runners is richer (unit/ + integration/ + e2e/) than
        # the old single-dir pattern from language_config
        file_pattern   = lang_runner.get("file_pattern", hints.get("file_pattern", ""))

        ticket = state.get("ticket_text", "")
        spec   = state.get("spec", "")
        max_spec   = int(profile.get("max_spec",     1_500))
        max_ticket = int(profile.get("max_test_out", 800))

        return dict(
            detected_language    = language,
            detected_framework   = framework,
            test_framework       = runner_cmd,
            file_pattern         = file_pattern,
            coverage_flag        = coverage_flag,   # NEW
            mutation_hint        = mutation_hint,   # NEW
            script_hint          = hints.get("script_hint", ""),
            lang_conventions     = hints.get("convention", ""),
            tool_catalogue       = _build_catalogue(verbose),
            file_list_str        = self._file_list(
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

    # ── Required: native tools ────────────────────────────────────────────────

    async def get_tools(self, state: GraphState) -> list:
        workspace_dir = self._workspace_dir(state)
        initiate_directory(workspace_dir)
        language, _   = self._detect(state, workspace_dir)
        docker_image  = get_docker_image(language)

        @tool
        def run_tests() -> str:
            """Run the unit test suite inside a Docker sandbox."""
            return run_tests_in_sandbox.invoke({
                "workspace_path": workspace_dir,
                "image_name":     docker_image,
            })

        return get_file_tools(workspace_dir) + [run_tests]

    # ── Optional: enrich AgentReport ─────────────────────────────────────────

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
        base["tests_generated"] = self._files_written
        return base

    # ── Optional: extra state keys ────────────────────────────────────────────

    async def extra_state_updates(self, state: GraphState) -> dict[str, Any]:
        return {
            "tests_generated":    self._files_written,
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
        base     = PROJECT_ROOT / "workspace"
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

async def testing_agent_node(state: GraphState) -> dict:
    return await TestingAgent().run(state)