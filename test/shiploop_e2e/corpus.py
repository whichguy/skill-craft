#!/usr/bin/env python3
"""One figure over many saved runs, with the scope that produced it.

Why this exists. Every corpus figure in LEARNINGS.md was computed by a throwaway script, and three of them
changed when a later session re-derived them: Improve yield (19% shipped, 18% in its own scope, 26% pooled),
narrative compliance (61%, then 69% once repeated bodies stopped counting as separate obligations), and the
refusal cost (a raw correlation that was a run-size confound). Each rewrite cost a session and each shipped
commit message still quotes the old number. This module is the one place that walks saved runs, so a figure
can be re-derived by the same code that produced it, with ``--json`` for a later reader to diff.

What it reports, per group and in total:

* ``runs`` -- run folders that produced a figure. A run with no metrics is counted in ``unmeasured`` with
  its reason instead of being dropped silently.
* ``improve_children`` / ``improve_editing_children`` -- from ``metrics.improve_reviews``, which reads each
  child's own ``passes.md``. The edit RATE is per group: pooling corpora with different rates produces a
  number that describes no corpus (see "The Improve yield figure is corpus-dependent" in LEARNINGS.md).
* ``narrative_emitted`` / ``narrative_shown`` -- from ``metrics.narrative``, which counts one obligation per
  DISTINCT narrative body (2026-11-03), not one per packet print.
* ``verify_records`` / ``verify_commands`` -- from ``metrics.verifications``, which counts executed ``runs``
  rows (2026-11-03), not the request array plus the run array.
* ``isolated`` / ``contended`` -- whether any other run in the corpus overlapped this one's span by more than
  ``--overlap-seconds``, read from ``result.json``'s ``environment.overlap`` when the run recorded it and
  computed from spans when it did not. Contended runs are 1.32x longer in median span (same entry), so a
  duration figure should say which group it came from.

Grouping is by the corpus directory a run lives under (``--group-by corpus``, the default) or as one total
(``--group-by none``). That default is deliberate: the per-corpus spread is the finding, and a single pooled
number hides it.

    python3 test/shiploop_e2e/corpus.py ~/e2e-runs ~/e2e-runs-multipass
    python3 test/shiploop_e2e/corpus.py ~/e2e-runs --group-by none --json

Read-only: it opens saved records and writes nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))

import environment  # noqa: E402
import metrics  # noqa: E402
import scorecard  # noqa: E402

# What a figure is built from, named so a reader can refuse a number whose basis they cannot see.
BASES = {
    "improve": "metrics.improve_reviews over each child's passes.md; edited = a pass changed tree or result",
    "narrative": "metrics.narrative; one obligation per distinct narrative body (2026-11-03)",
    "verify": "metrics.verifications; executed `runs` rows only (2026-11-03)",
    "overlap": "result.json environment.overlap, else computed from run spans over the same corpus",
}


# Folders that hold a saved run only because they are a copy of the repository: a build or experiment tree under a
# corpus carries `docs/experiments/...` and `test/fixtures/...` runs that are fixtures, not observations. Counting them
# inflated a first pass to 2,419 runs with 1,603 unmeasurable spans (2026-11-03), which is the same "read the wrong
# folder" error that produced three false alarms that day. A caller who wants them names the folder directly.
NOT_OBSERVATIONS = ("/docs/experiments/", "/test/experiments/", "/test/fixtures/", "/fixtures/",
                    "/marketplace-cache/", "/.tmp/", "/node_modules/", "/home/")


def is_observation(run: Path) -> bool:
    """Whether ``run`` is a recorded observation rather than a fixture inside a copied repository."""
    text = "/" + str(Path(run).resolve()).strip("/") + "/"
    return not any(marker in text for marker in NOT_OBSERVATIONS)


def run_dir_of(run: Path) -> Path:
    """The navigator run directory inside a discovered workspace folder.

    ``scorecard.run_folders`` yields the WORKSPACE a case ran in; the records ``metrics`` reads live one level down, at
    ``.shiploop-runs/<work>/run``. Passing the workspace to ``metrics.improve_reviews`` reads
    ``<workspace>/../worktree/.shiploop-improve`` and reports the evidence unavailable, which a first version of this
    module did: it reported 0 Improve children over 398 runs (2026-11-03). The newest work folder is used when a
    workspace holds more than one run, since that is the one the workspace's own metrics describe.
    """
    nested = sorted((run / ".shiploop-runs").glob("*/run")) if (run / ".shiploop-runs").is_dir() else []
    return nested[-1] if nested else run


def _span(run: Path) -> tuple[float, float] | None:
    """The run's (started, ended) from its metrics span, or None when it has no usable pair."""
    path = run / "metrics.json"
    try:
        found = json.loads(path.read_text(encoding="utf-8")).get("span") or {}
    except (OSError, ValueError, AttributeError):
        return None
    started, ended = found.get("started"), found.get("ended")
    if not isinstance(started, (int, float)) or not isinstance(ended, (int, float)) or ended <= started:
        return None
    return float(started), float(ended)


def _recorded_overlap(run: Path) -> int | None:
    """How many runs this one recorded as overlapping it, or None when it recorded nothing either way."""
    try:
        found = json.loads((run / "result.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    environment_record = found.get("environment")
    if not isinstance(environment_record, dict) or "overlap" not in environment_record:
        return None
    overlap = environment_record["overlap"]
    return len(overlap) if isinstance(overlap, list) else None


def _overlaps(a: tuple[float, float], b: tuple[float, float], floor: float) -> bool:
    """Whether two spans share more than ``floor`` seconds."""
    shared = min(a[1], b[1]) - max(a[0], b[0])
    return shared > floor


def group_of(run: Path, roots: Iterable[Path]) -> str:
    """The corpus group ``run`` belongs to: its date folder under the root it was found in.

    ``~/e2e-runs/2026-11-01/x/y`` groups as ``2026-11-01``, because the per-corpus spread is the finding (11% to 85%
    edit rate across date folders) and grouping by root name alone collapsed 16 corpora into one row. A run directly
    under the root groups as the root's own name.
    """
    resolved = run.resolve()
    for root in roots:
        try:
            relative = resolved.relative_to(Path(root).resolve())
        except ValueError:
            continue
        return relative.parts[0] if len(relative.parts) > 1 else Path(root).name
    return "other"


def summarise(roots: Iterable[Path], *, group_by: str = "corpus", overlap_seconds: float = 60.0) -> dict:
    """Every figure over the runs found under ``roots``, grouped, with what it could not measure named."""
    roots = [Path(root) for root in roots]
    runs: list[Path] = []
    missing: list[str] = []
    for root in roots:
        if not root.is_dir():
            missing.append(str(root))
            continue
        runs += [folder for folder in scorecard.run_folders([root])]
    runs = sorted(run for run in dict.fromkeys(runs) if is_observation(run))

    spans = {run: _span(run) for run in runs}
    measurable = [run for run in runs if spans[run] is not None]
    # An overlap needs both spans: a run with no span cannot be placed, and saying "isolated" would be a guess.
    external: dict[Path, int] = {}
    for run in measurable:
        external[run] = sum(1 for other in measurable
                            if other != run and _overlaps(spans[run], spans[other], overlap_seconds))

    groups: dict[str, dict[str, Any]] = {}
    unmeasured: dict[str, str] = {}
    for run in runs:
        key = group_of(run, roots) if group_by == "corpus" else "all"
        bucket = groups.setdefault(key, {
            "runs": 0, "unmeasured": 0,
            "improve_children": 0, "improve_editing_children": 0, "runs_with_improve": 0,
            "narrative_emitted": 0, "narrative_shown": 0,
            "verify_records": 0, "verify_commands": 0,
            "isolated": 0, "contended": 0, "span_seconds": [],
        })
        bucket["runs"] += 1
        try:
            reviews = metrics.improve_reviews(run_dir_of(run))
        except (OSError, ValueError) as error:
            reviews = {}
            unmeasured[f"{run}: improve_reviews"] = str(error)
        if isinstance(reviews.get("children"), int) and reviews["children"]:
            bucket["runs_with_improve"] += 1
            bucket["improve_children"] += reviews["children"]
            bucket["improve_editing_children"] += reviews.get("edited_children") or 0
        try:
            story = metrics.narrative(run, run_dir_of(run))
        except (OSError, ValueError) as error:
            story = {}
            unmeasured[f"{run}: narrative"] = str(error)
        if story.get("emitted"):
            bucket["narrative_emitted"] += story["emitted"]
            bucket["narrative_shown"] += story["shown"]
        try:
            verify = metrics.verifications(run_dir_of(run))
        except OSError as error:
            verify = {}
            unmeasured[f"{run}: verifications"] = str(error)
        if verify.get("records"):
            bucket["verify_records"] += verify["records"]
            bucket["verify_commands"] += verify["commands"]
        span = spans[run]
        if span is None:
            bucket["unmeasured"] += 1
            unmeasured.setdefault(f"{run}: span", "no readable started/ended pair in metrics.json")
            continue
        bucket["span_seconds"].append(span[1] - span[0])
        if external.get(run, 0) >= 1:
            bucket["contended"] += 1
        else:
            bucket["isolated"] += 1

    for bucket in groups.values():
        spans_seen = sorted(bucket.pop("span_seconds"))
        children = bucket["improve_children"]
        emitted = bucket["narrative_emitted"]
        bucket["improve_edit_rate"] = round(100 * bucket["improve_editing_children"] / children, 1) \
            if children else None
        bucket["narrative_shown_rate"] = round(100 * bucket["narrative_shown"] / emitted, 1) if emitted else None
        bucket["span_median_minutes"] = round(spans_seen[len(spans_seen) // 2] / 60, 1) if spans_seen else None
    return {"group_by": group_by, "bases": BASES, "roots": [str(root) for root in roots],
            "missing_roots": missing, "groups": groups, "unmeasured": unmeasured}


def render(summary: Mapping[str, Any]) -> str:
    """One line per group, then the bases a reader needs to know what the numbers are."""
    if summary["missing_roots"]:
        lines = ["not a folder: " + ", ".join(summary["missing_roots"])]
    else:
        lines = []
    heading = ("a rate is per group: pooling corpora with different rates describes none of them"
               if summary["group_by"] == "corpus" else "pooled: the per-corpus spread is hidden")
    lines.append(f"corpus summary ({heading})")
    lines.append(f"  {'group':<28}{'runs':>6}{'ch/run':>8}{'edit%':>7}{'narr%':>7}{'verify':>8}"
                 f"{'span min':>10}{'iso':>5}{'con':>5}")
    for name, row in sorted(summary["groups"].items(), key=lambda item: -item[1]["runs"]):
        per_run = round(row["improve_children"] / row["runs_with_improve"], 1) if row["runs_with_improve"] else "-"
        cells = (f"{name:<28}{row['runs']:>6}{str(per_run):>8}"
                 f"{_pct(row['improve_edit_rate']):>7}{_pct(row['narrative_shown_rate']):>7}"
                 f"{row['verify_commands']:>8}{_min(row['span_median_minutes']):>10}"
                 f"{row['isolated']:>5}{row['contended']:>5}")
        lines.append("  " + cells)
    lines.append("  bases: " + "; ".join(f"{key} = {value}" for key, value in summary["bases"].items()
                                         if key != "overlap"))
    if summary["unmeasured"]:
        lines.append(f"  unmeasured: {len(summary['unmeasured'])} part(s); --json names each")
    return "\n".join(lines)


def _pct(value: float | None) -> str:
    return "-" if value is None else f"{value:.0f}%"


def _min(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("roots", nargs="+", help="folders holding saved runs (searched recursively)")
    parser.add_argument("--group-by", choices=("corpus", "none"), default="corpus",
                        help="per corpus directory (default) or one pooled total")
    parser.add_argument("--overlap-seconds", type=float, default=60.0,
                        help="shared span that counts as an overlap (default 60)")
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = parser.parse_args(argv)
    summary = summarise(args.roots, group_by=args.group_by, overlap_seconds=args.overlap_seconds)
    print(json.dumps(summary, indent=1, sort_keys=True) if args.json else render(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
