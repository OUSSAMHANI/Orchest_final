"""Multi-language linter dispatcher — language-agnostic pipeline support.

Detects the dominant language in the workspace (via file extensions) and
runs the appropriate linter. Fails gracefully when a linter binary is not
installed — returns an informational message instead of crashing.

Supported linters
-----------------
Language            | Tool
Python              | flake8
JavaScript/TypeScript | eslint (via npx)
Java                | checkstyle via Maven (mvn checkstyle:check)
PHP                 | phpcs (PSR-12)
Kotlin              | ktlint
C#                  | dotnet format (dry-run)
Go                  | golint / go vet
Ruby                | rubocop
Other               | Informational skip message
"""
import os
import subprocess

from langchain_core.tools import tool
from src.utils.language_detector import detect_language


# ── Helpers ─────────────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: str) -> str:
    """Run *cmd* in *cwd* and return a combined output string."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if result.returncode == 0:
            return f"Linting passed — no issues found. ({' '.join(cmd)})"
        combined = "\n".join(filter(None, [result.stdout, result.stderr])).strip()
        return f"Linting issues found:\n{combined}"
    except FileNotFoundError:
        tool_name = cmd[0]
        return (
            f"Linter '{tool_name}' is not installed or not on PATH. "
            "Install it for automated quality checks, or ignore this message."
        )
    except subprocess.TimeoutExpired:
        return f"Linter timed out after 120 s: {' '.join(cmd)}"
    except Exception as exc:
        return f"Linter execution error: {exc}"


def _lint_python(workspace: str) -> str:
    return _run(["flake8", workspace, "--max-line-length=100"], cwd=workspace)


def _lint_javascript(workspace: str) -> str:
    # Prefer a local eslint config; fall back to recommended rules
    return _run(["npx", "--yes", "eslint", ".", "--ext", ".js,.jsx,.ts,.tsx"], cwd=workspace)


def _lint_java(workspace: str) -> str:
    pom = os.path.join(workspace, "pom.xml")
    gradle = os.path.join(workspace, "build.gradle")
    if os.path.exists(pom):
        return _run(["mvn", "--batch-mode", "checkstyle:check", "-f", pom], cwd=workspace)
    if os.path.exists(gradle):
        return _run(["./gradlew", "checkstyleMain"], cwd=workspace)
    return "Linter: no pom.xml or build.gradle found — skipping Java lint."


def _lint_kotlin(workspace: str) -> str:
    return _run(["ktlint", "**/*.kt"], cwd=workspace)


def _lint_php(workspace: str) -> str:
    return _run(["phpcs", "--standard=PSR12", workspace], cwd=workspace)


def _lint_csharp(workspace: str) -> str:
    return _run(["dotnet", "format", workspace, "--verify-no-changes"], cwd=workspace)


def _lint_go(workspace: str) -> str:
    return _run(["go", "vet", "./..."], cwd=workspace)


def _lint_ruby(workspace: str) -> str:
    return _run(["rubocop", workspace], cwd=workspace)


_LINTERS: dict = {
    "Python":     _lint_python,
    "JavaScript": _lint_javascript,
    "TypeScript": _lint_javascript,
    "Java":       _lint_java,
    "Kotlin":     _lint_kotlin,
    "PHP":        _lint_php,
    "C#":         _lint_csharp,
    "Go":         _lint_go,
    "Ruby":       _lint_ruby,
}


# ── LangChain tool ──────────────────────────────────────────────────────────

@tool
def run_linter(workspace_path: str) -> str:
    """Run the appropriate linter for the detected language in *workspace_path*.

    Detects the dominant programming language automatically and dispatches to
    the correct linter (flake8, eslint, checkstyle, phpcs, ktlint, …).
    Returns a plain-text report or a success message.

    Args:
        workspace_path: Absolute or relative path to the workspace directory.
    """
    abs_workspace = os.path.abspath(workspace_path)
    lang_info = detect_language(abs_workspace)
    language = lang_info.get("language", "Unknown")
    framework = lang_info.get("framework", "Unknown")

    print(f"  [Linter] Detected language: {language} | framework: {framework}")

    linter_fn = _LINTERS.get(language)
    if linter_fn is None:
        return (
            f"No linter configured for language '{language}'. "
            "Skipping lint step — the test runner in script.sh will catch syntax errors."
        )

    return linter_fn(abs_workspace)


def get_linter_tools() -> list:
    """Return the linting tool list."""
    return [run_linter]
