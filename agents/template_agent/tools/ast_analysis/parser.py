"""Generic parsing logic — Language Agnostic.

This module replaces the old Python-only AST parser with a generic regex-based
symbol extractor so GraphRAG and Validator tools work on JS, TS, Go, Java, etc.
"""
import re
import glob
from typing import Any


def parse_file(file_path: str) -> dict[str, Any]:
    """
    Parse a generic source file and return a structured symbol table.

    Returns
    -------
    dict with keys:
      - ``file``                : str  — the input path
      - ``imports``             : list[str] — empty (hard to regex reliably across languages)
      - ``top_level_functions`` : list[dict] — ``{name, lineno}``
      - ``classes``             : list[dict] — ``{name, lineno, methods: []}``
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except OSError as exc:
        return {"file": file_path, "error": str(exc)}

    classes: list[dict] = []
    top_level_functions: list[dict] = []

    # Extremely generic regex heuristics for major languages (JS, TS, Py, Go, Java, C#, C++)
    class_pattern = re.compile(r"^\s*(export\s+)?(public\s+)?class\s+([A-Za-z0-9_]+)")
    func_pattern = re.compile(r"^\s*(export\s+)?(public\s+|private\s+|protected\s+)?(static\s+)?(async\s+)?(function|func|def)\s+([A-Za-z0-9_]+)")
    
    # Also catch common JS arrow function exports: export const myFunc = (
    arrow_pattern = re.compile(r"^\s*(export\s+)?(const|let|var)\s+([A-Za-z0-9_]+)\s*=\s*(\(.*\)|[^=]+)\s*=>")

    for i, line in enumerate(lines):
        lineno = i + 1
        
        # Match classes
        c_match = class_pattern.search(line)
        if c_match:
            classes.append({"name": c_match.group(3), "lineno": lineno, "methods": []})
            continue
            
        # Match standard functions / defs / funcs
        f_match = func_pattern.search(line)
        if f_match:
            top_level_functions.append({"name": f_match.group(6), "lineno": lineno})
            continue
            
        # Match JS arrow functions
        a_match = arrow_pattern.search(line)
        if a_match:
            top_level_functions.append({"name": a_match.group(3), "lineno": lineno})
            continue

    return {
        "file": file_path,
        "imports": [],
        "top_level_functions": top_level_functions,
        "classes": classes,
    }
