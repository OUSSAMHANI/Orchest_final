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

# ── Tools already included in the base concrete_agent.py template ────────────
# These don't need extra imports — they are wired in unconditionally.
_BUILTIN_TOOLS = {"files", "folders"}

# ── Optional filename overrides ───────────────────────────────────────────────
# If the actual file on disk differs from the key listed in data/tools.py,
# add an entry here: { "<tool_key>": { "<tools_py_filename>": "<actual_filename>" } }
_FILENAME_OVERRIDES: dict[str, dict[str, str]] = {
    "linter": {"tools.py": "linter_tools.py"},
}

# ── Docker gets a special inline tool wrapper ─────────────────────────────────
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


def _module_name(tool_key: str, filename: str) -> str:
    """Return the Python module name to import from, applying any overrides."""
    overrides = _FILENAME_OVERRIDES.get(tool_key, {})
    actual    = overrides.get(filename, filename)
    return actual.removesuffix(".py")


def derive_tool_imports(
    selected_keys: list[str],
) -> tuple[list[str], list[str]]:
    """
    Derive import lines and tool registration entries from EXISTANT_TOOLS.

    Returns:
        import_lines    — list of 'from tools.X.Y import a, b' strings
        tool_reg_lines  — list of function names / inline blocks to register
    """
    import_lines:   list[str] = []
    tool_reg_lines: list[str] = []

    for key in selected_keys:
        if key in _BUILTIN_TOOLS:
            continue  # already in base template

        tool_def = EXISTANT_TOOLS.get(key, {})
        analyzed = tool_def.get("analyzed_files", {})

        # Special case: docker needs an inline wrapper tool
        if key == "docker":
            imp = "from tools.docker.sandbox import run_tests_in_sandbox"
            imp2 = "from langchain_core.tools import tool as _tool"
            for line in [imp, imp2]:
                if line not in import_lines:
                    import_lines.append(line)
            if DOCKER_TOOL_BLOCK.strip() not in [r.strip() for r in tool_reg_lines]:
                tool_reg_lines.append(DOCKER_TOOL_BLOCK.strip("\n"))
            continue

        # General case: derive from analyzed_files
        for filename, file_info in analyzed.items():
            module  = _module_name(key, filename)
            methods = file_info.get("methods", [])
            if not methods:
                continue

            # Handle name clashes: github & gitlab both export list_open_issues etc.
            # Alias them when the tool key is not the first to define the name.
            needs_alias = key in ("gitlab",)
            if needs_alias:
                func_parts = [f"{fn} as {key}_{fn}" for fn in methods]
                aliases    = [f"{key}_{fn}" for fn in methods]
            else:
                func_parts = methods
                aliases    = methods

            imp = f"from tools.{key}.{module} import {', '.join(func_parts)}"
            if imp not in import_lines:
                import_lines.append(imp)

            for alias in aliases:
                if alias not in tool_reg_lines:
                    tool_reg_lines.append(alias)

    return import_lines, tool_reg_lines


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


# ── Interactive checkbox selector ────────────────────────────────────────────


def _checkbox_fallback(tools: dict) -> list[str]:
    """
    Pure-stdlib interactive checkbox.
    ↑/↓ to move, Space to toggle, Enter to confirm, 'a' to toggle all.
    Works on Windows (msvcrt) and Unix (termios).
    """
    import shutil

    keys   = list(tools.keys())
    n      = len(keys)
    checks = [False] * n
    cursor = 0

    # ── Platform-specific single-keypress reader ──────────────────────────────
    if sys.platform == "win32":
        import msvcrt

        def _getch() -> str:
            ch = msvcrt.getch()
            if ch in (b"\xe0", b"\x00"):   # special/arrow prefix
                ch2 = msvcrt.getch()
                return {b"H": "UP", b"P": "DOWN"}.get(ch2, "")
            return ch.decode("utf-8", errors="ignore")
    else:
        import tty, termios

        def _getch() -> str:              # type: ignore[misc]
            fd  = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    sys.stdin.read(1)      # '['
                    arrow = sys.stdin.read(1)
                    return {"A": "UP", "B": "DOWN"}.get(arrow, "")
                return ch
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _term_w() -> int:
        return shutil.get_terminal_size((80, 20)).columns

    def _sep() -> str:
        return "  " + "-" * min(56, _term_w() - 4)

    def _item_line(i: int) -> str:
        key     = keys[i]
        desc    = tools[key].get("description", "")
        tick    = "[x]" if checks[i] else "[ ]"
        pointer = "►" if i == cursor else " "
        prefix  = f"  {pointer} {tick}  {key:<20}  "
        # Clamp description so the total line never wraps
        max_desc = max(0, _term_w() - len(prefix) - 1)
        if len(desc) > max_desc:
            desc = desc[:max(0, max_desc - 1)] + "…"
        return prefix + desc

    # ── Initial draw (printed once; instruction line stays fixed) ─────────────
    print("\n  Use ↑/↓ to move, Space to toggle, 'a' to toggle all, Enter to confirm.")
    print(_sep())
    for i in range(n):
        print(_item_line(i))
    sys.stdout.write(_sep())          # no trailing newline — cursor stays here
    sys.stdout.flush()

    # ── Re-render: move up n+2 lines (sep + n items + sep, NOT the instruction)
    def _render() -> None:
        # Move cursor up to the top separator, then rewrite n+2 lines in-place
        w = _term_w()
        sys.stdout.write(f"\x1b[{n + 2}A\r")
        for line in [_sep()] + [_item_line(i) for i in range(n)] + [_sep()]:
            # ESC[2K clears the current line, then write the new content
            sys.stdout.write(f"\x1b[2K{line}\n")
        # Step cursor back up 1 so we're sitting on the last separator,
        # ready for the next render (avoids scrolling the terminal).
        sys.stdout.write(f"\x1b[1A")
        sys.stdout.flush()

    # ── Event loop ────────────────────────────────────────────────────────────
    while True:
        ch = _getch()
        if ch == "UP":
            cursor = (cursor - 1) % n
        elif ch == "DOWN":
            cursor = (cursor + 1) % n
        elif ch == " ":
            checks[cursor] = not checks[cursor]
        elif ch in ("a", "A"):
            all_on = all(checks)
            checks = [not all_on] * n
        elif ch in ("\r", "\n"):
            sys.stdout.write("\n")   # tidy newline after selection
            break
        elif ch in ("\x03", "q", "Q"):  # Ctrl-C or q
            sys.stdout.write("\n  Aborted.\n")
            sys.exit(0)
        _render()

    return [keys[i] for i, checked in enumerate(checks) if checked]



def select_tools(tools: dict) -> list[str]:
    """
    Render an interactive checkbox list of tools.
    Uses `questionary` if available (prettier), falls back to the
    built-in arrow-key implementation.
    """
    if not tools:
        return []

    try:
        import questionary
        choices = [
            questionary.Choice(
                title=f"{key:<20}  {tools[key].get('description', '')}",
                value=key,
                checked=False,
            )
            for key in tools
        ]
        result = questionary.checkbox(
            "Select tools  (Space to toggle, ↑/↓ to move, Enter to confirm):",
            choices=choices,
            instruction="(a = toggle all)",
        ).ask()
        return result or []
    except ImportError:
        return _checkbox_fallback(tools)


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

    # ── Build import & registration lines (derived from data/tools.py) ────────
    import_lines, tool_reg_lines = derive_tool_imports(selected_tool_keys)

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
    print("\n  Step 3 — Select tools:")
    selected_keys = select_tools(EXISTANT_TOOLS)
    if selected_keys:
        print(f"  ✓ Selected: {', '.join(selected_keys)}")
    else:
        print("  (no tools selected — file tools included by default)")

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
