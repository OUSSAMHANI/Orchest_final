"""Pure graph construction logic — zero LangChain dependency (SRP / DIP).

Builds a directed NetworkX graph from AST symbol data so the
graph structure can be tested and reasoned about independently of
any LLM tooling.

Node types
----------
- ``file``     — a Python source file
- ``class``    — a class definition inside a file
- ``function`` — a top-level function inside a file
- ``method``   — a method inside a class
- ``module``   — an imported module name

Edge relations
--------------
- ``imports``  — file → module
- ``defines``  — file → class | function,  class → method
"""
import glob
import os

import networkx as nx

from src.tools.ast_analysis.parser import parse_file


def build_code_graph(workspace_path: str) -> nx.DiGraph:
    """
    Walk every ``.py`` file under *workspace_path* and build a directed
    knowledge graph encoding the code structure.

    Args:
        workspace_path: Root directory to scan recursively.

    Returns:
        A ``networkx.DiGraph`` populated with typed nodes and labelled edges.
    """
    G: nx.DiGraph = nx.DiGraph()
    pattern = os.path.join(os.path.abspath(workspace_path), "**", "*.py")

    for fp in glob.glob(pattern, recursive=True):
        symbols = parse_file(fp)
        if "error" in symbols:
            continue

        # ---- file node -------------------------------------------------------
        G.add_node(fp, node_type="file", label=os.path.basename(fp))

        # ---- import edges ----------------------------------------------------
        for imp in symbols.get("imports", []):
            imp_node = f"import::{imp}"
            G.add_node(imp_node, node_type="module", label=imp)
            G.add_edge(fp, imp_node, relation="imports")

        # ---- top-level function nodes ----------------------------------------
        for func in symbols.get("top_level_functions", []):
            fn_node = f"fn::{fp}::{func['name']}"
            G.add_node(
                fn_node,
                node_type="function",
                label=func["name"],
                parent_file=fp,
                lineno=func["lineno"],
            )
            G.add_edge(fp, fn_node, relation="defines")

        # ---- class + method nodes -------------------------------------------
        for cls in symbols.get("classes", []):
            cls_node = f"cls::{fp}::{cls['name']}"
            G.add_node(
                cls_node,
                node_type="class",
                label=cls["name"],
                parent_file=fp,
                lineno=cls["lineno"],
            )
            G.add_edge(fp, cls_node, relation="defines")

            for method in cls.get("methods", []):
                m_node = f"method::{fp}::{cls['name']}::{method['name']}"
                G.add_node(
                    m_node,
                    node_type="method",
                    label=method["name"],
                    parent_class=cls["name"],
                    parent_file=fp,
                    lineno=method["lineno"],
                )
                G.add_edge(cls_node, m_node, relation="defines")

    return G
