"""LangChain tool wrappers for GraphRAG (SRP: adapter layer only).

All graph construction lives in ``builder.py``.  This module wraps the
query and summary operations as LangChain ``@tool`` callables.
"""
import os

from langchain_core.tools import tool

from src.tools.graph_rag.builder import build_code_graph


def _fuzzy_match(label: str, query: str) -> bool:
    """Case-insensitive substring match used for node retrieval."""
    return query.lower() in label.lower()


@tool
def query_code_graph(query: str, workspace_path: str) -> str:
    """
    Build the code knowledge graph and retrieve nodes whose names fuzzy-match
    the *query*, together with their immediate neighbours.

    Use this *before* writing new code to understand existing relationships —
    who calls what, what a class extends, which file defines a function.

    Args:
        query:          Term to search for (e.g. ``"llm"``, ``"validate_spec"``).
        workspace_path: Root directory to scan.
    """
    G = build_code_graph(workspace_path)

    matched = [
        n for n, attrs in G.nodes(data=True)
        if _fuzzy_match(attrs.get("label", ""), query)
    ]

    if not matched:
        return f"No nodes found matching '{query}'."

    lines = [f"Graph query results for '{query}':\n"]
    for node in matched:
        attrs = G.nodes[node]
        n_type = attrs.get("node_type", "?")
        label = attrs.get("label", node)
        parent_file = attrs.get("parent_file", "")
        lineno = attrs.get("lineno", "")
        location = (
            f" (in {os.path.basename(parent_file)} line {lineno})"
            if parent_file else ""
        )
        lines.append(f"  [{n_type.upper()}] {label}{location}")

        for _, tgt, edata in G.out_edges(node, data=True):
            lines.append(f"      --> [{edata.get('relation')}] {G.nodes[tgt].get('label', tgt)}")
        for src, _, edata in G.in_edges(node, data=True):
            lines.append(f"      <-- [{edata.get('relation')}] {G.nodes[src].get('label', src)}")

    return "\n".join(lines)


@tool
def summarise_code_graph(workspace_path: str) -> str:
    """
    Build the full code knowledge graph and return a high-level structural
    summary: node counts by type, total edges, and per-file class/function counts.

    Use this as a first orientation step before diving into specific queries.

    Args:
        workspace_path: Root directory to scan.
    """
    G = build_code_graph(workspace_path)

    type_counts: dict[str, int] = {}
    for _, attrs in G.nodes(data=True):
        t = attrs.get("node_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    file_lines = []
    for node, attrs in G.nodes(data=True):
        if attrs.get("node_type") == "file":
            successors = list(G.successors(node))
            n_cls  = sum(1 for s in successors if G.nodes[s].get("node_type") == "class")
            n_fn   = sum(1 for s in successors if G.nodes[s].get("node_type") == "function")
            file_lines.append(
                f"  {attrs.get('label', node)}: {n_cls} class(es), {n_fn} function(s)"
            )

    lines = [
        "=== Code Knowledge Graph ===",
        f"Nodes : {G.number_of_nodes()}",
        f"Edges : {G.number_of_edges()}",
        "By type:",
        *[f"  {t:<12}: {c}" for t, c in sorted(type_counts.items())],
        "\nFiles:",
        *sorted(file_lines),
    ]
    return "\n".join(lines)


def get_graph_rag_tools() -> list:
    """Return all GraphRAG LangChain tools."""
    return [query_code_graph, summarise_code_graph]
