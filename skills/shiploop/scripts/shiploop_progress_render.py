"""Render a saved ShipLoop progress snapshot as a self-contained HTML page."""

from __future__ import annotations

from collections import deque
from html import escape
import json
import math
from textwrap import wrap
from typing import Any, Mapping
from urllib.parse import quote, urlsplit, urlunsplit


_PHASES = ("Preparation", "Work items", "Release")
_STATUS_CLASSES = {
    "active": "active",
    "awaiting": "awaiting",
    "blocked": "blocked",
    "done": "done",
    "halted": "halted",
    "paused": "paused",
}
_DOC_STATUS_LABELS = {
    "accepted-result": "Accepted result",
    "draft": "Draft",
    "missing": "Missing",
    "withheld": "Withheld",
}


def _e(value: Any, default: str = "") -> str:
    if value is None:
        value = default
    return escape(str(value), quote=True)


def _value(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, (bool, int, float)):
        return str(value)
    if isinstance(value, Mapping):
        for key in ("text", "summary", "headline", "label"):
            candidate = value.get(key)
            if candidate is not None:
                return str(candidate)
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if isinstance(value, (list, tuple)):
        return "; ".join(_value(item) for item in value)
    return str(value)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return result if math.isfinite(result) else default


def _local_file_uri(value: Any) -> str | None:
    """Return a normalized local file URI, rejecting every other scheme/host."""
    if not isinstance(value, str) or not value or any(ord(char) < 32 for char in value):
        return None
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return None
    if parts.scheme.lower() != "file" or parts.netloc.lower() not in ("", "localhost"):
        return None
    if not parts.path.startswith("/"):
        return None
    path = quote(parts.path, safe="/%:@!$&'()*+,;=-._~")
    query = quote(parts.query, safe="/?%:@!$&'()*+,;=-._~")
    fragment = quote(parts.fragment, safe="/?%:@!$&'()*+,;=-._~")
    return urlunsplit(("file", "", path, query, fragment))


def _phase_rows(facts: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    incoming = facts.get("phases", [])
    by_name = {
        _value(row.get("name")).casefold(): row
        for row in incoming
        if isinstance(row, Mapping)
    } if isinstance(incoming, (list, tuple)) else {}
    return [
        by_name.get(name.casefold(), {
            "name": name, "done": 0, "done_label": 0, "total": 0, "state": "pending",
        })
        for name in _PHASES
    ]


def _phase_card(row: Mapping[str, Any], index: int, plan_accepted: bool) -> str:
    name = _value(row.get("name"), _PHASES[index])
    phase_key = name.casefold()
    state = _value(row.get("state"), "pending").casefold()
    if state not in ("done", "current"):
        state = "pending"
    total = max(0, _number(row.get("total")))
    done = max(0.0, _number(row.get("done")))
    if total > 0:
        done = min(done, total)
        percent = min(100.0, 100.0 * done / total)
    else:
        percent = 100.0 if state == "done" else 0.0

    if phase_key == "work items" and not plan_accepted:
        progress = "Plan pending"
        state = "pending"
        percent = 0.0
    elif state == "done":
        progress = "Complete"
    elif total > 0 and phase_key == "work items":
        progress = f"{_value(row.get('done_label'), '0')}/{_value(row.get('total'))} items"
    elif total > 0:
        progress = f"{_value(row.get('done_label'), '0')}/{_value(row.get('total'))} steps"
    elif state == "current":
        progress = "In progress"
    else:
        progress = "Pending"

    return (
        '<article class="phase-card phase-' + state + '">'
        '<div class="phase-top"><span class="phase-number">0' + str(index + 1) + '</span>'
        '<span class="phase-state">' + _e(progress) + '</span></div>'
        '<h3>' + _e(name) + '</h3>'
        '<div class="meter" role="progressbar" aria-label="' + _e(name)
        + ' progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'
        + str(round(percent)) + '"><span style="width:' + str(round(percent)) + '%"></span></div>'
        '</article>'
    )


def _narrative(snapshot: Mapping[str, Any], facts: Mapping[str, Any]) -> str:
    run = snapshot.get("run")
    run = run if isinstance(run, Mapping) else {}
    stop = facts.get("stop")
    if isinstance(stop, Mapping):
        title = "Run status"
        label = _value(stop.get("kind"), "Stopped")
        text = _value(stop.get("text"))
    else:
        now = facts.get("now")
        now = now if isinstance(now, Mapping) else {}
        title = "Current focus"
        label = _value(now.get("label"), _value(run.get("stage"), "Unknown"))
        text = _value(now.get("text"))

    parts = [
        '<section class="panel narrative-panel" aria-labelledby="narrative-heading">',
        '<div class="section-heading"><div><p class="eyebrow">RUN NARRATIVE</p>'
        '<h2 id="narrative-heading">' + _e(title) + '</h2></div></div>',
        '<div class="focus-row"><span class="focus-label">' + _e(label) + '</span>'
        '<p>' + (_e(text) if text else '<span class="muted">No additional detail recorded.</span>') + '</p></div>',
    ]
    achieved = facts.get("achieved", [])
    if isinstance(achieved, (list, tuple)) and achieved:
        parts.append('<div class="narrative-list"><h3>Achieved</h3><ul>')
        for row in achieved:
            if not isinstance(row, Mapping):
                continue
            text = _value(row.get("text"))
            parts.append('<li><strong>' + _e(row.get("label")) + '</strong>')
            if text:
                parts.append('<span>' + _e(text) + '</span>')
            parts.append('</li>')
        parts.append('</ul></div>')
    ahead = facts.get("ahead", [])
    if isinstance(ahead, (list, tuple)) and ahead:
        parts.append('<div class="narrative-list"><h3>Ahead</h3><ul>')
        for row in ahead:
            if not isinstance(row, Mapping):
                continue
            parts.append('<li><strong>' + _e(row.get("label")) + '</strong>')
            if row.get("text"):
                parts.append('<span>' + _e(row.get("text")) + '</span>')
            parts.append('</li>')
        parts.append('</ul></div>')
    parts.append('</section>')
    return "".join(parts)


def _work_items(snapshot: Mapping[str, Any]) -> str:
    rows = snapshot.get("work_items", [])
    rows = rows if isinstance(rows, (list, tuple)) else []
    plan_accepted = bool(snapshot.get("plan_accepted"))
    parts = [
        '<section class="panel" aria-labelledby="work-heading">',
        '<div class="section-heading"><div><p class="eyebrow">PLAN</p>'
        '<h2 id="work-heading">Work items</h2></div>',
        '<span class="small-note">' + ("Plan accepted" if plan_accepted else "Plan pending") + '</span></div>',
    ]
    if not plan_accepted:
        parts.append('<p class="empty-state">The plan is pending; work items have not been accepted yet.</p>')
    elif not rows:
        parts.append('<p class="empty-state">The accepted plan has no work items.</p>')
    else:
        parts.append('<div class="work-list">')
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            status = _value(row.get("status"), "unspecified")
            state_class = status.lower() if status.lower() in {
                "active", "blocked", "done", "pending", "queued", "skipped",
            } else "other"
            dependencies = row.get("dependencies", [])
            if not isinstance(dependencies, (list, tuple)):
                dependencies = []
            plan = _value(row.get("plan"))
            parts.append(
                '<article class="work-card"><div class="work-heading"><div>'
                '<span class="work-id">' + _e(row.get("id"), "Item") + '</span>'
                '<h3>' + _e(row.get("title"), "Untitled work item") + '</h3></div>'
                '<span class="pill pill-' + state_class + '">' + _e(status) + '</span></div>'
            )
            if plan:
                parts.append('<p class="work-plan">' + _e(plan) + '</p>')
            if dependencies:
                parts.append('<p class="dependencies"><span>Depends on</span> ')
                parts.append(", ".join(_e(item) for item in dependencies))
                parts.append('</p>')
            parts.append('</article>')
        parts.append('</div>')
    parts.append('</section>')
    return "".join(parts)


def _svg_lines(value: Any, *, width: int, max_lines: int) -> list[str]:
    lines = wrap(_value(value), width=width, max_lines=max_lines, placeholder="…")
    return lines or [""]


def _graph_model(graph: Mapping[str, Any]) -> tuple[
    list[Mapping[str, Any]], list[str], list[tuple[int, int]], list[int], list[str], bool
]:
    raw_nodes = graph.get("nodes", [])
    nodes = [node for node in raw_nodes if isinstance(node, Mapping)] \
        if isinstance(raw_nodes, (list, tuple)) else []
    diagnostics: list[str] = []
    if isinstance(raw_nodes, (list, tuple)) and len(nodes) != len(raw_nodes):
        diagnostics.append("Ignored a malformed step entry.")

    node_ids = [_value(node.get("id")).strip() for node in nodes]
    positions: dict[str, list[int]] = {}
    for index, node_id in enumerate(node_ids):
        if node_id:
            positions.setdefault(node_id, []).append(index)
        else:
            diagnostics.append(f"Step {index + 1} has no ID.")
    for node_id, matches in positions.items():
        if len(matches) > 1:
            diagnostics.append(f"Duplicate step ID {_value(node_id)!r} makes dependency links ambiguous.")
    unique_ids = {node_id: matches[0] for node_id, matches in positions.items() if len(matches) == 1}
    display_ids = [
        node_id or f"Step {index + 1}"
        for index, node_id in enumerate(node_ids)
    ]

    dependencies_known = bool(graph.get("dependencies_known", False))
    raw_edges = graph.get("edges", [])
    raw_edges = raw_edges if isinstance(raw_edges, (list, tuple)) else []
    edges: list[tuple[int, int]] = []
    if not dependencies_known and raw_edges:
        diagnostics.append("Dependency edges were omitted because dependency data is marked unknown.")
    elif dependencies_known:
        seen: set[tuple[int, int]] = set()
        for edge in raw_edges:
            if not isinstance(edge, Mapping):
                diagnostics.append("Ignored a malformed dependency edge.")
                continue
            source = _value(edge.get("from")).strip()
            target = _value(edge.get("to")).strip()
            if not source or not target:
                diagnostics.append("Ignored a dependency edge with a missing endpoint.")
                continue
            missing = [node_id for node_id in (source, target) if node_id not in positions]
            ambiguous = [node_id for node_id in (source, target)
                         if node_id in positions and len(positions[node_id]) > 1]
            if missing:
                diagnostics.append(
                    f"Ignored edge {source} → {target}; missing step ID(s): {', '.join(missing)}."
                )
                continue
            if ambiguous:
                diagnostics.append(
                    f"Ignored edge {source} → {target}; ambiguous step ID(s): {', '.join(ambiguous)}."
                )
                continue
            pair = (unique_ids[source], unique_ids[target])
            if pair not in seen:
                edges.append(pair)
                seen.add(pair)

    outgoing: list[list[int]] = [[] for _ in nodes]
    indegree = [0] * len(nodes)
    for source, target in edges:
        outgoing[source].append(target)
        indegree[target] += 1
    ranks = [0] * len(nodes)
    if dependencies_known:
        remaining_indegree = indegree[:]
        ready = deque(index for index, degree in enumerate(remaining_indegree) if degree == 0)
        ordered: list[int] = []
        while ready:
            source = ready.popleft()
            ordered.append(source)
            for target in outgoing[source]:
                ranks[target] = max(ranks[target], ranks[source] + 1)
                remaining_indegree[target] -= 1
                if remaining_indegree[target] == 0:
                    ready.append(target)
        unresolved = [index for index, degree in enumerate(remaining_indegree) if degree > 0]
        if unresolved:
            names = ", ".join(display_ids[index] for index in unresolved[:8])
            extra = f" and {len(unresolved) - 8} more" if len(unresolved) > 8 else ""
            diagnostics.append(
                "Cycle detected or cycle-dependent steps remain after topological ordering: "
                + names + extra + ". Those steps are grouped at the end."
            )
            final_rank = max((ranks[index] for index in ordered), default=-1) + 1
            for index in unresolved:
                ranks[index] = final_rank
    return nodes, display_ids, edges, ranks, diagnostics, dependencies_known


def _graph_svg(
    graph_index: int,
    label: str,
    nodes: list[Mapping[str, Any]],
    display_ids: list[str],
    edges: list[tuple[int, int]],
    ranks: list[int],
    dependencies_known: bool,
) -> str:
    if not nodes:
        return '<p class="empty-state">The accepted graph contains no implementation steps.</p>'

    node_width, node_height = 204, 112
    gap_x, gap_y = 82, 34
    margin_x, margin_y = 28, 28
    if dependencies_known:
        layers: dict[int, list[int]] = {}
        for index, rank in enumerate(ranks):
            layers.setdefault(rank, []).append(index)
        layer_rows = [layers[key] for key in sorted(layers)]
        layer_by_node = {node: layer for layer, row in enumerate(layer_rows) for node in row}
        row_by_node = {node: row for row, layer in enumerate(layer_rows) for node in layer}
    else:
        columns = min(3, max(1, math.ceil(math.sqrt(len(nodes)))))
        layer_rows = []
        for index in range(0, len(nodes), columns):
            layer_rows.append(list(range(index, min(index + columns, len(nodes)))))
        layer_by_node = {node: node % columns for node in range(len(nodes))}
        row_by_node = {node: node // columns for node in range(len(nodes))}

    positions: dict[int, tuple[int, int]] = {}
    for node_index in range(len(nodes)):
        x = margin_x + layer_by_node[node_index] * (node_width + gap_x)
        y = margin_y + row_by_node[node_index] * (node_height + gap_y)
        positions[node_index] = (x, y)
    max_col = max(layer_by_node.values(), default=0)
    max_row = max(row_by_node.values(), default=0)
    width = max(620, margin_x * 2 + (max_col + 1) * node_width + max_col * gap_x)
    height = margin_y * 2 + (max_row + 1) * node_height + max_row * gap_y
    marker_id = f"dependency-arrow-{graph_index}"
    parts = [
        '<div class="graph-viewport" role="region" tabindex="0" aria-label="Scrollable dependency graph">'
        '<svg class="dependency-svg" role="img" aria-labelledby="graph-title-' + str(graph_index)
        + ' graph-desc-' + str(graph_index) + '" viewBox="0 0 ' + str(width) + ' ' + str(height)
        + '" width="' + str(width) + '" height="' + str(height) + '">'
        '<title id="graph-title-' + str(graph_index) + '">' + _e(label) + ' implementation dependencies</title>'
        '<desc id="graph-desc-' + str(graph_index) + '">Arrows point from prerequisites to dependent steps.'
        + (' Dependencies are not recorded; node positions do not imply order.' if not dependencies_known else '')
        + '</desc><defs><marker id="' + marker_id
        + '" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" viewBox="0 0 8 8">'
        '<path d="M0,0 L8,4 L0,8 z" fill="#5d806c"/></marker></defs>',
    ]
    if dependencies_known:
        for source, target in edges:
            sx, sy = positions[source]
            tx, ty = positions[target]
            start_x, start_y = sx + node_width, sy + node_height // 2
            end_x, end_y = tx, ty + node_height // 2
            forward = ranks[target] > ranks[source]
            if forward:
                mid_x = (start_x + end_x) // 2
                path = f"M {start_x} {start_y} C {mid_x} {start_y}, {mid_x} {end_y}, {end_x} {end_y}"
                edge_class = "dependency-edge"
            else:
                high_x = max(start_x, end_x) + 46
                path = f"M {start_x} {start_y} C {high_x} {start_y - 44}, {high_x} {end_y - 44}, {end_x} {end_y}"
                edge_class = "dependency-edge dependency-cycle-edge"
            parts.append(
                '<path class="' + edge_class + '" d="' + path + '" marker-end="url(#'
                + marker_id + ')"/>'
            )
    for index, node in enumerate(nodes):
        x, y = positions[index]
        status = _value(node.get("status"), "unspecified")
        status_key = status.lower().replace("_", "-")
        status_class = status_key if status_key in {
            "active", "blocked", "current", "done", "pending", "queued", "accepted",
        } else "other"
        title = _value(node.get("title"), _value(node.get("task"), "Untitled step"))
        action = _value(node.get("action"), _value(node.get("stage")))
        workitem = _value(node.get("workitem"))
        heading = display_ids[index]
        if workitem:
            heading += " · " + workitem
        if action:
            heading += " · " + action
        title_lines = _svg_lines(title, width=25, max_lines=2)
        parts.append(
            '<g class="graph-node status-' + status_class + '"><rect x="' + str(x) + '" y="' + str(y)
            + '" width="' + str(node_width) + '" height="' + str(node_height) + '" rx="11"/>'
            '<text class="graph-node-id" x="' + str(x + 13) + '" y="' + str(y + 23) + '">'
            + _e(_svg_lines(heading, width=27, max_lines=1)[0]) + '</text>'
            '<text class="graph-node-title" x="' + str(x + 13) + '" y="' + str(y + 48) + '">'
            + "".join('<tspan x="' + str(x + 13) + '" dy="' + ("0" if line_index == 0 else "17")
                      + '">' + _e(line) + '</tspan>'
                      for line_index, line in enumerate(title_lines))
            + '</text><text class="graph-node-status" x="' + str(x + 13) + '" y="' + str(y + 98)
            + '">' + _e(status) + '</text></g>'
        )
    parts.append('</svg></div>')
    if dependencies_known and not edges:
        parts.append('<p class="graph-note">No dependency edges were recorded in this accepted graph.</p>')
    elif not dependencies_known:
        parts.append('<p class="graph-note">Dependencies were not recorded; node positions do not imply order.</p>')
    return "".join(parts)


def _graph_text(nodes: list[Mapping[str, Any]], display_ids: list[str], edges: list[tuple[int, int]],
                dependencies_known: bool, state_key: str) -> str:
    if not nodes:
        return ""
    incoming: list[list[int]] = [[] for _ in nodes]
    for source, target in edges:
        incoming[target].append(source)
    parts = [
        '<details class="graph-text" data-state-key="' + _e(state_key) + '" open>'
        '<summary>Text dependency list · ' + str(len(nodes)) + ' steps</summary><ul>',
    ]
    for index, node in enumerate(nodes):
        title = _value(node.get("title"), _value(node.get("task"), "Untitled step"))
        status = _value(node.get("status"), "unspecified")
        plan = _value(node.get("plan"))
        action = _value(node.get("action"), _value(node.get("stage")))
        workitem = _value(node.get("workitem"))
        parts.append('<li><strong>' + _e(display_ids[index]) + '</strong>')
        parts.append(' — ' + _e(title))
        if workitem:
            parts.append(' <span class="graph-text-meta">(' + _e(workitem) + ')</span>')
        if action:
            parts.append(' <span class="graph-text-meta">(' + _e(action) + ')</span>')
        parts.append('<span class="graph-text-meta"> · Status: ' + _e(status) + '</span>')
        if plan:
            parts.append('<p class="graph-plan">' + _e(plan) + '</p>')
        if dependencies_known:
            prerequisites = incoming[index]
            if prerequisites:
                parts.append('<p class="graph-dependencies"><strong>Depends on:</strong> '
                             + ", ".join(_e(display_ids[source]) for source in prerequisites) + '</p>')
            else:
                parts.append('<p class="graph-dependencies">No prerequisites recorded.</p>')
        else:
            parts.append('<p class="graph-dependencies">Dependencies not recorded; order is unknown.</p>')
        parts.append('</li>')
    parts.append('</ul></details>')
    return "".join(parts)


def _dependency_graphs(snapshot: Mapping[str, Any]) -> str:
    raw_graphs = snapshot.get("graphs", [])
    graphs = raw_graphs if isinstance(raw_graphs, (list, tuple)) else []
    parts = [
        '<section class="panel dependency-panel" aria-labelledby="dependency-heading">'
        '<div class="section-heading"><div><p class="eyebrow">GENERATED IMPLEMENTATION</p>'
        '<h2 id="dependency-heading">Steps and dependencies</h2></div></div>',
        '<p class="graph-intro">Arrows point from a prerequisite to the step that depends on it. '
        'Only accepted generated graphs are drawn.</p>',
    ]
    usable = [graph for graph in graphs if isinstance(graph, Mapping)]
    if not usable:
        parts.append('<p class="empty-state">No accepted generated graph is available. '
                     'Implementation steps will appear here after a generated graph is accepted.</p>')
    for index, graph in enumerate(graphs):
        if not isinstance(graph, Mapping):
            parts.append('<p class="graph-diagnostic">Ignored a malformed graph entry.</p>')
            continue
        label = _value(graph.get("label"), f"Generated graph {index + 1}")
        state = _value(graph.get("status"), "unavailable").lower()
        state_label = state.replace("-", " ").title()
        parts.append('<article class="graph-group"><div class="graph-group-heading">'
                     '<h3>' + _e(label) + '</h3><span class="pill pill-' +
                     ("accepted" if state == "accepted" else "other") + '">' + _e(state_label) +
                     '</span></div>')
        if state != "accepted":
            message = {
                "draft": "A generated graph draft exists but is not accepted; its steps are not shown as implementation work.",
                "unavailable": "Graph data is unavailable for this scope.",
            }.get(state, "Graph status is unknown; no implementation steps are displayed.")
            if graph.get("reason"):
                message += " " + _value(graph.get("reason"))
            parts.append('<p class="empty-state">' + _e(message) + '</p></article>')
            continue

        nodes, display_ids, edges, ranks, diagnostics, dependencies_known = _graph_model(graph)
        parts.append(_graph_svg(index, label, nodes, display_ids, edges, ranks, dependencies_known))
        stable_key = _value(graph.get("id"), _value(graph.get("label"), "graph-" + str(index)))
        if nodes:
            parts.append(_graph_text(nodes, display_ids, edges, dependencies_known,
                                     "graph-text-" + stable_key))
        if diagnostics:
            parts.append('<ul class="graph-diagnostics" aria-label="Graph diagnostics">'
                         + "".join('<li>' + _e(message) + '</li>' for message in diagnostics)
                         + '</ul>')
        parts.append('</article>')
    parts.append('</section>')
    return "".join(parts)


def _documents(snapshot: Mapping[str, Any]) -> str:
    rows = snapshot.get("documents", [])
    rows = rows if isinstance(rows, (list, tuple)) else []
    parts = [
        '<section class="panel" aria-labelledby="documents-heading">',
        '<div class="section-heading"><div><p class="eyebrow">EVIDENCE</p>'
        '<h2 id="documents-heading">Key files</h2></div></div>',
    ]
    if not rows:
        parts.append('<p class="empty-state">No files were included in this snapshot.</p>')
    else:
        parts.append('<div class="document-list">')
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                continue
            title = _value(row.get("title"), _value(row.get("path"), "Untitled document"))
            status = _value(row.get("status"), "unknown").lower()
            label = _DOC_STATUS_LABELS.get(status, status or "Unknown")
            state_key = "doc-" + _value(row.get("id"), str(index))
            parts.append(
                '<details class="document" data-state-key="' + _e(state_key) + '">'
                '<summary><span class="document-title">' + _e(title) + '</span>'
                '<span class="pill pill-' + ("accepted" if status == "accepted-result" else "other")
                + '">' + _e(label) + '</span></summary><div class="document-body">'
            )
            if row.get("summary"):
                parts.append('<p class="document-summary">' + _e(row.get("summary")) + '</p>')
            path = _value(row.get("path"))
            if path:
                parts.append('<p class="file-path"><span>Path</span> ' + _e(path) + '</p>')
            href = _local_file_uri(row.get("uri"))
            if href:
                parts.append('<p><a class="file-link" href="' + _e(href) + '">Open local source</a></p>')
            acceptance = _value(row.get("acceptance"))
            if acceptance:
                parts.append('<p class="document-summary"><strong>Acceptance</strong> '
                             + _e(acceptance) + '</p>')
            error = _value(row.get("error"))
            if error:
                parts.append('<p class="document-error">' + _e(error) + '</p>')
            sha256 = _value(row.get("sha256"))
            if sha256:
                parts.append('<p class="file-path"><span>SHA-256</span> <code>' + _e(sha256) + '</code></p>')
            content = _value(row.get("content"))
            if content:
                parts.append('<pre class="preview" tabindex="0">' + _e(content) + '</pre>')
            else:
                parts.append('<p class="empty-state">No inline preview is available.</p>')
            parts.append('</div></details>')
        parts.append('</div>')
    parts.append('</section>')
    return "".join(parts)


def _activity(snapshot: Mapping[str, Any]) -> tuple[str, str]:
    rows = snapshot.get("activity", [])
    rows = [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, (list, tuple)) else []
    latest = _value(rows[-1].get("time")) if rows else ""
    parts = [
        '<section class="panel" aria-labelledby="activity-heading">',
        '<div class="section-heading"><div><p class="eyebrow">RUN LOG</p>'
        '<h2 id="activity-heading">Recent activity</h2></div></div>',
    ]
    if not rows:
        parts.append('<p class="empty-state">No activity has been recorded.</p>')
    else:
        parts.append('<ol class="activity-list">')
        for row in reversed(rows):
            parts.append(
                '<li><div class="activity-marker"></div><div class="activity-content">'
                '<div class="activity-meta"><span>' + _e(row.get("stage"), "Stage unknown") + '</span>'
                '<time datetime="' + _e(row.get("time")) + '">' + _e(row.get("time"), "Time unknown") + '</time></div>'
                '<p class="activity-summary">' + _e(row.get("summary"), "No summary") + '</p>'
            )
            details = []
            if row.get("workitem"):
                details.append("Work item " + _value(row.get("workitem")))
            if row.get("outcome"):
                details.append(_value(row.get("outcome")))
            if row.get("stream"):
                details.append("stream " + _value(row.get("stream")))
            if row.get("seq") is not None:
                details.append("event " + _value(row.get("seq")))
            if details:
                parts.append('<p class="activity-detail">' + _e(" · ".join(details)) + '</p>')
            parts.append('</div></li>')
        parts.append('</ol>')
    parts.append('</section>')
    return "".join(parts), latest


def _status_details(snapshot: Mapping[str, Any]) -> str:
    status = _value(snapshot.get("status_block"))
    if not status:
        return ""
    return (
        '<details class="panel status-details" data-state-key="status">'
        '<summary><span class="status-summary-copy"><span class="eyebrow">DETAILS</span>'
        '<strong>Full status block</strong></span>'
        '<span class="disclosure">Show</span></summary>'
        '<pre class="status-pre" tabindex="0">' + _e(status) + '</pre></details>'
    )


_STYLE = r"""
<style>
:root{color-scheme:light;--ink:#15231f;--muted:#66766f;--line:#dce5df;--paper:#f3f6f2;--panel:#fff;--green:#206b50;--soft:#e9f3ed;--amber:#946418;--rose:#a23b43;--blue:#315e78}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1120px;margin:auto;padding:38px 28px 64px}.masthead{display:flex;justify-content:space-between;gap:20px;align-items:center;margin-bottom:20px}.brand{font-size:.78rem;letter-spacing:.16em;font-weight:750;color:var(--green)}.schema{font-size:.78rem;color:var(--muted)}
.hero{padding:30px 34px;background:#143d32;color:#f7fbf8;border-radius:20px;box-shadow:0 18px 42px #193c2b1b}.hero-top{display:flex;align-items:flex-start;justify-content:space-between;gap:18px}.eyebrow{margin:0 0 5px;font-size:.68rem;letter-spacing:.14em;font-weight:750;color:var(--muted)}.hero .eyebrow{color:#b7d4c3}.hero h1{margin:4px 0 7px;font-size:clamp(1.7rem,4vw,2.65rem);line-height:1.14;letter-spacing:-.035em}.prompt{max-width:760px;color:#d9e7de;margin:0}.status-badge{flex:none;border:1px solid #9dc5ab;border-radius:99px;padding:7px 12px;color:#ecf8ef;font-size:.83rem;font-weight:700}.status-badge.status-blocked,.status-badge.status-halted{border-color:#e6a9a9;background:#71363a}.status-badge.status-paused,.status-badge.status-awaiting{border-color:#e2c68d;background:#66552f}.hero-meta{display:flex;flex-wrap:wrap;gap:9px 24px;margin-top:22px;padding-top:17px;border-top:1px solid #ffffff32;color:#d0e1d6;font-size:.82rem}.hero-meta b{color:#fff;font-weight:650}
.observer{display:flex;flex-wrap:wrap;gap:8px 20px;align-items:center;padding:13px 16px;margin:14px 0 24px;border:1px solid var(--line);background:#fff;border-radius:12px;color:var(--muted);font-size:.8rem}.observer strong{color:var(--ink)}.freshness-stale{color:var(--rose)!important}.observer-error{flex-basis:100%;color:var(--rose)}
.toolbar{display:flex;gap:8px;margin-left:auto}.button{font:inherit;font-size:.78rem;font-weight:650;border:1px solid #cddbd1;background:#fff;color:#244c3d;border-radius:8px;padding:7px 11px;cursor:pointer}.button:hover:not(:disabled){background:var(--soft)}.button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #82b7da;outline-offset:2px}.button:disabled{cursor:default;color:#87958d;background:#f5f7f5}.noscript{margin:0 0 20px;padding:10px 14px;border-radius:9px;background:#fff7e6;color:#75541a;font-size:.83rem}
.phase-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:0 0 18px}.phase-card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:17px 18px}.phase-top{display:flex;justify-content:space-between;align-items:center}.phase-number{font-size:.7rem;letter-spacing:.13em;color:#8a9a91;font-weight:750}.phase-state{font-size:.73rem;color:var(--muted);font-weight:650}.phase-card h3{margin:7px 0 15px;font-size:1.05rem}.phase-current{border-color:#87b89c;box-shadow:inset 0 0 0 1px #b8dac4}.phase-done .phase-state{color:var(--green)}.phase-current .phase-state{color:var(--green)}.meter{height:5px;border-radius:99px;overflow:hidden;background:#e7ede8}.meter span{display:block;height:100%;background:var(--green);border-radius:inherit}
.layout{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(280px,.85fr);gap:16px;align-items:start}.column{display:grid;gap:16px}.panel{min-width:0;background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:22px 23px}.section-heading{display:flex;justify-content:space-between;align-items:end;gap:14px;margin-bottom:17px}.section-heading h2{margin:0;font-size:1.2rem;letter-spacing:-.02em}.small-note{font-size:.76rem;color:var(--muted)}.focus-row{padding:14px 16px;border-left:3px solid var(--green);background:#f0f6f1;border-radius:0 9px 9px 0}.focus-label{display:block;margin-bottom:3px;font-weight:750;color:#205c46}.focus-row p{margin:0;color:#43574c}.narrative-list{margin-top:17px}.narrative-list h3{margin:0 0 7px;font-size:.79rem;color:var(--muted);letter-spacing:.06em;text-transform:uppercase}.narrative-list ul{list-style:none;margin:0;padding:0;display:grid;gap:8px}.narrative-list li{display:grid;grid-template-columns:minmax(115px,.55fr) minmax(0,1fr);gap:10px;padding-top:8px;border-top:1px solid #edf1ed;font-size:.82rem}.narrative-list strong{color:#365548}.narrative-list li span{color:var(--muted)}
.empty-state,.muted{color:var(--muted)}.empty-state{margin:5px 0 0;font-size:.88rem}.work-list{display:grid;gap:10px}.work-card{border:1px solid #e4ebe6;border-radius:11px;padding:15px 16px}.work-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.work-id{font-size:.7rem;color:var(--muted);font-weight:750;letter-spacing:.08em}.work-heading h3{margin:2px 0 0;font-size:.98rem;line-height:1.35}.pill{display:inline-flex;align-items:center;white-space:nowrap;border-radius:99px;padding:4px 9px;font-size:.68rem;font-weight:700;background:#edf1ee;color:#58665e}.pill-active{background:#e1f1e7;color:#216343}.pill-done,.pill-accepted{background:#e1f1e7;color:#216343}.pill-blocked{background:#f8e6e5;color:#953d42}.pill-pending,.pill-queued{background:#f2f0e9;color:#776738}.work-plan{margin:10px 0 0;color:#53635a;font-size:.83rem}.dependencies{margin:8px 0 0;font-size:.76rem;color:#596b61}.dependencies span{font-weight:700;color:#7a8981}
.document-list{display:grid;gap:9px}.document{border:1px solid #e1e9e3;border-radius:10px;overflow:hidden}.document summary{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:12px;padding:13px 14px}.document summary::-webkit-details-marker{display:none}.document summary:after{content:"+";order:2;color:#72837a;font-size:1.15rem}.document[open] summary:after{content:"−"}.document-title{min-width:0;overflow-wrap:anywhere;font-weight:700;font-size:.86rem}.document-body{padding:0 14px 14px}.document-summary{margin:0 0 9px;color:#516259;font-size:.81rem}.file-path{overflow-wrap:anywhere;margin:7px 0;color:#78867f;font-size:.72rem}.file-path span{font-weight:750;color:#56685e}.file-link{font-size:.78rem;color:#236747;font-weight:700}.document-error{margin:8px 0;color:var(--rose);font-size:.8rem}.preview,.status-pre{margin:10px 0 0;padding:13px 14px;max-height:420px;overflow:auto;border-radius:8px;background:#f4f6f4;color:#34443b;white-space:pre-wrap;overflow-wrap:anywhere;font: .78rem/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}.preview{border:1px solid #e7ece8}
.activity-list{list-style:none;margin:0;padding:0}.activity-list li{display:grid;grid-template-columns:10px minmax(0,1fr);gap:12px;position:relative;padding:0 0 18px}.activity-list li:last-child{padding-bottom:0}.activity-marker{width:8px;height:8px;margin-top:7px;border-radius:50%;background:#69a27e;box-shadow:0 0 0 3px #e7f1e9}.activity-content{min-width:0}.activity-meta{display:flex;justify-content:space-between;gap:8px;color:#315d48;font-weight:700;font-size:.77rem}.activity-meta time{font-weight:500;text-align:right;color:#87958d;font-size:.7rem}.activity-summary{margin:4px 0 0;color:#53635a;font-size:.81rem;overflow-wrap:anywhere}.activity-detail{margin:5px 0 0;color:#8a978f;font-size:.7rem}
.status-details{padding:0}.status-details>summary{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;padding:17px 21px}.status-details>summary::-webkit-details-marker{display:none}.status-details>summary .eyebrow{margin-bottom:1px}.status-details strong{font-size:.91rem}.disclosure{color:var(--green);font-size:.77rem;font-weight:700}.status-pre{margin:0 20px 20px}.terminal-report{padding:17px 20px;border-radius:12px;background:#e8f1eb;color:#3b5a48;font-size:.84rem}.terminal-report a{color:#205b41;font-weight:750}
.status-summary-copy{display:grid}
.graph-intro,.graph-note{margin:0 0 12px;color:#596a61;font-size:.81rem}.graph-note{margin:11px 0 0}.graph-group{margin-top:17px;padding-top:16px;border-top:1px solid #e8eee9}.graph-group:first-of-type{margin-top:0;padding-top:0;border-top:0}.graph-group-heading{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:10px}.graph-group-heading h3{margin:0;font-size:.96rem}.graph-viewport{max-width:100%;max-height:68vh;overflow:auto;border-radius:10px;outline-offset:3px}.dependency-svg{display:block;max-width:none;background:#f8faf8;border:1px solid #e4ebe6;border-radius:10px}.dependency-edge{fill:none;stroke:#5d806c;stroke-width:2;opacity:.9}.dependency-cycle-edge{stroke:#a23b43;stroke-dasharray:6 4}.graph-node rect{fill:#fff;stroke:#cbd9cf;stroke-width:1.5}.graph-node.status-done rect,.graph-node.status-accepted rect{fill:#edf7f0;stroke:#80ac8d}.graph-node.status-active rect,.graph-node.status-current rect{fill:#f0f6fb;stroke:#7c9db7}.graph-node.status-blocked rect{fill:#fff1ef;stroke:#bd7473}.graph-node-id{font-size:11px;font-weight:750;fill:#315d48}.graph-node-title{font-size:13px;font-weight:650;fill:#20372c}.graph-node-status{font-size:10px;fill:#718078}.graph-text{margin-top:11px;border:1px solid #e3eae4;border-radius:9px;padding:10px 13px}.graph-text>summary{cursor:pointer;color:#365c46;font-size:.8rem;font-weight:700}.graph-text>ul{margin:10px 0 0;padding-left:21px;display:grid;gap:9px}.graph-text>ul>li{padding-left:2px;color:#40564a;font-size:.8rem}.graph-text-meta{color:#75847b;font-size:.74rem}.graph-plan{margin:4px 0;color:#65756c;font-size:.76rem}.graph-dependencies{margin:5px 0 0;color:#53665b;font-size:.76rem}.graph-diagnostics{margin:11px 0 0;padding:10px 14px 10px 32px;border-radius:8px;background:#fff7e9;color:#785b25;font-size:.77rem}.graph-diagnostics li+li{margin-top:4px}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.stop-reason{margin:17px 0 0;padding-top:13px;border-top:1px solid #ffffff32;color:#f1dfb7;font-size:.88rem}
footer{margin-top:24px;text-align:center;color:#89968e;font-size:.72rem}
@media(max-width:800px){main{padding:25px 18px 44px}.layout{grid-template-columns:1fr}.hero{padding:25px 23px}.phase-strip{gap:8px}.phase-card{padding:14px}.toolbar{margin-left:0}}
@media(max-width:520px){main{padding:17px 12px 32px}.masthead{align-items:flex-start}.hero-top{display:block}.status-badge{display:inline-flex;margin-top:16px}.hero{padding:21px 18px}.hero-meta{display:grid;gap:6px}.phase-strip{grid-template-columns:1fr}.phase-card{padding:13px 15px}.phase-card h3{margin:5px 0 9px}.panel{padding:18px 16px}.section-heading{align-items:flex-start}.observer{gap:7px 12px}.toolbar{width:100%}.button{flex:1}.narrative-list li{grid-template-columns:1fr;gap:2px}.activity-meta{display:grid}.activity-meta time{text-align:left}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
</style>
"""


_SCRIPT = r"""
<script>
(() => {
  "use strict";
  const root = document.querySelector("[data-progress-view]");
  if (!root) return;
  const byId = (id) => document.getElementById(id);
  const parseDate = (value) => {
    const date = value ? new Date(value) : null;
    return date && !Number.isNaN(date.getTime()) ? date : null;
  };
  const ageText = (stamp) => {
    const date = parseDate(stamp);
    if (!date) return "time unavailable";
    const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
    if (seconds < 60) return seconds + " sec ago";
    if (seconds < 3600) return Math.floor(seconds / 60) + " min ago";
    if (seconds < 86400) return Math.floor(seconds / 3600) + " hr ago";
    return Math.floor(seconds / 86400) + " days ago";
  };
  const observed = root.dataset.observedAt || "";
  const staleSetting = Number(root.dataset.staleAfterSeconds);
  const staleAfter = Number.isFinite(staleSetting) ? Math.max(0, staleSetting) : 30;
  const mode = root.dataset.mode || "snapshot";
  const isFinal = root.dataset.final === "true";
  const changed = root.dataset.sourceChangedAt || "";
  const changedNode = byId("source-changed-age");
  const activity = root.dataset.lastActivityAt || "";
  const activityNode = byId("last-activity-age");
  const openedNode = byId("page-opened");
  const updateFreshness = () => {
    const observerAge = byId("observer-age");
    const observedDate = parseDate(observed);
    if (observerAge) {
      if (!observedDate) {
        observerAge.textContent = (isFinal ? "Final snapshot age: " :
          (mode === "snapshot" ? "Snapshot age: " : "Observer data age: ")) + "unavailable";
      } else {
        const seconds = Math.max(0, Math.floor((Date.now() - observedDate.getTime()) / 1000));
        const stale = seconds > staleAfter;
        const prefix = isFinal ? "Final snapshot age: " :
          (mode === "snapshot" ? "Snapshot age: " : "Observer data age: ");
        const suffix = isFinal ? " · final snapshot" :
          (mode === "snapshot" ? " · snapshot mode" : (stale ? " · stale" : " · current"));
        observerAge.textContent = prefix + ageText(observed) + suffix;
        observerAge.classList.toggle("freshness-stale", mode === "watch" && !isFinal && stale);
      }
    }
    if (changedNode) changedNode.textContent = changed
      ? "Source changed: " + changed + " (" + ageText(changed) + ")"
      : "Source change time: unavailable";
    if (activityNode) activityNode.textContent = activity
      ? "Latest run activity: " + activity + " (" + ageText(activity) + ")"
      : "Latest run activity: none";
    if (openedNode && !openedNode.dataset.openedAt) {
      openedNode.dataset.openedAt = new Date().toLocaleString();
      openedNode.textContent = "Page opened: " + openedNode.dataset.openedAt;
    }
  };
  updateFreshness();
  setInterval(updateFreshness, 1000);

  const interval = Math.max(1, Number(root.dataset.refreshSeconds) || 5);
  const toggle = byId("refresh-toggle");
  const manual = byId("refresh-now");
  const announce = byId("refresh-state");
  const autoAllowed = mode === "watch" && !isFinal;
  let paused = false;
  let timer = null;
  const stateKey = "shiploop-progress-view:" + location.pathname;
  const viewState = () => {
    const details = {};
    document.querySelectorAll("details[data-state-key]").forEach((node) => {
      details[node.dataset.stateKey] = !!node.open;
    });
    return {
      scrollY: Math.max(0, window.scrollY || 0),
      details: details,
      paused: paused
    };
  };
  const saveViewState = () => {
    const state = viewState();
    try {
      sessionStorage.setItem(stateKey, JSON.stringify(state));
      return;
    } catch (_) {}
    try {
      location.hash = "shiploop-view=" + encodeURIComponent(JSON.stringify(state));
    } catch (_) {}
  };
  const readFragmentState = () => {
    const match = location.hash.match(/^#shiploop-view=([^&]*)$/);
    if (!match) return null;
    try {
      return JSON.parse(decodeURIComponent(match[1]));
    } catch (_) {
      return null;
    }
  };
  const restoreViewState = () => {
    let state = null;
    try {
      const saved = sessionStorage.getItem(stateKey);
      if (saved) state = JSON.parse(saved);
    } catch (_) {}
    if (!state) state = readFragmentState();
    if (!state || typeof state !== "object") return;
    if (autoAllowed && typeof state.paused === "boolean") paused = state.paused;
    if (state.details && typeof state.details === "object" && !Array.isArray(state.details)) {
      document.querySelectorAll("details[data-state-key]").forEach((node) => {
        const key = node.dataset.stateKey;
        if (Object.prototype.hasOwnProperty.call(state.details, key)) {
          node.open = !!state.details[key];
        }
      });
    }
    const scrollY = Number(state.scrollY);
    if (Number.isFinite(scrollY) && scrollY > 0) {
      requestAnimationFrame(() => window.scrollTo(0, scrollY));
    }
  };
  const focusedControl = () => {
    const active = document.activeElement;
    return !!(active && active !== document.body &&
      active.matches("input, textarea, select, [contenteditable=true]"));
  };
  const hasSelection = () => {
    try {
      const selection = window.getSelection();
      return !!(selection && !selection.isCollapsed && String(selection).length);
    } catch (_) {
      return false;
    }
  };
  const reloadPage = () => {
    saveViewState();
    location.reload();
  };
  const schedule = () => {
    if (timer) clearTimeout(timer);
    if (!autoAllowed || paused) return;
    timer = setTimeout(() => {
      if (hasSelection() || focusedControl()) {
        if (announce) announce.textContent = "Auto-refresh skipped while text or a reading control is active.";
        schedule();
        return;
      }
      reloadPage();
    }, interval * 1000);
  };
  if (toggle) {
    if (!autoAllowed) {
      toggle.disabled = true;
      toggle.textContent = isFinal ? "Final snapshot · updates off" : "Snapshot view · updates off";
      toggle.setAttribute("aria-pressed", "true");
    } else {
      toggle.textContent = "Pause updates";
      toggle.setAttribute("aria-pressed", "false");
      toggle.addEventListener("click", () => {
        paused = !paused;
        toggle.textContent = paused ? "Resume updates" : "Pause updates";
        toggle.setAttribute("aria-pressed", paused ? "true" : "false");
        if (announce) announce.textContent = paused
          ? "Automatic updates paused."
          : "Automatic updates resume every " + interval + " seconds.";
        schedule();
      });
    }
  }
  if (manual) manual.addEventListener("click", reloadPage);
  restoreViewState();
  if (toggle && autoAllowed) {
    toggle.textContent = paused ? "Resume updates" : "Pause updates";
    toggle.setAttribute("aria-pressed", paused ? "true" : "false");
  }
  schedule();
})();
</script>
"""


def render(snapshot: Mapping[str, Any]) -> str:
    """Return a self-contained HTML progress view for a ShipLoop snapshot."""
    run = snapshot.get("run")
    run = run if isinstance(run, Mapping) else {}
    observer = snapshot.get("observer")
    observer = observer if isinstance(observer, Mapping) else {}
    facts = snapshot.get("facts")
    facts = facts if isinstance(facts, Mapping) else {}
    mode = _value(observer.get("mode"), "snapshot").lower()
    if mode not in ("watch", "snapshot"):
        mode = "snapshot"
    final = bool(observer.get("final"))
    observed_at = _value(snapshot.get("observed_at"))
    source_changed_at = _value(snapshot.get("source_changed_at"))
    refresh_seconds = max(1, min(3600, round(_number(observer.get("refresh_seconds"), 5))))
    stale_after_seconds = max(0, min(86400, round(_number(observer.get("stale_after_seconds"), 30))))
    activity_html, latest_activity = _activity(snapshot)
    status = _value(run.get("status"), "unknown")
    status_class = _STATUS_CLASSES.get(status.lower(), "other")
    prompt = _value(run.get("prompt"), _value(facts.get("goal"), "ShipLoop run"))
    reason = _value(run.get("reason"))
    stage = _value(run.get("stage"), "Unknown")
    owner = _value(run.get("owner"))
    terminal_uri = _local_file_uri(snapshot.get("terminal_report"))
    warnings = snapshot.get("warnings", [])
    warnings = warnings if isinstance(warnings, (list, tuple)) else ([warnings] if warnings else [])
    auto_allowed = mode == "watch" and not final
    refresh_button_label = ("Pause updates" if auto_allowed else
                            "Final snapshot · updates off" if final else "Snapshot view · updates off")
    refresh_button_disabled = "" if auto_allowed else " disabled"
    freshness_label = ("Final snapshot age:" if final else
                       "Snapshot age:" if mode == "snapshot" else "Observer data age:")

    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        'style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; img-src \'none\'; '
        'connect-src \'none\'; object-src \'none\'; base-uri \'none\'; form-action \'none\'>'
        '<meta name="color-scheme" content="light"><title>ShipLoop progress · ' + _e(prompt) + '</title>',
        _STYLE,
        '</head><body><main data-progress-view data-mode="' + _e(mode)
        + '" data-final="' + ("true" if final else "false")
        + '" data-refresh-seconds="' + str(refresh_seconds)
        + '" data-stale-after-seconds="' + str(stale_after_seconds)
        + '" data-observed-at="' + _e(observed_at)
        + '" data-source-changed-at="' + _e(source_changed_at)
        + '" data-last-activity-at="' + _e(latest_activity) + '">',
        '<div class="masthead"><div class="brand">SHIPLOOP / RUN VIEW</div>'
        '<div class="schema">' + _e(snapshot.get("schema"), "Progress snapshot") + '</div></div>',
        '<header class="hero"><div class="hero-top"><div><p class="eyebrow">RUN GOAL</p>'
        '<h1>' + _e(prompt) + '</h1></div><span class="status-badge status-' + status_class
        + '">' + _e(status) + '</span></div><p class="prompt">Run details and accepted progress, from the saved snapshot.</p>'
        '<div class="hero-meta"><span>Run <b>' + _e(run.get("id"), "Unknown") + '</b></span>'
        '<span>Revision <b>' + _e(run.get("revision"), "Unknown") + '</b></span>'
        '<span>Stage <b>' + _e(stage) + '</b></span>'
        + ('<span>Owner <b>' + _e(owner) + '</b></span>' if owner else '')
        + '</div>' + ('<p class="stop-reason">' + _e(reason) + '</p>' if reason else '') + '</header>',
        '<section class="observer" aria-label="Snapshot freshness and refresh controls">'
        '<strong id="observer-age">' + _e(freshness_label) + ' calculating…</strong>'
        '<span id="source-changed-age">Source change time: calculating…</span>'
        '<span id="last-activity-age">Latest run activity: calculating…</span>'
        '<span id="page-opened">Page opened: calculating…</span>'
        '<div class="toolbar"><button class="button" id="refresh-toggle" type="button"'
        + refresh_button_disabled + '>' + _e(refresh_button_label) + '</button>'
        + '<button class="button" id="refresh-now" type="button">Refresh now</button></div>'
        '<span id="refresh-state" class="sr-only" aria-live="polite"></span>'
        + ('<span class="observer-error">Observer error: ' + _e(observer.get("error")) + '</span>'
           if observer.get("error") else '') + '</section>',
        '<noscript><p class="noscript">This saved snapshot is readable without JavaScript. Browser refresh controls need JavaScript.</p></noscript>',
        '<section class="phase-strip" aria-label="Run phases">'
        + "".join(_phase_card(row, index, bool(snapshot.get("plan_accepted")))
                  for index, row in enumerate(_phase_rows(facts))) + '</section>',
        '<div class="layout"><div class="column">' + _narrative(snapshot, facts)
        + _dependency_graphs(snapshot) + _work_items(snapshot)
        + _documents(snapshot) + _status_details(snapshot)
        + ('<section class="terminal-report"><strong>Terminal report</strong> · '
           '<a href="' + _e(terminal_uri) + '">Open the saved report</a></section>' if terminal_uri else '')
        + '</div><aside class="column">' + activity_html
        + ('<section class="panel warnings"><div class="section-heading"><div><p class="eyebrow">ATTENTION</p>'
           '<h2>Warnings</h2></div></div><ul>'
           + "".join('<li>' + _e(item) + '</li>' for item in warnings
                     if item is not None)
           + '</ul></section>' if warnings else '')
        + '</aside></div>',
        '<footer>Generated from a saved progress snapshot. Run activity and observer freshness are shown separately.</footer>',
        '</main>',
        _SCRIPT,
        '</body></html>',
    ]
    return "".join(parts)
