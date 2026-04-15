"""
generate.py — Interactive agent generator for Orchest.

Usage:
    python generate.py

Follow the prompts to configure and scaffold a new agent from the template.
Text prompts end when you type  :wq!  on a line by itself.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import textwrap

# ── Locate the template & agents dir ─────────────────────────────────────────

TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR   = os.path.dirname(TEMPLATE_DIR)

# ── Load the tool registry ────────────────────────────────────────────────────

sys.path.insert(0, TEMPLATE_DIR)
try:
    from data.tools import EXISTANT_TOOLS
except ImportError:
    EXISTANT_TOOLS = {}

# ── Import→function map: which functions each tool module exports ─────────────
# key  = EXISTANT_TOOLS key
# value = list of (import_line, function_name_or_call_in_get_tools)

TOOL_IMPORT_MAP: dict[str, dict] = {
    "ast_analysis": {
        "imports": [
            "from tools.ast_analysis.tools import analyze_file_ast, list_workspace_symbols, get_ast_tools",
        ],
        "registrations": [
            "get_ast_tools(workspace_dir)",
        ],
    },
    "docker": {
        "imports": [
            "from tools.docker.sandbox import run_tests_in_sandbox",
            "from langchain_core.tools import tool as _tool",
        ],
        "registrations": [
            # inline tool definition injected as a string block
            "__docker__",
        ],
    },
    "files": {
        "imports": [],  # already in base template
        "registrations": [],  # get_file_tools already called
    },
    "folders": {
        "imports": [],  # already in base template
        "registrations": [],  # initiate_directory already called
    },
    "git": {
        "imports": [
            "from tools.git.git_tools import clone_or_pull_repo, create_branch, commit_and_push",
        ],
        "registrations": [
            "clone_or_pull_repo",
            "create_branch",
            "commit_and_push",
        ],
    },
    "github": {
        "imports": [
            "from tools.github.issue_tools import list_open_issues, assign_issue",
            "from tools.github.pr_tools import create_pull_request",
        ],
        "registrations": [
            "list_open_issues",
            "assign_issue",
            "create_pull_request",
        ],
    },
    "gitlab": {
        "imports": [
            "from tools.gitlab.issue_tools import list_open_issues as gitlab_list_open_issues, assign_issue as gitlab_assign_issue",
            "from tools.gitlab.pr_tools import create_pull_request as gitlab_create_pull_request",
        ],
        "registrations": [
            "gitlab_list_open_issues",
            "gitlab_assign_issue",
            "gitlab_create_pull_request",
        ],
    },
    "graph_rag": {
        "imports": [
            "from tools.graph_rag.tools import query_code_graph, summarise_code_graph",
        ],
        "registrations": [
            "query_code_graph",
            "summarise_code_graph",
        ],
    },
    "linter": {
        "imports": [
            "from tools.linter.tools import run_linter",
        ],
        "registrations": [
            "run_linter",
        ],
    },
    "search": {
        "imports": [
            "from tools.search.tools import search",
        ],
        "registrations": [
            "search",
        ],
    },
}

# ── Docker inline tool block ──────────────────────────────────────────────────

DOCKER_TOOL_BLOCK = '''
        @_tool
        def run_tests() -> str:
            """Run the test suite inside a Docker sandbox."""
            from config.language_config import get_docker_image
            image = get_docker_image(self._cached_lang or "python")
            return run_tests_in_sandbox.invoke({
                "workspace_path": workspace_dir,
                "image_name":     image,
            })
'''

# ── Helpers ───────────────────────────────────────────────────────────────────


def to_pascal_case(snake_str: str) -> str:
    return "".join(x.capitalize() for x in snake_str.lower().split("_"))


def read_multiline(prompt: str) -> str:
    """Read multiple lines until the user types ':wq!' alone on a line."""
    print(prompt)
    print('  (type  :wq!  on an empty line when done)\n')
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == ":wq!":
            break
        lines.append(line)
    return "\n".join(lines)


def _hr(char: str = "─", width: int = 60) -> str:
    return char * width


def display_tool_menu(tools: dict) -> list[str]:
    """Print a numbered checklist of available tools and return the keys list."""
    keys = list(tools.keys())
    print("\nAvailable tools:")
    print(_hr())
    for i, key in enumerate(keys, 1):
        desc = tools[key].get("description", "")
        print(f"  [{i:2d}]  {key:<20}  {desc}")
    print(_hr())
    return keys


def parse_selection(raw: str, max_idx: int) -> list[int]:
    """Parse a comma/space-separated string of indices into 0-based ints."""
    selected = []
    for token in re.split(r"[\s,]+", raw.strip()):
        try:
            idx = int(token) - 1
            if 0 <= idx < max_idx:
                selected.append(idx)
        except ValueError:
            pass
    return selected


# ── Core generation ────────────────────────────────────────────────────────────


def generate_agent(
    name: str,
    agent_type: str,           # "executor" | "thinker"
    selected_tool_keys: list[str],
    system_prompt: str,
    human_prompt: str,
) -> None:
    new_agent_dir = os.path.join(AGENTS_DIR, name)

    if os.path.exists(new_agent_dir):
        print(f"\n[!] Agent '{name}' already exists at {new_agent_dir}")
        return

    pascal_name  = to_pascal_case(name)
    uses_tests   = agent_type == "executor"
    node_fn_name = f"{name}_node"

    print(f"\n  ► Copying template to {new_agent_dir} ...")
    shutil.copytree(TEMPLATE_DIR, new_agent_dir)

    # ── Rename resources folder ───────────────────────────────────────────────
    old_res = os.path.join(new_agent_dir, "resources", "agents", "template_agent")
    new_res = os.path.join(new_agent_dir, "resources", "agents", name)
    if os.path.exists(old_res):
        os.rename(old_res, new_res)
        print(f"  ► Renamed resources/agents/template_agent → resources/agents/{name}")

    # ── Build import & registration lines ────────────────────────────────────
    import_lines   = []
    tool_reg_lines = []
    for key in selected_tool_keys:
        entry = TOOL_IMPORT_MAP.get(key, {})
        for imp in entry.get("imports", []):
            if imp not in import_lines:
                import_lines.append(imp)
        for reg in entry.get("registrations", []):
            if reg == "__docker__":
                tool_reg_lines.append(DOCKER_TOOL_BLOCK.strip("\n"))
            elif reg not in tool_reg_lines:
                tool_reg_lines.append(reg)

    imports_str = "\n".join(import_lines)
    tool_list   = (
        "get_file_tools(workspace_dir) + [" + ", ".join(tool_reg_lines) + "]"
        if tool_reg_lines else
        "get_file_tools(workspace_dir)"
    )

    # ── Global text replacements across all text files ────────────────────────
    replacements = {
        "template_agent": name,
        "TemplateAgent":  pascal_name,
        "ConcreteAgent":  pascal_name,
        "template_agent_node": node_fn_name,
        "uses_tests = False": f"uses_tests = {uses_tests}",
        "uses_tests = True":  f"uses_tests = {uses_tests}",
        "# ── Add your tool imports below ───────────────────────────────────────────────\n"
        "# from tools.git.git_tools import clone_or_pull_repo, create_branch, commit_and_push\n"
        "# from tools.docker.sandbox import run_tests_in_sandbox\n"
        "# from tools.search.tools import search\n"
        "# ─────────────────────────────────────────────────────────────────────────────": (
            "# ── Tool imports (generated) ─────────────────────────────────────────────────\n"
            + (imports_str if imports_str else "# (no extra tools selected)")
            + "\n# ─────────────────────────────────────────────────────────────────────────────"
        ),
        "return get_file_tools(workspace_dir)": f"return {tool_list}",
    }

    print("  ► Rewriting file contents ...")
    for root, dirs, files in os.walk(new_agent_dir):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git"}]
        for file in files:
            if file == "generate.py":
                continue
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8") as fh:
                    content = fh.read()
                new_content = content
                for old, new in replacements.items():
                    new_content = new_content.replace(old, new)
                if new_content != content:
                    with open(file_path, "w", encoding="utf-8") as fh:
                        fh.write(new_content)
            except Exception:
                pass  # skip binary / unreadable files

    # ── Rename concrete_agent.py to concrete_agent.py (already named right) ──
    # Also rename node function in concrete_agent.py
    concrete = os.path.join(new_agent_dir, "agents", "concrete_agent.py")
    if os.path.exists(concrete):
        with open(concrete, "r", encoding="utf-8") as fh:
            src = fh.read()
        # Fix return annotation on node function
        src = src.replace(
            f"async def template_agent_node",
            f"async def {node_fn_name}",
        )
        with open(concrete, "w", encoding="utf-8") as fh:
            fh.write(src)

    # ── Write prompts ─────────────────────────────────────────────────────────
    prompts_dir = os.path.join(new_res, "prompts")
    os.makedirs(prompts_dir, exist_ok=True)

    def _yaml_block(text: str) -> str:
        indented = textwrap.indent(text, "  ")
        return f"verbose: |\n{indented}\n\ncompact: |\n{indented}\n"

    with open(os.path.join(prompts_dir, "system.yaml"), "w", encoding="utf-8") as fh:
        fh.write(_yaml_block(system_prompt or f"You are a helpful {name}."))
    with open(os.path.join(prompts_dir, "human.yaml"), "w", encoding="utf-8") as fh:
        fh.write(_yaml_block(human_prompt or "Perform the task described above."))

    # Stub nudges/suffixes if missing
    for stub_file, stub_content in [
        ("nudges.yaml", "verbose: |\n  Continue your work.\ncompact: |\n  Continue.\n"),
        ("suffixes.yaml", "# Add suffix prompts here\n"),
    ]:
        target = os.path.join(prompts_dir, stub_file)
        if not os.path.exists(target):
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(stub_content)

    # ── Remove generate.py from new agent ────────────────────────────────────
    gen_copy = os.path.join(new_agent_dir, "generate.py")
    if os.path.exists(gen_copy):
        os.remove(gen_copy)

    # ── Prune __pycache__ ────────────────────────────────────────────────────
    for root, dirs, files in os.walk(new_agent_dir, topdown=False):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{_hr('═')}")
    print(f"  ✓ Agent '{name}' generated successfully!")
    print(f"  Path      : {new_agent_dir}")
    print(f"  Class     : {pascal_name}  (concrete_agent.py)")
    print(f"  Type      : {'Executor (uses_tests=True)' if uses_tests else 'Thinker (uses_tests=False)'}")
    print(f"  Tools     : {', '.join(selected_tool_keys) if selected_tool_keys else 'files only (default)'}")
    print(f"{_hr('═')}")
    print("\nNext steps:")
    print(f"  1. Open  agents/{name}/agents/concrete_agent.py  and customise the logic.")
    print(f"  2. Edit  resources/agents/{name}/prompts/  to refine your prompts.")
    print(f"  3. Run with:  uvicorn agents.{name}.main:app --reload\n")


# ── CLI entry point ────────────────────────────────────────────────────────────


def main() -> None:
    print()
    print("╔" + _hr("═", 58) + "╗")
    print("║{:^58}║".format("O R C H E S T   Agent Generator"))
    print("╚" + _hr("═", 58) + "╝")
    print()

    # 1. Name ─────────────────────────────────────────────────────────────────
    while True:
        name = input("  Agent name (snake_case, e.g. security_agent): ").strip()
        if re.match(r"^[a-z][a-z0-9_]*$", name):
            break
        print("  [!] Invalid name. Use lowercase letters, digits, and underscores.")

    # 2. Type ─────────────────────────────────────────────────────────────────
    print()
    print("  Agent type:")
    print("    [1]  Executor  — can run tests / execute sandboxed code  (uses_tests=True)")
    print("    [2]  Thinker   — pure reasoning / code generation only   (uses_tests=False)")
    while True:
        choice = input("  Select type [1/2]: ").strip()
        if choice == "1":
            agent_type = "executor"
            break
        elif choice == "2":
            agent_type = "thinker"
            break
        print("  [!] Please enter 1 or 2.")

    # 3. Tools ────────────────────────────────────────────────────────────────
    tool_keys     = display_tool_menu(EXISTANT_TOOLS) if EXISTANT_TOOLS else []
    selected_keys: list[str] = []
    if tool_keys:
        raw = input(
            "\n  Enter tool numbers to include (comma or space separated),"
            "\n  or press Enter to skip: "
        ).strip()
        if raw:
            indices       = parse_selection(raw, len(tool_keys))
            selected_keys = [tool_keys[i] for i in indices]
            if selected_keys:
                print(f"  Selected: {', '.join(selected_keys)}")
            else:
                print("  No valid selection — using file tools only.")

    # 4. System prompt ────────────────────────────────────────────────────────
    system_prompt = read_multiline(
        f"\n  System prompt for {name}\n  (describe the agent's role and constraints):"
    )

    # 5. Human prompt ─────────────────────────────────────────────────────────
    human_prompt = read_multiline(
        f"\n  Human / task prompt for {name}\n  (describe what the agent should do when invoked):"
    )

    # 6. Confirm & generate ───────────────────────────────────────────────────
    print()
    print(_hr())
    print(f"  Name   : {name}   ({to_pascal_case(name)})")
    print(f"  Type   : {agent_type}")
    print(f"  Tools  : {', '.join(selected_keys) if selected_keys else 'files (default)'}")
    print(_hr())
    confirm = input("  Generate? [Y/n]: ").strip().lower()
    if confirm in ("", "y", "yes"):
        generate_agent((name+"_agent").lower(), agent_type, selected_keys, system_prompt, human_prompt)
    else:
        print("  Aborted.")


if __name__ == "__main__":
    main()
