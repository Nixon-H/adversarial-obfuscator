"""
diagram_generator.py

Purpose:
Generates Mermaid.js diagrams for build artifacts: architecture
diagrams (module pipeline), protection flowcharts (coverage heatmaps),
attack surface diagrams (attack-target-mitigation graphs), and
before/after comparison charts.

Architectural Role:
Visualization layer of the artifacts module. Each function produces
a Mermaid.js diagram string (and optionally writes it to a .mmd file).

Execution Context:
Called by ArtifactBuilder._generate_diagrams() during artifact
generation. Diagrams are written to build/artifacts/diagrams/.

Dependencies:
- Standard library only (os)

Security Relevance:
Diagrams provide visual documentation of the protection architecture,
coverage status, and attack surface. They are used in reports and
presentations to communicate security posture.

Maintenance Notes:
- Output format is Mermaid.js (https://mermaid.js.org/). These .mmd
  files can be rendered by GitHub, GitLab, or the mermaid-cli tool.
- The color scheme uses category-based CSS classes (obfuscation,
  proof, metric, attack, analysis, hardware, runtime).
- The architecture diagram uses a linear pipeline layout; for
  branching pipelines, the Mermaid subgraph feature could be used.
"""

from __future__ import annotations

import os


def _color_for_category(category: str) -> str:
    mapping = {
        "obfuscation": "#4a90d9",
        "proof": "#7ed321",
        "metric": "#f5a623",
        "attack": "#d0021b",
        "analysis": "#9013fe",
        "hardware": "#50e3c2",
        "runtime": "#bd10e0",
        "default": "#9b9b9b",
    }
    return mapping.get(category, mapping["default"])


def generate_architecture_diagram(
    modules: list[dict], output_path: str | None = None
) -> str:
    lines = ["graph TD"]
    lines.append("    classDef obfuscation fill:#4a90d9,stroke:#fff,color:#fff")
    lines.append("    classDef proof fill:#7ed321,stroke:#fff,color:#fff")
    lines.append("    classDef metric fill:#f5a623,stroke:#fff,color:#fff")
    lines.append("    classDef attack fill:#d0021b,stroke:#fff,color:#fff")
    lines.append("    classDef analysis fill:#9013fe,stroke:#fff,color:#fff")
    lines.append("    classDef hardware fill:#50e3c2,stroke:#333,color:#333")
    lines.append("    classDef runtime fill:#bd10e0,stroke:#fff,color:#fff")

    input_id = "input_payload"
    lines.append(f"    {input_id}[\"Input Payload\"]")
    lines.append(f"    style {input_id} fill:#fcfcfc,stroke:#333,stroke-width:2px")

    prev_id = input_id
    stage_num = 0
    for mod in modules:
        stage_num += 1
        node_id = f"stage{stage_num}_{mod.get('name', f'mod_{stage_num}')}"
        label = mod.get("label", mod.get("name", f"Stage {stage_num}"))
        cat = mod.get("category", "default")
        lines.append(f"    {node_id}[\"{label}\"]")
        lines.append(f"    class {node_id} {cat}")
        lines.append(f"    {prev_id} --> {node_id}")
        prev_id = node_id

    output_id = "output_artifact"
    lines.append(f"    {output_id}[\"Protected Output\"]")
    lines.append(f"    style {output_id} fill:#2ecc71,stroke:#fff,color:#fff")
    lines.append(f"    {prev_id} --> {output_id}")

    diagram = "\n".join(lines)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(diagram)

    return diagram


def generate_protection_flowchart(
    coverage_map: dict, output_path: str | None = None
) -> str:
    lines = ["graph LR"]
    lines.append("    classDef covered fill:#2ecc71,stroke:#fff,color:#fff")
    lines.append("    classDef partial fill:#f5a623,stroke:#fff,color:#fff")
    lines.append("    classDef uncovered fill:#e74c3c,stroke:#fff,color:#fff")

    functions = coverage_map.get("functions", {})
    if not functions:
        lines.append("    empty[\"No functions in coverage map\"]")
        diagram = "\n".join(lines)
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w") as f:
                f.write(diagram)
        return diagram

    func_ids = []
    for i, (fname, fdata) in enumerate(sorted(functions.items())):
        node_id = f"func_{i}"
        func_ids.append(node_id)
        prot = fdata.get("protections", {})
        covered_count = sum(1 for v in prot.values() if v)
        total = max(len(prot), 1)
        pct = covered_count / total
        if pct >= 0.8:
            cls = "covered"
        elif pct >= 0.3:
            cls = "partial"
        else:
            cls = "uncovered"
        detail = fdata.get("uncovered_paths", [])
        suffix = f" ({covered_count}/{total})"
        if detail:
            suffix += " ⚠"
        lines.append(f'    {node_id}["{fname}{suffix}"]')
        lines.append(f"    class {node_id} {cls}")

    for i in range(1, len(func_ids)):
        lines.append(f"    {func_ids[i-1]} --> {func_ids[i]}")

    per_prot = coverage_map.get("per_protection_stats", {})
    if per_prot:
        lines.append("    subgraph Protection_Heatmap")
        for pname, pdata in sorted(per_prot.items()):
            ratio = pdata.get("coverage_ratio", 0)
            pid = f"prot_{pname.lower().replace(' ', '_')}"
            if ratio >= 0.8:
                pcls = "covered"
            elif ratio >= 0.3:
                pcls = "partial"
            else:
                pcls = "uncovered"
            lines.append(f'    {pid}["{pname}: {ratio:.0%}"]')
            lines.append(f"    class {pid} {pcls}")
        lines.append("    end")

    diagram = "\n".join(lines)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(diagram)

    return diagram


def generate_attack_surface_diagram(
    knowledge_graph: dict, output_path: str | None = None
) -> str:
    lines = ["graph TB"]
    lines.append("    classDef attack fill:#d0021b,stroke:#fff,color:#fff")
    lines.append("    classDef target fill:#4a90d9,stroke:#fff,color:#fff")
    lines.append("    classDef mitigation fill:#7ed321,stroke:#fff,color:#fff")

    attacks = knowledge_graph.get("attack_vectors", [])
    targets = knowledge_graph.get("targets", [])
    mitigations = knowledge_graph.get("mitigations", [])

    if not attacks:
        lines.append('    empty["No attack vectors found"]')
        diagram = "\n".join(lines)
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w") as f:
                f.write(diagram)
        return diagram

    for i, attack in enumerate(attacks):
        aid = f"attack_{i}"
        aname = attack.get("name", f"Attack {i}")
        severity = attack.get("severity", "unknown")
        lines.append(f'    {aid}["{aname} ({severity})"]')
        lines.append(f"    class {aid} attack")

    for j, target in enumerate(targets):
        tid = f"target_{j}"
        tname = target.get("name", f"Target {j}")
        lines.append(f'    {tid}["{tname}"]')
        lines.append(f"    class {tid} target")

    for k, mitigation in enumerate(mitigations):
        mid = f"mitigation_{k}"
        mname = mitigation.get("name", f"Mitigation {k}")
        lines.append(f'    {mid}["{mname}"]')
        lines.append(f"    class {mid} mitigation")

    attack_target_map = knowledge_graph.get("attack_target_map", {})
    for attack_idx_str, target_indices in attack_target_map.items():
        aid = f"attack_{attack_idx_str}"
        for ti in target_indices:
            tid = f"target_{ti}"
            lines.append(f"    {aid} -->|attacks| {tid}")

    mitigation_map = knowledge_graph.get("mitigation_map", {})
    for attack_idx_str, mit_indices in mitigation_map.items():
        aid = f"attack_{attack_idx_str}"
        for mi in mit_indices:
            mid = f"mitigation_{mi}"
            lines.append(f"    {mid} -->|mitigates| {aid}")

    diagram = "\n".join(lines)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(diagram)

    return diagram


def generate_comparison_chart(
    before_metrics: dict,
    after_metrics: dict,
    output_path: str | None = None,
) -> str:
    lines = ["gantt"]
    lines.append("    title Before/After Protection Comparison")
    lines.append("    dateFormat  X")
    lines.append("    axisFormat  %s")

    metrics = ["entropy", "cyclomatic_complexity", "instruction_count",
               "string_count", "function_count", "branch_count"]

    for metric in metrics:
        before_val = before_metrics.get(metric, 0)
        after_val = after_metrics.get(metric, 0)
        scaled_before = max(int(before_val * 10), 1)
        scaled_after = max(int(after_val * 10), 1)
        lines.append(f'    section {metric}')
        lines.append(f'    Before : 0, {scaled_before}')
        lines.append(f'    After  : 0, {scaled_after}')

    diagram = "\n".join(lines)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(diagram)

    return diagram
