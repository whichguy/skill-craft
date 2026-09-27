"""Render ShipLoop's run narrative: what is achieved, what is happening, what comes next.

The navigator gathers the facts from saved state (``narrative_facts``); this
module only formats them as Markdown; the status hook turns that Markdown into
styled terminal text for the one host that displays hook messages. Every value is already cleaned and
capped by the navigator; nothing here reads files or run state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

BEGIN = "=== ShipLoop narrative ==="
END = "=== end ShipLoop narrative ==="
BAR_WIDTH = 12
_STOP_ICON = {"paused": "⏸️ Paused", "blocked": "⛔ Blocked", "halted": "⛔ Halted",
              "awaiting": "❓ Waiting on you", "done": "\U0001f3c1 Done"}


def bar(done: float, total: int) -> str:
    """A fixed-width block bar; an unknown total renders as empty."""
    filled = 0 if total <= 0 else max(0, min(BAR_WIDTH, round(BAR_WIDTH * done / total)))
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def duration(seconds: float) -> str:
    minutes = round(seconds / 60)
    if minutes < 1:
        return "under a minute"
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60} h {minutes % 60} min" if minutes % 60 else f"{minutes // 60} h"


def _parse(stamp: Any) -> datetime | None:
    try:
        return datetime.strptime(str(stamp), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def pace_line(pace: Mapping[str, Any] | None) -> str | None:
    """Observed pace, and a forecast only when at least two steps give a rate."""
    if not pace:
        return None
    started = _parse(pace.get("started"))
    stamps = sorted(filter(None, (_parse(stamp) for stamp in pace.get("stamps", ()))))
    if started is None or not stamps:
        return None
    elapsed = max(0.0, (stamps[-1] - started).total_seconds())
    count = len(stamps)
    line = f"{count} step{'s' if count != 1 else ''} in {duration(elapsed)}"
    remaining = pace.get("remaining_steps") or 0
    if count >= 2 and elapsed > 0 and remaining:
        estimate = elapsed / count * remaining
        line += (f" · about {duration(estimate)} left in {pace['scope']} "
                 "at this run's pace (an estimate, not a promise)")
    return line


def _phase_line(phases: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    """Return (markdown, plain) for the phase strip with a bar on the current phase."""
    md, plain = [], []
    for phase in phases:
        total, done, status = phase["total"], phase["done"], phase["state"]
        count = f"{phase['done_label']}/{total}" if total else "—"
        if status == "current":
            meter = bar(done, total or 0)
            md.append(f"`{meter}` **{phase['name']} {count}**")
            plain.append(f"{meter} {phase['name']} {count}")
        else:
            mark = ("✓" if status == "done" else f"({total} steps)" if phase["name"] == "Release"
                    else f"({total} planned)" if total else "(set by plan)")
            md.append(f"{phase['name']} {mark}")
            plain.append(f"{phase['name']} {mark}")
    return " · ".join(md), " · ".join(plain)


def _rows(facts: Mapping[str, Any]) -> list[tuple[str, list[tuple[str, str]] | str]]:
    """Sections as (heading, rows) where each row is (label, text)."""
    sections: list[tuple[str, list[tuple[str, str]] | str]] = []
    if facts["achieved"]:
        sections.append(("✅ Achieved", [(row["label"], row["text"]) for row in facts["achieved"]]))
    stop = facts.get("stop")
    if stop:
        sections.append((_STOP_ICON[stop["kind"]], stop["text"]))
    else:
        now = facts["now"]
        sections.append(("▶️ Now", [(now["label"], now["text"])]))
    if facts["ahead"]:
        sections.append(("\U0001f52d Ahead", [(row["label"], row["text"]) for row in facts["ahead"]]))
    return sections


def markdown(facts: Mapping[str, Any]) -> str:
    phases_md, _ = _phase_line(facts["phases"])
    lines = [f"#### \U0001f6a2 ShipLoop — {facts['goal']}", phases_md, ""]
    for heading, rows in _rows(facts):
        if isinstance(rows, str):
            lines += [f"**{heading}** — {rows}", ""]
            continue
        if heading.endswith("Now"):
            label, text = rows[0]
            lines += [f"**{heading}** — **{label}**: {text}", ""]
            continue
        lines.append(f"**{heading}**")
        lines += [f"- **{label}** — {text}" if text else f"- **{label}**" for label, text in rows]
        lines.append("")
    pace = pace_line(facts.get("pace"))
    if pace:
        lines.append(f"**⏱ Pace** — {pace}")
    return "\n".join(lines).rstrip()
