###############################################################################
# PrOMMiS was produced under the DOE Process Optimization and Modeling
# for Minerals Sustainability (“PrOMMiS”) initiative, and is
# Copyright © 2024-2025 by the software owners: The Regents of the
# University of California, through Lawrence Berkeley National
# Laboratory, National Technology & Engineering Solutions of Sandia, LLC,
# Carnegie Mellon University, West Virginia University Research
# Corporation, University of Notre Dame, and Georgia Institute of
# Technology. All rights reserved.
###############################################################################
"""
Jupyter Notebook utilities
"""
# stdlib
from typing import Dict
from warnings import warn

# third-party
from IPython.display import Markdown

# package
from idaes_connectivity.base import Connectivity, Mermaid


def display_connectivity(
    conn: Connectivity = None,
    input_model=None,
    mermaid_options: Dict = None,
    jb=False,
) -> Markdown:
    """Display connectivity in a Jupyter Notebook using the built-in MermaidJS capabilities.
    Requires JupyterLab >= 4.1 or Jupyter Notebook >= 7.1.

    Args:
        conn: Constructed Connectivity of a model
        input_model: If present, create Connectivity instance from this model instead
        mermaid_options: Keyword args for {py:class}`idaes_connectivity.base.Mermaid`
        jb: Workaround for rendering in Jupyterbook

    Returns:
        Markdown object, containing Mermaid graph, for Jupyter Notebook to render
    """
    if input_model is not None:
        conn = Connectivity(input_model=input_model)
    if conn is None:
        warn("Nothing to display")
        return None
    mm_opt = mermaid_options or {}
    mermaid = Mermaid(conn, **mm_opt)
    graph_str = mermaid.write(None)
    if jb:
        return _mm(graph_str)
    else:
        graph_text = f"```mermaid\n{graph_str}\n```"
        return Markdown(graph_text)


def _mm(text):
    from mermaid import Mermaid as M

    return M(text)
