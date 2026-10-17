"""The packet obligation ledger: load it, render the packets it covers, check every row (ShipLoop efficiency plan, G-LEDGER).

    python3 test/shiploop_e2e/obligations.py            # check the ledger against this checkout's packets; exit 0 when every row holds
    python3 test/shiploop_e2e/obligations.py --arm-checks DIR   # also write DIR/arm-checks.json: the rows this checkout loses (arms.py reads it)

packet_obligations.json says what each packet must carry and where (see its ``_about``). The check renders the packets with
this checkout's navigator and walks no model, no project and no network:

* the dry-run walk of the whole graph (all 24 stages and the Improve parent packets between them, shiploop_navigator_dry_run),
  on both delegation routes: each packet as the packet file holds it (``file``) and as ``emit`` prints it (``printed``: the
  whole text up to PRINT_LIMIT, else ``packet_head``);
* the offline step slice of a case (packets.py ``offline_packets``): the inner loop with a real step plan, both routes.

A row is checked in every packet of its ``kinds`` where its ``when`` condition holds. ``check`` returns the violations and writes
nothing; a unit that moves an obligation changes the ledger in the same commit.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LEDGER = HERE / "packet_obligations.json"
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
SCHEMA = "shiploop-packet-obligations/v1"
SURFACES = ("head", "file")
KINDS = ("producer", "improve")
ROUTES = ("inline", "ask-agent")
SLICE_CASE = "node-fix-bug"


def _imports():
    for path in (str(SCRIPTS), str(HERE)):
        if path not in sys.path:
            sys.path.insert(0, path)
    import shiploop_navigator as navigator
    import shiploop_navigator_dry_run as dry_run
    import packets
    return navigator, dry_run, packets


def load(path: Path = LEDGER) -> dict:
    """The ledger, checked for shape: a schema, unique ids, a known surface and kinds, and anchors that name alternatives and a
    source file in this repository."""
    ledger = json.loads(Path(path).read_text())
    if ledger.get("schema") != SCHEMA:
        raise ValueError(f"{path}: schema must be {SCHEMA}")
    seen = set()
    for row in ledger["obligations"]:
        if row["id"] in seen:
            raise ValueError(f"duplicate obligation id {row['id']}")
        seen.add(row["id"])
        if row["surface"] not in SURFACES or not row["kinds"] or not set(row["kinds"]) <= set(KINDS):
            raise ValueError(f"{row['id']}: surface must be one of {SURFACES} and kinds a subset of {KINDS}")
        if not row["anchors"]:
            raise ValueError(f"{row['id']}: no anchors")
        for anchor in row["anchors"]:
            if not anchor["any"] or not all(isinstance(t, str) and t for t in anchor["any"]):
                raise ValueError(f"{row['id']}: an anchor needs non-empty alternatives")
            if not (ROOT / anchor["source"]).is_file():
                raise ValueError(f"{row['id']}: source {anchor['source']} is not a file")
    return ledger


def source_violations(ledger: dict) -> list[dict]:
    """The anchors none of whose alternatives is in the source file they name: a token is derived from source."""
    found = []
    for row in ledger["obligations"]:
        for anchor in row["anchors"]:
            text = (ROOT / anchor["source"]).read_text(errors="replace")
            if not any(token in text for token in anchor["any"]):
                found.append({"id": row["id"], "source": anchor["source"], "any": anchor["any"]})
    return found


def dry_run_packets(route: str) -> list[dict]:
    """Every packet of the dry-run delivery scenario: ``{"where", "stage", "kind", "file", "printed"}``. ``file`` is the packet
    as the packet file holds it, ``printed`` what ``emit`` prints for it."""
    navigator, dry_run, _packets = _imports()
    state = navigator.new_state("/simulation-only/repo", "Inspect the SDLC graph with synthetic declarations.",
                                improve_skill=str(dry_run.stage_loops.BUNDLED_IMPROVE_CARD), delegation=route)
    found = []
    for number, step in enumerate(dry_run.scenarios()["delivery"]["steps"], 1):
        stage = navigator.sequence_stage(state)
        action = navigator.current_action(state)
        text = navigator.render(dry_run.CORE, dry_run.RUN, state)
        printed = text if len(text) <= navigator.PRINT_LIMIT else navigator.packet_head(
            dry_run.CORE, dry_run.RUN, state, navigator.packet_path(dry_run.RUN, state))
        found.append({"where": f"dry-run {route} {number:02d}-{stage}", "stage": stage,
                      "kind": "improve" if stage == navigator.IMPROVE_STAGE else "producer", "file": text, "printed": printed})
        command = step.get("command", "done")
        if command == "finish-improve":
            state = navigator.finish_improve(state, state["active_improve"]["action_id"], step.get("receipt"), step.get("final_result"))
        else:
            state = navigator.apply(state, action["id"], step.get("result", {"outcome": "done", "summary": "Synthetic."}))
    return found


def slice_packets(route: str, case: str = SLICE_CASE) -> list[dict]:
    """The offline step slice's packets of ``case`` (the inner loop with a real step plan), in the same shape."""
    _navigator, _dry_run, packets = _imports()
    cases = json.loads((HERE / "step_cases.json").read_text())
    whole = packets.offline_packets(cases[case], delegation=route)
    printed = packets.offline_packets(cases[case], delegation=route, printed=True)
    return [{"where": f"slice {case} {route} {key}", "stage": key.split("-", 1)[1],
             "kind": "improve" if key.endswith("-improve") else "producer", "file": whole[key], "printed": printed[key]}
            for key in whole]


def all_packets() -> list[dict]:
    return [p for route in ROUTES for p in (*dry_run_packets(route), *slice_packets(route))]


def check(ledger: dict, packets: list[dict], drop: tuple[str, ...] | str = ()) -> list[dict]:
    """The violations: ``{"id", "where", "surface", "missing"}`` for each row and packet where an anchor has none of its
    alternatives. ``drop`` removes those tokens from every text first, which is how a test proves a row notices a lost token."""
    found = []
    for packet in packets:
        texts = {surface: packet[{"head": "printed", "file": "file"}[surface]] for surface in SURFACES}
        for token in ((drop,) if isinstance(drop, str) else drop):
            texts = {surface: text.replace(token, "") for surface, text in texts.items()}
        for row in ledger["obligations"]:
            if packet["kind"] not in row["kinds"]:
                continue
            condition = row.get("when", {}).get("file_has")
            if condition and condition not in packet["file"]:
                continue
            text = texts[row["surface"]]
            for anchor in row["anchors"]:
                if not any(token in text for token in anchor["any"]):
                    found.append({"id": row["id"], "where": packet["where"], "surface": row["surface"], "missing": anchor["any"]})
    return found


def lost(ledger: dict, packets: list[dict]) -> list[str]:
    """The ids of the rows that do not hold, once each, in ledger order."""
    broken = {v["id"] for v in check(ledger, packets)}
    return [row["id"] for row in ledger["obligations"] if row["id"] in broken]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    ledger_path, arm_dir = LEDGER, None
    while args:
        flag = args.pop(0)
        if flag == "--ledger" and args:
            ledger_path = Path(args.pop(0))
        elif flag == "--arm-checks" and args:
            arm_dir = Path(args.pop(0))
        else:
            sys.stderr.write(__doc__)
            return 2
    ledger = load(ledger_path)
    packets = all_packets()
    problems = [f"source: {v['id']} {v['any']} is not in {v['source']}" for v in source_violations(ledger)]
    problems += [f"{v['id']} ({v['surface']}) missing {v['missing']} in {v['where']}" for v in check(ledger, packets)]
    for line in problems:
        print(line)
    print(f"{len(ledger['obligations'])} obligations, {len(problems)} violations")
    if arm_dir is not None:
        target = arm_dir / "arm-checks.json"
        try:
            record = json.loads(target.read_text())
        except (OSError, ValueError):
            record = {}
        record["obligations_lost"] = lost(ledger, packets)
        target.write_text(json.dumps(record, indent=1) + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
