from __future__ import annotations

from typing import Dict, List, Tuple, Any

from ..script.model import Program


def build_flow_graph(program: Program) -> Dict[str, Any]:
    """Build a simple label-level flow graph from the Program.

    Nodes: label names (plus a virtual "__start__").
    Edges: from current label to choice targets in its block, or to next label by default.
    Returns dict with keys: nodes (List[str]), edges (List[dict]), order (List[str]).
    """
    labels = program.labels or {}
    inv_labels: Dict[int, str] = {ip: name for name, ip in labels.items()}
    order: List[Tuple[str, int]] = sorted(((name, ip) for name, ip in labels.items()), key=lambda x: x[1])
    nodes: List[str] = [name for name, _ in order]
    edges: List[Dict[str, Any]] = []

    # Helper: find next label index after given op index
    def next_label_after(ip: int) -> str | None:
        for i in range(ip + 1, len(program.ops)):
            if i in inv_labels:
                return inv_labels[i]
        return None

    # Add start edge to the first label if present
    if order:
        edges.append({"src": "__start__", "dst": order[0][0], "kind": "start"})

    # For each label, scan until next label for choices
    for name, ip in order:
        i = ip + 1
        made_choice_edges = False
        while i < len(program.ops) and i not in inv_labels:
            op = program.ops[i]
            if op.kind == "choice":
                # Gather contiguous choices
                made_choice_edges = True
                while i < len(program.ops) and program.ops[i].kind == "choice":
                    ch = program.ops[i].payload
                    tgt = ch.get("target")
                    if tgt and tgt in labels:
                        edges.append({"src": name, "dst": tgt, "kind": "choice"})
                    i += 1
                break
            i += 1
        if not made_choice_edges:
            nxt = next_label_after(ip)
            if nxt:
                edges.append({"src": name, "dst": nxt, "kind": "next"})

    return {"nodes": nodes, "edges": edges, "order": [n for n, _ in order]}
