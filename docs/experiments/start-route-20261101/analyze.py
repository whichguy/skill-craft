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


def dark_cells(cells: dict) -> list[str]:
    """The request/arm cells with no session that reached a start. A comparison needs both arms to have started somewhere: a
    treatment that never starts shows no regression in the sessions it never ran (Sol's review, 2026-11-01)."""
    return [f"{stimulus}/{arm}" for (stimulus, arm), c in sorted(cells.items()) if arm in ("C", "T2") and c["workspace"] + c["direct"] == 0]


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
    dark = dark_cells(cells)
    verdict = ("HARM: T2 lowers explicit in-place starts (pooled)" if harmed else
               f"HARM on {', '.join(flagged)}" if flagged else
               f"UNREADABLE: no session reached the start in {', '.join(dark)}, so there is nothing to compare there" if dark else
               "NO HARM FOUND")
    return lines, verdict


HOSTS_MORE_INIT = 3        # extra `init` starts on T2, over the control, that count as a regression where `workspace start` is right
HOSTS_P = 0.05


def evaluate_hosts(cells: dict) -> tuple[list[str], str]:
    """One host that is not the one the card was tuned on: does T2 start more runs with `init` where `workspace start` is right
    (sf-ui, repo), or fewer where `init` is right (the explicit in-place and non-Git requests)?"""
    lines: list[str] = []
    problems: list[str] = []
    for arm in ("C", "T2"):   # registered: a host that does not reach the start in most sessions is unreadable, not fine; judged
        # per arm, because the other arm's sessions would otherwise hold the aggregate at half (Sol's review, 2026-11-01)
        total = sum(c["n"] for (_, a), c in cells.items() if a == arm)
        nostart = sum(c["none"] for (_, a), c in cells.items() if a == arm)
        if total and nostart * 2 > total:
            lines.append(f"{arm} sessions with no start: {nostart} of {total}")
            return lines, f"UNREADABLE: the host reached ShipLoop's start in only {total - nostart} of {total} {arm} sessions"
    for s in sorted({s for s, _ in cells}):
        c, t_ = cells[(s, "C")], cells[(s, "T2")]
        cn, tn = c["workspace"] + c["direct"], t_["workspace"] + t_["direct"]
        lines.append(f"{s}: init as the first start, C {c['direct']}/{cn}, T2 {t_['direct']}/{tn}; no start: C {c['none']}, T2 {t_['none']}")
        if s in ("sf-ui", "repo") and cn and tn:
            p_more = fisher_lower(t_["direct"], tn, c["direct"], cn)   # T2 has at least as many `init` starts as it does
            if t_["direct"] - c["direct"] >= HOSTS_MORE_INIT and p_more < HOSTS_P:
                problems.append(f"{s}: T2 starts with init more often than the old wording (p {p_more:.3f})")
    explicit = [s for s in sorted({s for s, _ in cells}) if s not in ("sf-ui", "repo")]
    if explicit:
        ci = sum(cells[(s, "C")]["direct"] for s in explicit)
        cn = sum(cells[(s, "C")]["workspace"] + cells[(s, "C")]["direct"] for s in explicit)
        ti = sum(cells[(s, "T2")]["direct"] for s in explicit)
        tn = sum(cells[(s, "T2")]["workspace"] + cells[(s, "T2")]["direct"] for s in explicit)
        p = fisher_lower(ci, cn, ti, tn) if cn and tn else 1.0
        drop = (ci / cn - ti / tn) if cn and tn else 0.0
        lines.append(f"explicit in-place and non-Git requests pooled: C {ci}/{cn} ({ci / max(cn, 1):.2f}), T2 {ti}/{tn} "
                     f"({ti / max(tn, 1):.2f}); drop {drop:+.2f}; one-sided p (T2 lower) {p:.4f}")
        if drop >= INPLACE_POOLED_DROP and p < INPLACE_P:
            problems.append("explicit requests: T2 lowers init (pooled)")
    dark = dark_cells(cells)
    if dark and not problems:
        return lines, f"UNREADABLE: no session reached the start in {', '.join(dark)}, so there is nothing to compare there"
    return lines, ("REGRESSION: " + "; ".join(problems)) if problems else "NO REGRESSION FOUND"


GUARD_MIN_REFUSED = 8        # refused sf-ui sessions needed before the recovery rate can be judged at all
GUARD_SHARE = 0.80           # the share that must end on the right route, with the Wilson lower bound below
GUARD_LOWER = 0.50
GUARD_QUIET_MAX_WRONG = 1    # G sessions that were never refused may end off `workspace` at most this often


def tally_guard(rows: list[dict]) -> dict:
    cells: dict = {}
    for stimulus in sorted({r["stimulus"] for r in rows}):
        for arm in sorted({r["arm"] for r in rows if r["stimulus"] == stimulus}):
            mine = [r for r in rows if r["stimulus"] == stimulus and r["arm"] == arm]
            cells[(stimulus, arm)] = {
                "n": len(mine), "refused": sum(bool(r.get("refused")) for r in mine),
                "first_direct": sum(r["start"] == "direct" for r in mine),
                "final_workspace": sum(r.get("final_route") == "workspace" for r in mine),
                "final_direct": sum(r.get("final_route") == "direct" for r in mine),
                "final_none": sum(r.get("final_route") is None for r in mine),
                "in_place": sum(any(st.get("in_place") for st in r.get("starts", [])) for r in mine)}
    return cells


GUARD_CELLS = (("sf-ui", "GOLD"), ("sf-ui", "G"), ("inplace-hello", "G"), ("nogit-hello", "G"))   # the registered design's cells


def evaluate_guard(rows: list[dict], gate: str = "h1") -> tuple[list[str], str]:
    """The registered rule of the guard probe: do sessions recover to the isolated entry after a refusal (H1), are explicit
    in-place requests still honored (H2), and do sessions that start right stay right (H3). The second probe gates on E
    instead of H1 (--gate e): of the sf-ui sessions whose first start was `init`, refused or not, how many end on
    workspace start. Both are always printed."""
    lines: list[str] = []
    sf = [r for r in rows if r["stimulus"] == "sf-ui"]
    refused = [r for r in sf if r.get("refused")]
    ws = sum(r.get("final_route") == "workspace" for r in refused)
    n = len(refused)
    lo, hi = wilson(ws, n) if n else (0.0, 0.0)
    if n < GUARD_MIN_REFUSED:
        h1 = None
        lines.append(f"H1 recovery: {ws} of {n} refused sf-ui sessions ended on workspace start: INSUFFICIENT "
                     f"(at least {GUARD_MIN_REFUSED} refused sessions are needed)")
    else:
        h1 = ws / n >= GUARD_SHARE and lo >= GUARD_LOWER
        lines.append(f"H1 recovery: {ws} of {n} refused sf-ui sessions ended on workspace start ({ws / n:.2f}, Wilson "
                     f"{lo:.2f}-{hi:.2f}; needs {GUARD_SHARE:.2f} and a lower bound of {GUARD_LOWER:.2f}): {'MET' if h1 else 'NOT MET'}")
    inits = [r for r in sf if r["start"] == "direct"]
    e_ws = sum(r.get("final_route") == "workspace" for r in inits)
    e_n = len(inits)
    elo, ehi = wilson(e_ws, e_n) if e_n else (0.0, 0.0)
    flagged = sum(any(st.get("in_place") for st in r.get("starts", [])[:1]) for r in inits)
    if e_n < GUARD_MIN_REFUSED:
        e_ok = None
        lines.append(f"E effectiveness: {e_ws} of {e_n} sf-ui sessions whose first start was init ended on workspace start: "
                     f"INSUFFICIENT (at least {GUARD_MIN_REFUSED} are needed)")
    else:
        e_ok = e_ws / e_n >= GUARD_SHARE and elo >= GUARD_LOWER
        lines.append(f"E effectiveness: {e_ws} of {e_n} sf-ui sessions whose first start was init ended on workspace start "
                     f"({e_ws / e_n:.2f}, Wilson {elo:.2f}-{ehi:.2f}; needs {GUARD_SHARE:.2f} and {GUARD_LOWER:.2f}): "
                     f"{'MET' if e_ok else 'NOT MET'}")
    lines.append(f"    of those {e_n}, {flagged} already carried --in-place on that first command (so the guard could not "
                 f"refuse them), {sum(bool(r.get('refused')) for r in inits)} were refused")
    if gate == "e":
        h1 = e_ok
    by_arm = {a: [r for r in refused if r["arm"] == a] for a in sorted({r["arm"] for r in sf})}
    lines.append("    refused sessions by build: " + ", ".join(f"{a} {len(v)}" for a, v in by_arm.items()))
    bypass = [r for r in refused if any(st.get("in_place") for st in r.get("starts", []))]
    lines.append(f"    of the refused sessions, {len(bypass)} then ran init with --in-place without the user's request "
                 f"(final routes: workspace {ws}, direct {sum(r.get('final_route') == 'direct' for r in refused)}, "
                 f"no run {sum(r.get('final_route') is None for r in refused)})")
    explicit = [r for r in rows if r["stimulus"] in ("inplace-hello", "nogit-hello")]
    direct = sum(r.get("final_route") == "direct" for r in explicit)
    m = len(explicit)
    lo2, hi2 = wilson(direct, m) if m else (0.0, 0.0)
    h2 = m > 0 and direct / m >= GUARD_SHARE and lo2 >= GUARD_LOWER
    lines.append(f"H2 explicit requests: {direct} of {m} ended on the direct entry ({direct / m if m else 0:.2f}, Wilson "
                 f"{lo2:.2f}-{hi2:.2f}; needs {GUARD_SHARE:.2f} and {GUARD_LOWER:.2f}): {'MET' if h2 else 'NOT MET'}")
    sees = sum(bool(r.get("refused")) for r in explicit)
    lines.append(f"    explicit sessions the guard refused first: {sees} (they then needed --in-place; final direct counted above)")
    quiet = [r for r in sf if r["arm"] == "G" and not r.get("refused")]
    off = sum(r.get("final_route") != "workspace" for r in quiet)
    h3 = bool(quiet) and off <= GUARD_QUIET_MAX_WRONG   # H3 cannot pass on no observations
    lines.append(f"H3 sessions that start right: {len(quiet) - off} of {len(quiet)} unrefused G sf-ui sessions ended on workspace "
                 f"start (at most {GUARD_QUIET_MAX_WRONG} off allowed): {'MET' if h3 else 'NOT MET'}")
    nostart = sum(r.get("final_route") is None for r in rows)
    lines.append(f"not gated: sessions that never made a run: {nostart} of {len(rows)}")
    present = {(r["stimulus"], r["arm"]) for r in rows}
    absent = [cell for cell in GUARD_CELLS if cell not in present]
    if absent:   # a verdict over a partial design is no verdict (Astra's review: 8 GOLD + 4 explicit sessions printed RELEASE)
        lines.append("cells of the registered design with no valid session: " + ", ".join("/".join(c) for c in absent))
        return lines, "INSUFFICIENT: the registered design's cells are missing, so no condition is judged"
    if h1 is False or not h2 or not h3:
        verdict = "DO NOT RELEASE the guard as it stands (a registered condition is not met)"
    elif h1 is None:
        verdict = "INSUFFICIENT: H2 and H3 hold but too few sessions were refused to judge H1; add old-wording sessions"
    else:
        verdict = "RELEASE: H1, H2 and H3 are met"
    return lines, verdict


def card_sizes(arms_file: Path) -> dict:
    """The size of each arm's card. An arms file's edits are relative to the card of its day, and applying them to today's card gives
    other sizes (on 2.31.0 `arms.json` gives C 30,115 and T1 30,137, not the 30,011 and 30,033 it was run with), so the sizes recorded
    beside the file (`<name>.sizes.json`) are used when they exist."""
    recorded = arms_file.with_suffix(".sizes.json")
    if recorded.is_file():
        return json.loads(recorded.read_text())
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
    """The report lines and the arm selected: fewest wrong starts among the arms that meet the bar, then the smaller card."""
    lines, meeting = evaluate_arms(cells, arms_file)
    return lines, (min(meeting)[2] if meeting else None)


def evaluate_arms(cells: dict, arms_file: Path) -> tuple[list[str], list[tuple[int, int, str]]]:
    """The report lines and every arm that meets the bar, as (wrong starts, card bytes, arm)."""
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
    return lines, meeting


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
            "read_run_start", "self_bootstrap", "skill_seen", "installed_card_sha256", "effect_route",
            "final_route", "refused", "starts")
    out = {k: row.get(k) for k in keys}
    out["start_command"] = short(row.get("start_command"), 200)
    out["pre_start"] = [short(c, 110) for c in row.get("pre_start", [])[:6]]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("--export", type=Path)
    ap.add_argument("--arms", type=Path, default=HERE / "arms.json", help="the arms file the batch used (sizes)")
    ap.add_argument("--gate", choices=("h1", "e"), default="h1", help="guard mode: which rule decides (the first probe h1, the second e)")
    ap.add_argument("--mode", choices=("start", "inplace", "hosts", "guard"), default="start",
                    help="start: init is wrong (the bar and tie-break); inplace: init is right (is T2 harmless?); "
                         "hosts: one other host, both directions; guard: what a session does after init is refused")
    ap.add_argument("--also", type=Path, help="another batch's results: add a pooled table (descriptive only)")
    ap.add_argument("--plan", type=Path, help="the plan the batch ran (plan*.json): planned slots with no valid session make the verdict INSUFFICIENT")
    ap.add_argument("--replicates", type=Path,
                    help="another batch of the same experiment: judge it alone by the same rules and print whether the "
                         "same arm is selected in both (a selection from one batch is not yet a result)")
    ap.add_argument("--replicates-arms", type=Path, help="the arms file that batch used (default: --arms)")
    args = ap.parse_args()
    rows, dropped = load(args.results)
    if not rows:   # nothing to tally, and an empty tally must not read as "no harm"
        print(f"0 valid slots; slots with no valid attempt: {dropped or 'none'}")
        print(f"{'DECISION' if args.mode == 'start' else 'VERDICT'}: INSUFFICIENT: no valid session in {args.results}")
        return
    planned = {slot["slot"] for slot in json.loads(args.plan.read_text())} if args.plan else None
    missing = sorted(planned - {r["slot"] for r in rows}) if planned is not None else []
    gaps = (f"{len(missing)} planned slot(s) have no valid session ({', '.join(map(str, missing[:12]))}{'...' if len(missing) > 12 else ''})"
            if missing else "")

    def settled(verdict: str) -> str:
        """A verdict over a batch with planned slots missing is no verdict: say so and keep the arithmetic's reading beside it. So is
        one with no plan to count against: thirteen rows of a 104-slot batch met every condition and printed RELEASE (Sol's review,
        2026-11-01)."""
        if planned is None:
            return f"INSUFFICIENT: no --plan was given, so the registered design's completeness is not checked (the data as they stand read: {verdict})"
        return f"INSUFFICIENT: {gaps} (the data as they stand read: {verdict})" if gaps else verdict

    if args.mode == "guard":
        print(f"{len(rows)} valid slots; slots with no valid attempt: {dropped or 'none'}")
        print(f"{'request':13s} {'build':5s} {'n':>3s} {'refused':>7s} {'first init':>10s} {'final ws':>8s} {'final direct':>12s} "
              f"{'no run':>6s} {'--in-place':>10s}")
        for (stimulus, arm), c in tally_guard(rows).items():
            print(f"{stimulus:13s} {arm:5s} {c['n']:3d} {c['refused']:7d} {c['first_direct']:10d} {c['final_workspace']:8d} "
                  f"{c['final_direct']:12d} {c['final_none']:6d} {c['in_place']:10d}")
        lines, verdict = evaluate_guard(rows, args.gate)
        print()
        print("\n".join(lines))
        print()
        print(f"VERDICT: {settled(verdict)}")
        if args.export:
            args.export.write_text("".join(json.dumps(compact(r)) + "\n" for r in rows))
            print(f"wrote {args.export}")
        return
    cells = tally(rows)
    print(f"{len(rows)} valid slots; slots with no valid attempt: {dropped or 'none'}")
    label = "wrong rate (95% CI)" if args.mode == "start" else "init share (95% CI)"
    print(f"{'request':13s} {'arm':3s} {'n':>3s} {'workspace':>9s} {'direct':>6s} {'none':>4s} {label:>22s} "
          f"{'bootstrap':>9s} {'read run-start':>14s} {'median s':>8s}")
    for (stimulus, arm), c in cells.items():
        started = c["workspace"] + c["direct"]
        lo, hi = wilson(c["direct"], started)
        rate = f"{c['direct'] / started:.2f} ({lo:.2f}-{hi:.2f})" if started else "-"
        median = c["seconds"][len(c["seconds"]) // 2] if c["seconds"] else "-"
        print(f"{stimulus:13s} {arm:3s} {c['n']:3d} {c['workspace']:9d} {c['direct']:6d} {c['none']:4d} {rate:>22s} "
              f"{c['bootstrap']:9d} {c['read_run_start']:14d} {median!s:>8s}")
    if args.mode in ("inplace", "hosts"):
        lines, verdict = (evaluate_inplace if args.mode == "inplace" else evaluate_hosts)(cells)
        print()
        print("\n".join(lines))
        print()
        print(f"VERDICT: {settled(verdict)}")
        winner = None
    else:
        lines, winner = evaluate(cells, args.arms)
        print()
        print("\n".join(lines))
        print()
        decision = f"ship {winner}" if winner else "ship nothing (no candidate meets the pre-registered bar)"
        print(f"DECISION: {settled(decision)}")
    if args.replicates:
        if args.mode != "start":
            raise SystemExit("--replicates is for the start set")
        again, _ = load(args.replicates)
        _, meeting = evaluate_arms(tally(again), args.replicates_arms or args.arms)
        others = sorted(arm for _, _, arm in meeting)
        print()
        print(f"REPLICATION (this batch and {args.replicates.name}, each judged alone by the same rules):")
        print(f"    this batch selects {winner or 'nothing'}; the arms meeting the bar in {args.replicates.name}: "
              f"{', '.join(others) or 'none'}")
        print("    REPLICATED: " + (f"yes, {winner} meets the bar in both batches" if winner in others
                                    else "NO, so the selection above rests on one batch"))
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
