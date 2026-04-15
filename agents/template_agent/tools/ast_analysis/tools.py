"""LangChain tool wrappers for AST analysis (SRP: adapter layer only).

All heavy logic lives in ``parser.py``.  This module only wraps those
functions as LangChain ``@tool`` callables and exposes the getter used
by agent nodes.
"""
import glob
import json
import os

from langchain_core.tools import tool

from src.tools.ast_analysis.parser import parse_file


@tool
def analyze_file_ast(file_path: str) -> str:
    """
    Parse a single Python file and return its symbol table as JSON.

    Returns imports, top-level functions, and classes (with their methods).

    Args:
        file_path: Absolute or relative path to the file.
    """
    return json.dumps(parse_file(file_path), indent=2)


@tool
def list_workspace_symbols(workspace_path: str) -> str:
    """
    Scan every ``.py`` file under *workspace_path* and return an aggregated
    symbol map (keyed by file path) as JSON.

    Args:
        workspace_path: Root directory to scan recursively.
    """
    extensions = ("*.py", "*.js", "*.ts", "*.java", "*.go", "*.cpp", "*.c", "*.cs", "*.rb", "*.php")
    results = {}
    
    for ext in extensions:
        pattern = os.path.join(os.path.abspath(workspace_path), "**", ext)
        for fp in glob.glob(pattern, recursive=True):
            results[fp] = parse_file(fp)
            
    return json.dumps(results, indent=2)


def get_ast_tools() -> list:
    """Return all AST analysis LangChain tools."""
    return [analyze_file_ast, list_workspace_symbols]
