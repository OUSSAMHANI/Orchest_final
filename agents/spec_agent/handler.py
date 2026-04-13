"""
SpecHandler — Bridge between the Orchestrator (AgentInput) and Agent Spec pipeline.

Receives an AgentInput dict, calls run_agent_spec(), writes spec.md, and returns
an AgentOutput dict.

Does NOT modify anything inside agent_spec/.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SpecHandler:
    """
    Orchestrator-facing handler for the Agent Spec pipeline.

    Usage:
        handler = SpecHandler()
        output  = handler.process(agent_input_dict)
    """

    # Confidence thresholds for status determination.
    _THRESHOLD_SUCCESS = 0.7
    _THRESHOLD_PARTIAL = 0.4

    # ── Public entry point ─────────────────────────────────────────────────────

    def process(self, request: dict) -> dict:
        """
        Receive an AgentInput (serialised dict) and return an AgentOutput dict.

        Args:
            request: AgentInput serialised as a plain dict.

        Returns:
            AgentOutput serialised as a plain dict.
        """
        start_ms = time.perf_counter()

        try:
            result = self._run(request)
        except Exception as exc:
            logger.exception("[SpecHandler] Unhandled exception: %s", exc)
            elapsed_ms = int((time.perf_counter() - start_ms) * 1000)
            return {
                "status":     "failed",
                "output":     {},
                "confidence": 0.0,
                "error":      str(exc),
                "metadata": {
                    "execution_time_ms": elapsed_ms,
                    "llm_model":         request.get("metadata", {}).get("llm_model", ""),
                    "warnings":          [],
                },
            }

        elapsed_ms = int((time.perf_counter() - start_ms) * 1000)
        result["metadata"]["execution_time_ms"] = elapsed_ms
        return result

    # ── Internal pipeline ──────────────────────────────────────────────────────

    def _run(self, request: dict) -> dict:
        # 1. Extract top-level fields from AgentInput.
        workspace_path   = request["workspace_path"]
        ticket           = request.get("ticket", {})
        ticket_summary   = request.get("ticket_summary", {})
        mr_diff          = request.get("mr_diff", "")
        metadata         = request.get("metadata", {})
        step_id          = request.get("step_id", "spec")
        previous_outputs = request.get("previous_outputs", {})

        # 2. Build enriched ticket for run_agent_spec().
        issue_id = ticket_summary.get("issue_id") or ticket.get("issue_id") or step_id
        ticket_for_pipeline: Dict[str, Any] = {
            "id":                  str(issue_id),
            "title":               ticket_summary.get("title")       or ticket.get("title", ""),
            "description":         ticket_summary.get("description") or ticket.get("description", ""),
            "summary":             ticket_summary.get("summary", ""),
            "severity":            ticket_summary.get("priority", "normal"),
            "component":           ticket_summary.get("scope", ""),
            "labels":              ticket_summary.get("labels", []),
            "branch":              ticket_summary.get("branch", ""),
            "acceptance_criteria": ticket_summary.get("acceptance_criteria", []),
            "constraints":         ticket_summary.get("constraints", ""),
            "non_goals":           ticket_summary.get("non_goals", ""),
            "hinted_scope":        ticket_summary.get("hinted_scope", []),
            "mr_diff":             mr_diff,
        }

        # 3. Extract optional context fields.
        error_trace    = ticket.get("error_trace")    or metadata.get("error_trace")
        affected_files = ticket.get("affected_files") or ticket_summary.get("hinted_scope") or None
        commit_sha     = ticket.get("commit_sha")
        retry_feedback = (previous_outputs.get("spec") or {}).get("error") or None
        priority_hints = ticket_summary.get("hinted_scope") or None
        llm_model      = metadata.get("llm_model") or None
        thread_id      = str(issue_id)

        logger.info(
            "[SpecHandler] Starting — step_id=%s  issue=%s  repo=%s",
            step_id, issue_id, workspace_path,
        )

        # 4. Call the Agent Spec pipeline.
        from agent_spec.graph import run_agent_spec
        location: dict = run_agent_spec(
            ticket         = ticket_for_pipeline,
            mr_diff        = mr_diff,
            repo_path      = workspace_path,
            thread_id      = thread_id,
            llm_model      = llm_model,
            error_trace    = error_trace,
            affected_files = affected_files,
            commit_sha     = commit_sha,
            retry_feedback = retry_feedback,
            priority_hints = priority_hints,
        )

        confidence = float(location.get("confidence", 0.0))
        logger.info("[SpecHandler] Pipeline done — confidence=%.2f", confidence)

        # 5. Write spec.md to disk.
        spec_file = self._write_spec_file(location, ticket_summary, workspace_path, issue_id)

        # 6. Format AgentOutput.output (SpecAgentOutput).
        output = self._format_output(location, spec_file, ticket_summary)

        # 7. Determine status from confidence.
        if confidence >= self._THRESHOLD_SUCCESS:
            status = "success"
        elif confidence >= self._THRESHOLD_PARTIAL:
            status = "partial"
        else:
            status = "failed"

        warnings: List[str] = []
        if not location.get("file"):
            warnings.append("bug file not identified")
        if not location.get("function"):
            warnings.append("bug function not identified")
        if confidence < self._THRESHOLD_SUCCESS:
            warnings.append(f"low confidence ({confidence:.2f}) — review fallback_locations")

        return {
            "status":     status,
            "output":     output,
            "confidence": confidence,
            "error":      None,
            "metadata": {
                "execution_time_ms": 0,   # filled by process()
                "llm_model":         llm_model or "",
                "warnings":          warnings,
            },
        }

    # ── Private helpers ────────────────────────────────────────────────────────

    def _write_spec_file(
        self,
        location:       dict,
        ticket_summary: dict,
        workspace_path: str,
        issue_id:       Any,
    ) -> str:
        """
        Write specs/spec_{issue_id}.md inside workspace_path.
        Returns the absolute path (even if writing failed).
        """
        specs_dir = Path(workspace_path) / "specs"
        spec_path = specs_dir / f"spec_{issue_id}.md"

        patch_constraints: dict = location.get("patch_constraints") or {}
        missing_files:     list = location.get("missing_files") or []

        missing_section = ""
        if missing_files:
            lines = ["## Files to Create\n"]
            for mf in missing_files:
                lines.append(f"### `{mf.get('path', '')}`")
                lines.append(f"**Reason**: {mf.get('reason', '')}\n")
                if mf.get("template"):
                    lines.append("```")
                    lines.append(mf["template"])
                    lines.append("```\n")
            missing_section = "\n".join(lines)

        fallback_section = ""
        fallbacks = location.get("fallback_locations") or []
        if fallbacks:
            rows = "\n".join(
                f"- `{fb.get('file')}::{fb.get('function')}` — {fb.get('reason', '')}"
                for fb in fallbacks
            )
            fallback_section = f"## Fallback Locations\n{rows}\n"

        content = f"""\
# Bug Fix Specification — {ticket_summary.get("title", "Untitled")}

## Summary
{ticket_summary.get("summary", "")}

## Problem
{location.get("problem_summary", "")}

## Root Cause
{location.get("root_cause", "")}

## Bug Location
- **File**: `{location.get("file", "")}`
- **Function**: `{location.get("function", "")}`
- **Line**: {location.get("line", 0)}
- **Language**: {location.get("language", "")}

## Code Context
```{location.get("language", "")}
{location.get("code_context", "")}
```

## Expected Behavior
{location.get("expected_behavior", "")}

## Patch Constraints
- **Scope**: {patch_constraints.get("scope", "")}
- **Preserve tests**: {patch_constraints.get("preserve_tests", [])}
- **Forbidden files**: {patch_constraints.get("forbidden_files", [])}
- **Style**: {patch_constraints.get("style_hint", "")}

## Call Graph
- **Callers**: {location.get("callers", [])}
- **Callees**: {location.get("callees", [])}

{missing_section}
{fallback_section}
## Acceptance Criteria
{self._format_list(ticket_summary.get("acceptance_criteria", []))}

## Constraints
{ticket_summary.get("constraints", "")}
"""

        try:
            specs_dir.mkdir(parents=True, exist_ok=True)
            spec_path.write_text(content, encoding="utf-8")
            logger.info("[SpecHandler] spec.md written: %s", spec_path)
        except Exception as exc:
            logger.warning("[SpecHandler] Could not write spec.md (%s) — continuing.", exc)

        return str(spec_path.resolve())

    def _format_output(
        self,
        location:       dict,
        spec_file:      str,
        ticket_summary: dict,
    ) -> dict:
        """Build the SpecAgentOutput dict from location + ticket_summary."""
        patch_constraints: dict = location.get("patch_constraints") or {}
        fallbacks:         list = location.get("fallback_locations") or []
        hinted_scope:      list = ticket_summary.get("hinted_scope") or []

        # requirements — root_cause + expected_behavior + acceptance_criteria
        requirements: List[str] = []
        if location.get("root_cause"):
            requirements.append(location["root_cause"])
        if location.get("expected_behavior"):
            requirements.append(location["expected_behavior"])
        ac = ticket_summary.get("acceptance_criteria") or []
        if isinstance(ac, list):
            requirements.extend(ac)
        elif isinstance(ac, str) and ac:
            requirements.append(ac)

        # constraints
        constraints: List[str] = []
        if patch_constraints.get("scope"):
            constraints.append(patch_constraints["scope"])
        tc = ticket_summary.get("constraints")
        if tc:
            constraints.append(str(tc))
        for f in patch_constraints.get("forbidden_files") or []:
            constraints.append(f"Do not modify: {f}")

        # suggested_files — bug file first, then fallbacks, then hinted_scope
        seen:            set  = set()
        suggested_files: List[str] = []
        for f in [location.get("file")] + [fb.get("file") for fb in fallbacks] + hinted_scope:
            if f and f not in seen:
                seen.add(f)
                suggested_files.append(f)

        # implementation_notes
        callers = (location.get("callers") or [])[:3]
        callees = (location.get("callees") or [])[:3]
        notes_lines = [
            f"**Problem**: {location.get('problem_summary', '')}",
            f"**Location**: `{location.get('file', '')}::{location.get('function', '')}` line {location.get('line', 0)}",
            f"**Callers**: {callers or 'none'}",
            f"**Callees**: {callees or 'none'}",
            f"**Confidence**: {location.get('confidence', 0.0):.0%}",
        ]
        if location.get("code_context"):
            notes_lines += ["", "**Code Context**:", "```", location["code_context"], "```"]
        implementation_notes = "\n".join(notes_lines)

        return {
            "spec_file":            spec_file,
            "requirements":         requirements,
            "acceptance_criteria":  ticket_summary.get("acceptance_criteria") or [],
            "constraints":          constraints,
            "suggested_files":      suggested_files,
            "implementation_notes": implementation_notes,
            # Extended fields for the Coder agent.
            "confidence":           location.get("confidence", 0.0),
            "language":             location.get("language", ""),
            "fallback_locations":   fallbacks,
            "missing_files":        location.get("missing_files") or [],
            "bug_file":             location.get("file", ""),
            "bug_function":         location.get("function", ""),
            "bug_line":             location.get("line", 0),
            "patch_constraints":    patch_constraints,
            "root_cause":           location.get("root_cause", ""),
            "callers":              location.get("callers") or [],
            "callees":              location.get("callees") or [],
        }

    # ── Utilities ──────────────────────────────────────────────────────────────

    @staticmethod
    def _format_list(items) -> str:
        """Format a list (or string) as a markdown bullet list."""
        if not items:
            return ""
        if isinstance(items, str):
            return items
        return "\n".join(f"- {item}" for item in items)
