#!/usr/bin/env python3
"""Tally the start-route probe and apply the pre-registered decision rule (README, "Decision rule").

    python3 -I analyze.py RESULTS.jsonl [--export results-compact.jsonl]

A slot counts once, by its last row if that row is valid; a slot whose last row is invalid is reported and left out. The outcome of a
sf-ui trial is the first ShipLoop start command the model ran: `workspace` (the isolated entry, right for an empty
directory the user did not ask to work in place in) or `direct` (init, the wrong route there).
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CARD_CAP_BYTES = 30500
BAR_P = 0.025            # one-sided Fisher exact, split over the two candidates
MIN_CONTROL_WRONG = 5    # fewer wrong starts than this in the control arm and the probe cannot tell the arms apart
NONE_MARGIN = 0.10       # a candidate may not leave more sessions without a start than the control by more than this
GUARD_MARGIN = 1         # in the two regression requests a candidate may add at most this many wrong or self-bootstrapped starts
ARMS = ("C", "T1", "T2")


def fisher_lower(c_wrong: int, c_n: int, t_wrong: int, t_n: int) -> float:
    """P(the candidate arm holds t_wrong or fewer of the wrong starts | the margins): one-sided Fisher exact."""
    wrong, n = c_wrong + t_wrong, c_n + t_n
    low = max(0, t_n - (n - wrong))
    return sum(math.comb(wrong, x) * math.comb(n - wrong, t_n - x) for x in range(low, t_wrong + 1)) / math.comb(n, t_n)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def load(path: Path) -> tuple[list[dict], list[int]]:
    last: dict[int, dict] = {}
    for line in path.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            last[row["slot"]] = row   # the last row of a slot decides: a later invalid row supersedes an earlier valid one
    valid = {slot: row for slot, row in last.items() if row["valid"]}
    return [valid[s] for s in sorted(valid)], sorted(set(last) - set(valid))


def tally(rows: list[dict]) -> dict:
    cells: dict = {}
    for stimulus in sorted({r["stimulus"] for r in rows}):
        for arm in sorted({r["arm"] for r in rows}):
            mine = [r for r in rows if r["stimulus"] == stimulus and r["arm"] == arm]
            cells[(stimulus, arm)] = {
                "n": len(mine), "workspace": sum(r["start"] == "workspace" for r in mine),
                "direct": sum(r["start"] == "direct" for r in mine), "none": sum(r["start"] == "none" for r in mine),
                "bootstrap": sum(bool(r["self_bootstrap"]) for r in mine),
                "read_run_start": sum(bool(r["read_run_start"]) for r in mine),
                "seconds": sorted(r["seconds_to_start"] for r in mine if r["seconds_to_start"] is not None)}
    return cells


INPLACE_POOLED_DROP = 0.20     # pooled drop in `init` starts that counts as harm, with the one-sided p below
INPLACE_STIMULUS_DROP = 0.30   # a single request is flagged at this drop and the same p
INPLACE_P = 0.05
INPLACE_MIN_CONTROL = 0.30     # below this share of `init` starts in the control the old wording does not honor the request either


def evaluate_inplace(cells: dict) -> tuple[list[str], str]:
    """Requests that explicitly ask for an in-place or non-Git run: `init` is the right first start. Does T2 lower it?"""
    stimuli = sorted({s for s, _ in cells})
    lines: list[str] = []
    flagged: list[str] = []

    def share(arm: str, subset: list[str]) -> tuple[int, int]:
        init = sum(cells[(s, arm)]["direct"] for s in subset)
        return init, sum(cells[(s, arm)]["workspace"] + cells[(s, arm)]["direct"] for s in subset)

    for s in stimuli:
        (ci, cn), (ti, tn) = share("C", [s]), share("T2", [s])
        p = fisher_lower(ci, cn, ti, tn) if cn and tn else 1.0
        drop = (ci / cn - ti / tn) if cn and tn else 0.0
        lines.append(f"{s}: init as the first start, C {ci}/{cn}, T2 {ti}/{tn}; drop {drop:+.2f}; one-sided p (T2 lower) {p:.3f}"
                     f"; own git init/config/commit: C {cells[(s, 'C')]['bootstrap']}, T2 {cells[(s, 'T2')]['bootstrap']}")
        if drop >= INPLACE_STIMULUS_DROP and p < INPLACE_P:
            flagged.append(s)
    (ci, cn), (ti, tn) = share("C", stimuli), share("T2", stimuli)
    p = fisher_lower(ci, cn, ti, tn) if cn and tn else 1.0
    drop = (ci / cn - ti / tn) if cn and tn else 0.0
    lines.append(f"pooled: C {ci}/{cn} ({ci / max(cn, 1):.2f}), T2 {ti}/{tn} ({ti / max(tn, 1):.2f}); drop {drop:+.2f}; one-sided p {p:.4f}")
    if cn and ci / cn < INPLACE_MIN_CONTROL:
        lines.append(f"note: the control honors the explicit request in only {ci / cn:.0%} of sessions, so T2 is judged on not being worse")
    harmed = drop >= INPLACE_POOLED_DROP and p < INPLACE_P
    verdict = ("HARM: T2 lowers explicit in-place starts (pooled)" if harmed else
               f"HARM on {', '.join(flagged)}" if flagged else "NO HARM FOUND")
    return lines, verdict


def card_sizes(arms_file: Path) -> dict:
    card = (ROOT / "skills" / "shiploop" / "SKILL.md").read_text()
    arms = json.loads(arms_file.read_text())
    sizes = {}
    for arm, edits in arms.items():
        text = card
        for old, new in edits:
            text = text.replace(old, new)
        sizes[arm] = len(text.encode())
    return sizes


def evaluate(cells: dict, arms_file: Path) -> tuple[list[str], str | None]:
    lines: list[str] = []
    control = cells[("sf-ui", "C")]
    c_started = control["workspace"] + control["direct"]
    lines.append(f"control (sf-ui): {control['direct']} wrong of {c_started} started "
                 f"(precondition: at least {MIN_CONTROL_WRONG} wrong): {'met' if control['direct'] >= MIN_CONTROL_WRONG else 'NOT met'}")
    sizes = card_sizes(arms_file)
    meeting: list[tuple[int, int, str]] = []
    for arm in ("T1", "T2"):
        cell = cells[("sf-ui", arm)]
        started = cell["workspace"] + cell["direct"]
        p = fisher_lower(control["direct"], c_started, cell["direct"], started) if started and c_started else 1.0
        halved = started > 0 and cell["direct"] * c_started <= 0.5 * control["direct"] * started
        none_ok = (cell["none"] / max(cell["n"], 1)) <= (control["none"] / max(control["n"], 1)) + NONE_MARGIN
        guard = sum(cells[(s, arm)]["direct"] + cells[(s, arm)]["bootstrap"] for s in ("hello", "repo"))
        guard_c = sum(cells[(s, "C")]["direct"] + cells[(s, "C")]["bootstrap"] for s in ("hello", "repo"))
        guard_ok = guard <= guard_c + GUARD_MARGIN
        size_ok = sizes[arm] <= CARD_CAP_BYTES
        precondition = control["direct"] >= MIN_CONTROL_WRONG
        checks = {"control can discriminate": precondition, f"one-sided Fisher p {p:.4f} < {BAR_P}": p < BAR_P,
                  "wrong rate at most half the control's": halved, "no more sessions without a start": none_ok,
                  f"regression guard ({guard} vs control {guard_c}, margin {GUARD_MARGIN})": guard_ok,
                  f"card {sizes[arm]} bytes <= {CARD_CAP_BYTES}": size_ok}
        ok = all(checks.values())
        lines.append(f"{arm}: {cell['direct']} wrong of {started} started, {cell['none']} without a start -> "
                     + ("MEETS THE BAR" if ok else "does not meet the bar"))
        lines.extend(f"    {'ok ' if v else 'NO '} {k}" for k, v in checks.items())
        if ok:
            meeting.append((cell["direct"], sizes[arm], arm))
    return lines, (min(meeting)[2] if meeting else None)


def agreement(rows: list[dict]) -> list[str]:
    """The route read from the command against the route read from what the start left on disk (effect_route)."""
    seen = [r for r in rows if "effect_route" in r]
    if not seen:
        return []
    both = [r for r in seen if r["start"] != "none" and r["effect_route"] != "none"]
    differ = [r for r in both if r["start"] != r["effect_route"]]
    unseen = [r for r in seen if r["start"] != "none" and r["effect_route"] == "none"]
    lines = [(f"route from the command against route from what the start left on disk: {len(seen)} sessions; both readable "
              f"{len(both)}, agree {len(both) - len(differ)}, differ {len(differ)}; command only (start stopped before it "
              f"wrote anything, or wrote outside the folder) {len(unseen)}")]
    lines.extend(f"    DIFFER slot {r['slot']} {r['arm']} {r['stimulus']}: command {r['start']}, disk {r['effect_route']}" for r in differ)
    no_start = [r for r in seen if r["start"] == "none"]
    lines.extend(f"    NO START slot {r['slot']} {r['arm']} {r['stimulus']}: disk reads {r['effect_route']}" for r in no_start)
    return lines


def compact(row: dict) -> dict:
    def short(text: str | None, limit: int) -> str | None:
        if text is None:
            return None
        text = re.sub(r"/Users/[^ '\"]*?/home/\.codex/plugins/cache/whichguy/skill-craft/[\d.]+/", "<plugin>/", text)
        text = re.sub(r"/Users/[^ '\"]*?/trials/[^/ '\"]+/", "<trial>/", text)
        return text[:limit]
    keys = ("slot", "attempt", "stimulus", "arm", "i", "start", "end", "valid", "error", "seconds_to_start",
            "read_run_start", "self_bootstrap", "skill_seen", "installed_card_sha256", "effect_route")
    out = {k: row.get(k) for k in keys}
    out["start_command"] = short(row.get("start_command"), 200)
    out["pre_start"] = [short(c, 110) for c in row.get("pre_start", [])[:6]]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("--export", type=Path)
    ap.add_argument("--arms", type=Path, default=HERE / "arms.json", help="the arms file the batch used (sizes)")
    ap.add_argument("--mode", choices=("start", "inplace"), default="start",
                    help="start: init is wrong (the bar and tie-break); inplace: init is right (is T2 harmless?)")
    ap.add_argument("--also", type=Path, help="another batch's results: add a pooled table (descriptive only)")
    args = ap.parse_args()
    rows, dropped = load(args.results)
    cells = tally(rows)
    print(f"{len(rows)} valid slots; slots with no valid attempt: {dropped or 'none'}")
    label = "init share (95% CI)" if args.mode == "inplace" else "wrong rate (95% CI)"
    print(f"{'request':13s} {'arm':3s} {'n':>3s} {'workspace':>9s} {'direct':>6s} {'none':>4s} {label:>22s} "
          f"{'bootstrap':>9s} {'read run-start':>14s} {'median s':>8s}")
    for (stimulus, arm), c in cells.items():
        started = c["workspace"] + c["direct"]
        lo, hi = wilson(c["direct"], started)
        rate = f"{c['direct'] / started:.2f} ({lo:.2f}-{hi:.2f})" if started else "-"
        median = c["seconds"][len(c["seconds"]) // 2] if c["seconds"] else "-"
        print(f"{stimulus:13s} {arm:3s} {c['n']:3d} {c['workspace']:9d} {c['direct']:6d} {c['none']:4d} {rate:>22s} "
              f"{c['bootstrap']:9d} {c['read_run_start']:14d} {median!s:>8s}")
    if args.mode == "inplace":
        lines, verdict = evaluate_inplace(cells)
        print()
        print("\n".join(lines))
        print()
        print(f"VERDICT: {verdict}")
        winner = None
    else:
        lines, winner = evaluate(cells, args.arms)
        print()
        print("\n".join(lines))
        print()
        print(f"DECISION: ship {winner}" if winner else "DECISION: ship nothing (no candidate meets the pre-registered bar)")
    extra = agreement(rows)
    if extra:
        print()
        print("\n".join(extra))
    if args.also:
        more, _ = load(args.also)
        pooled = tally(rows + more)
        if args.mode != "start":
            raise SystemExit("--also is for the start set")
        print()
        print("pooled over both batches (descriptive, not a decision): sf-ui wrong / started")
        for arm in ARMS:
            c = pooled[("sf-ui", arm)]
            started = c["workspace"] + c["direct"]
            lo, hi = wilson(c["direct"], started)
            print(f"   {arm:3s} {c['direct']:3d} / {started:3d}  {c['direct'] / started:.3f} ({lo:.3f}-{hi:.3f})  none {c['none']}")
        pc, pt = pooled[("sf-ui", "C")], pooled[("sf-ui", "T2")]
        print(f"   T2 against C, one-sided Fisher p = {fisher_lower(pc['direct'], pc['workspace'] + pc['direct'], pt['direct'], pt['workspace'] + pt['direct']):.2e}")
    if args.export:
        args.export.write_text("".join(json.dumps(compact(r)) + "\n" for r in rows))
        print(f"wrote {args.export}")


if __name__ == "__main__":
    main()
