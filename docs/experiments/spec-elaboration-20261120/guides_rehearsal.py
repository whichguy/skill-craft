#!/usr/bin/env python3
"""An offline rehearsal of guides_test.py, with no model: prepare, launch and watch, collect, blind copies, sealing, audit, score.

    guides_rehearsal.py TEMPLATE_RUN SCRATCH_ROOT

TEMPLATE_RUN is the output folder of any real run that was stopped when its specification was accepted (it is only read).
SCRATCH_ROOT must not exist and must be outside the checkout. The harness is replaced by a stub (this file, started with
GUIDES_STUB set) that lays the template's records down as a run would write them: first without the acceptance, then with
it, and then waits for the stop file; it also lays down the host's own session record, which says what the model was
given, with the arm's packet text in it. Everything guides_test.py would write into the checkout (labels, blind copies,
grades, session folders) is pointed at SCRATCH_ROOT. The sorter's and the judges' sessions are replaced by functions that
write made-up answers, and the reader's file is made up: what is rehearsed is the handling, not any judgement.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SKIP = shutil.ignore_patterns(
    "home",
    "work",
    "worktree",
    "stop",
    "spec-as-*.md",
    "review-export",
    "delivery",
    "flow.*",
    "transcript.md",
)


def stub() -> int:
    """Stand in for test/shiploop_e2e/run.py: write a run's records the way one arm's run would, by the mode asked for."""
    import guides_test as g

    plan, argv = json.loads(os.environ["GUIDES_STUB"]), sys.argv[1:]

    def arg(name: str) -> str:
        return argv[argv.index(name) + 1]

    final, plugin, prior = (
        Path(arg("--output")),
        Path(arg("--plugin-dir")),
        Path(arg("--continue-from")),
    )
    arm = final.name.rsplit("-", 1)[-1]
    mode = plan["modes"][arm]
    if mode == "nofolder":
        time.sleep(300)
        return 0
    out = final.with_name(
        final.name + ".building"
    )  # the output folder appears whole, as the watcher would meet a run's
    shutil.copytree(plan["template"], out, ignore=SKIP)
    run = g.chosen_run(out)
    lines = (run / "trace.jsonl").read_text().splitlines(keepends=True)
    rows = [json.loads(line) for line in lines]
    last = rows.index(g.acceptance(rows)[0])
    (run / "trace.jsonl").write_text(
        "".join(lines[: last - 1])
    )  # neither the next packet nor the accepting command
    (out / "prompt.txt").write_text(arg("--prompt") + "\n")
    invocation = json.loads((out / "invocation.json").read_text())
    invocation.update(
        plugin_dir=str(plugin),
        plugin={**(invocation.get("plugin") or {}), "wanted": str(plugin)},
    )
    (out / "invocation.json").write_text(json.dumps(invocation))
    loaded = (
        out
        / "home/.codex/plugins/cache/stub/skill-craft/0/skills/shiploop/scripts/shiploop_prompts.py"
    )
    loaded.parent.mkdir(parents=True)
    shutil.copyfile(plugin / "skills/shiploop/scripts/shiploop_prompts.py", loaded)
    edits = g.overlay_docs()[g.ARM_OVERLAY[arm]]["edits"] if g.ARM_OVERLAY[arm] else []
    printed = next(
        run / row["file"]
        for row in rows
        if row.get("kind") == "packet" and row.get("stage") == "spec"
    )
    assert all(printed.read_text().count(edit["old"]) == 1 for edit in edits), (
        "the template's spec packet is of another build"
    )

    def as_given(text: str) -> str:
        """The arm's packet text in an output the model was given; in mode "skim" only the head of the spec packet."""
        for edit in edits:
            text = text.replace(edit["old"], edit["new"])
        mark = text.find("ShipLoop navigator | spec | revision")
        return text[: mark + 1500] if mode == "skim" and mark >= 0 else text

    kept = printed.read_text()
    for edit in edits:
        kept = kept.replace(edit["old"], edit["new"])
    printed.write_text(kept)
    shutil.copytree(
        Path(plan["template"]) / "home/.codex/sessions", out / "home/.codex/sessions"
    )
    for record in (out / "home/.codex/sessions").rglob("rollout-*.jsonl"):
        told = [
            json.loads(line) for line in record.read_text().splitlines() if line.strip()
        ]
        for row in told:
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            if str(payload.get("type") or "").endswith("_output") and isinstance(
                payload.get("output"), list
            ):
                for part in payload["output"]:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        part["text"] = as_given(part["text"])
        record.write_text("".join(json.dumps(row) + "\n" for row in told))
    result = json.loads((out / "result.json").read_text())
    head = subprocess.run(
        ["git", "-C", str(prior / "work"), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    result["follow_on"] = {"prior": str(prior), "start_head": head}
    (out / "result.json").unlink()
    out.rename(final)
    out, run = final, g.chosen_run(final)
    if mode == "exit":
        (
            result["process"]["status"],
            result["termination"]["resume_stop"],
            result["outcome_class"],
        ) = "exited", "the host ended its turn", "FAILED"
        (out / "result.json").write_text(json.dumps(result))
        return 0
    if mode in ("accept", "skim"):
        time.sleep(2)
        with (run / "trace.jsonl").open("a") as trace:
            trace.write("".join(lines[last - 1 : last + 1]))
    while not (out / "stop").exists():
        time.sleep(0.2)
    (out / "result.json").write_text(json.dumps(result))
    return 0


FAILED = []


def expect(what: str, held: bool, shown: object = "") -> None:
    print(
        ("ok    " if held else "FAIL  ")
        + what
        + (f"  [{shown}]" if shown != "" and not held else "")
    )
    if not held:
        FAILED.append(what)


def refuses(what: str, call, *args) -> None:
    try:
        call(*args)
    except SystemExit as stop:
        expect(f"refused: {what} ({str(stop)[:90]})", True)
    else:
        expect(f"refused: {what}", False, "it went through")


def main() -> int:
    import guides_test as g

    template, scratch = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    if scratch.exists():
        raise SystemExit("SCRATCH_ROOT must not exist")
    root = scratch / "root"
    g.LABELS, g.RESULTS, g.HARNESS = (
        scratch / "labels",
        scratch / "results",
        str(Path(__file__).resolve()),
    )
    g.grade.grades_dir = lambda round_name, tag=None: (
        scratch / "grades" / (f"{round_name}@{tag}" if tag else round_name)
    )
    g.labels_committed = lambda: (
        True
    )  # the label files here are made up and live in the scratch folder
    wanted = [n["id"] for n in g.grade.cases()[g.CASE]["nuances"]]

    print("== prepare: the base and the three arms, built for real")
    expect("prepare finds no problem", g.cmd_prepare(root, True) == 0)
    ready = json.loads((root / "prepare.json").read_text())
    ready["checkout_status_lines"] = (
        0  # rehearsal only: the checkout may hold uncommitted work
    )
    (root / "prepare.json").write_text(json.dumps(ready))

    print(
        "== sort: the command's handling, with a made-up sorter in place of the session"
    )
    g.grade.WORK, said = scratch / "sessions", {}

    def fake_sorter(prompt, cwd, judge, timeout):
        said["prompt"], said["files"] = (
            prompt,
            sorted(path.name for path in cwd.iterdir()),
        )
        (cwd / "verdict.json").write_text(json.dumps({"labels": said["labels"]}))
        return 0, None

    g.grade.run_session, g.LABELS = fake_sorter, scratch / "sort-labels"
    g.LABELS.mkdir(parents=True)
    rows = [
        {"id": i, "here": "mixed" if n == 3 else "applies", "why": "made up"}
        for n, i in enumerate(wanted)
    ]
    said["labels"] = rows
    refuses(
        "a mixed label that does not say which part applies", g.cmd_sort, "opus", 60
    )
    rows[3]["applies_part"] = "made up"
    said["labels"] = rows[:-1]
    refuses("a sort that leaves an item out", g.cmd_sort, "opus", 60)
    said["labels"] = rows
    expect("a complete sort is kept", g.cmd_sort("opus", 60) == 0)
    kept = json.loads((g.LABELS / "here-opus.json").read_text())
    expect(
        "the label file carries the sentence, the base's digest and 21 labels",
        (kept["request"], kept["fixture_digest"], len(kept["labels"]))
        == (g.REQUEST, g.brownfield.digest(g.FIXTURE), 21),
    )
    expect(
        "the sorter was given the registered text, the sentence, the base and the items",
        said["prompt"] == g.SORT_PROMPT
        and said["files"] == ["base", "items.json", "request.txt"],
        said["files"],
    )
    refuses("a second sort by the same sorter", g.cmd_sort, "opus", 60)
    g.LABELS = scratch / "labels"

    print("== the launch gate")
    refuses("a launch with no label files", g.cmd_run, root, "r1", "sol", 1.0)
    g.LABELS.mkdir(parents=True)

    def write_labels(labels: dict) -> None:
        for name, own in labels.items():
            rows = [
                {
                    "id": i,
                    "here": own[i],
                    "why": "made up",
                    **({"applies_part": "made up"} if own[i] == "mixed" else {}),
                }
                for i in wanted
            ]
            record = {
                "request": g.REQUEST,
                "fixture_digest": g.brownfield.digest(g.FIXTURE),
                "labels": rows,
            }
            (g.LABELS / f"here-{name}.json").write_text(json.dumps(record))

    few = {i: "applies" if n < 5 else "capability" for n, i in enumerate(wanted)}
    write_labels({"opus": few, "astra": few})
    refuses("a launch with five items that apply", g.cmd_run, root, "r1", "sol", 1.0)
    (root / "items.json").unlink()
    base = {
        i: "applies" if n < 12 or n >= 18 else "mixed" if n < 15 else "capability"
        for n, i in enumerate(wanted)
    }
    write_labels({"opus": base, "astra": {**base, wanted[18]: "unclear"}})
    refuses("a driver that is not registered", g.cmd_run, root, "r1", "sonnet", 1.0)

    print("== set r1: three runs that reach acceptance")
    os.environ["GUIDES_STUB"] = json.dumps(
        {
            "template": str(template),
            "modes": {"A": "accept", "C": "accept", "X": "accept"},
        }
    )
    expect("run returns cleanly", g.cmd_run(root, "r1", "sol", 1.0) == 0)
    items = json.loads((root / "items.json").read_text())
    expect(
        "14 items apply, 3 are capability, 4 are kept out of the rule",
        [len(items[k]) for k in ("applies", "capability", "other")] == [14, 3, 4],
        items,
    )
    for arm in g.ARMS:
        sample = json.loads(
            (root / "samples" / f"r1-sol-{arm}.sample.json").read_text()
        )
        seen = sample["seen"] or {}
        expect(
            f"{arm}: the watcher saw the acceptance and wrote the stop file",
            sample["watcher"] == "saw the acceptance" and sample["stop_written"],
            sample,
        )
        expect(
            f"{arm}: the working file was copied at acceptance",
            (root / "samples" / f"r1-sol-{arm}.spec-at-acceptance.md").is_file()
            and bool(seen.get("spec_sha256")),
        )
        expect(
            f"{arm}: the review's bind was kept when first seen",
            (
                root
                / "samples"
                / f"r1-sol-{arm}.binds"
                / f"{seen.get('spec_action')}-bind.md"
            ).is_file(),
        )
    refuses("a second launch of the same set", g.cmd_run, root, "r1", "sol", 1.0)
    expect("collect finds the set complete", g.cmd_collect(root, "r1-sol") == 0)
    refuses("a second collect of the same set", g.cmd_collect, root, "r1-sol")
    collected = {
        row["arm"]: row
        for row in json.loads((root / "collect-r1-sol.json").read_text())
    }
    for arm in g.ARMS:
        row = collected[arm]
        expect(f"{arm}: usable by every check", row["usable"], row["usable_checks"])
        expect(
            f"{arm}: delivered as the arm intends",
            row["delivered"] is True,
            row["delivery_checks"],
        )
        expect(
            f"{arm}: pinned by ShipLoop's own commit, review text from the kept bind",
            row["witness"].startswith("the accepting command")
            and row["bind_read_from"].startswith("the copy kept"),
        )
    expect(
        "the cue is in C's and X's packet and not in A's",
        [collected[a]["exposure"]["cue_shown"] for a in g.ARMS] == [False, True, True],
    )
    expect(
        "the guide text is in X's packet alone",
        [collected[a]["exposure"]["guide_block_shown_whole"] for a in g.ARMS]
        == [False, False, True],
    )
    manifest = g.manifest_of(root, "r1-sol")
    arm_code = {info["arm"]: code for code, info in manifest["slots"].items()}
    names = sorted(path.name for path in (g.RESULTS / manifest["round"]).iterdir())
    expect(
        "three blind copies whose names show no arm",
        len(names) == 3
        and all(name.split("__")[1] in arm_code.values() for name in names),
        names,
    )

    print(
        "== readings: made-up verdicts through the judging command, sealed, then compared"
    )
    refuses("a score before any reading", g.cmd_score, root, "r1-sol")
    state = {arm: {i: [0, 0] for i in wanted} for arm in g.ARMS}
    for arm in g.ARMS:
        for i in wanted[:6]:
            state[arm][i] = [2, 2]
        for i in wanted[6:9]:
            state[arm][i] = [1, 1]
    state["C"][wanted[6]] = [2, 1]  # higher under one judge only: not a difference
    state["X"].update(
        {
            wanted[6]: [2, 1],
            wanted[7]: [2, 2],
            wanted[9]: [2, 1],
            wanted[10]: [1, 1],
            wanted[11]: [2, 2],
            wanted[19]: [1, 2],
        }
    )
    word, prompts = {value: key for key, value in g.RANK.items()}, []

    def fake_judge(prompt, cwd, judge, timeout):
        prompts.append(prompt)
        arm = next(arm for arm, code in arm_code.items() if f"__{code}__" in cwd.name)
        which = 0 if judge["host"] == "claude" else 1
        (cwd / "verdict.json").write_text(
            json.dumps(
                {
                    "verdicts": [
                        {"id": i, "state": word[state[arm][i][which]]} for i in wanted
                    ]
                }
            )
        )
        return 0, None

    g.grade.run_session = fake_judge
    rubric = g.live_rubric()
    expect(
        "the live rubric is the bench judge's text with four phrases changed",
        rubric != g.grade.JUDGE_PROMPT
        and "R-n" in rubric
        and "C-n" not in rubric
        and "U-n" not in rubric,
    )
    expect(
        "judge takes six readings and seals them",
        g.cmd_judge(root, "r1-sol", 60) == 0 and len(prompts) == 6,
        len(prompts),
    )
    expect("every judge was given the live rubric", set(prompts) == {rubric})
    sealed = root / "judged-r1-sol.json"
    held = sealed.read_text()
    sealed.unlink()
    refuses("a score before the readings are sealed", g.cmd_score, root, "r1-sol")
    sealed.write_text(held)
    refuses("a score before the reader's audit", g.cmd_score, root, "r1-sol")
    expect(
        "the reader's folder is made",
        g.cmd_audit_pack(root, "r1-sol", scratch / "reader") == 0,
    )
    reader = sorted(path.name for path in (scratch / "reader").iterdir())
    expect(
        "the reader's folder holds the sentence, the base, three coded files and its instructions",
        reader
        == sorted(
            [
                "PROMPT.md",
                "base",
                "request.txt",
                *(f"{code}.md" for code in arm_code.values()),
            ]
        ),
        reader,
    )
    sentence = next(
        line
        for line in (scratch / "reader" / f"{arm_code['X']}.md")
        .read_text()
        .splitlines()
        if len(line) > 80
    )
    verdict = scratch / "reader-verdict.json"
    found = [
        {"spec": arm_code["X"], "requirement": "R-1", "quote": sentence[:70]},
        {
            "spec": arm_code["C"],
            "requirement": "R-2",
            "quote": "words that are in no specification at all",
        },
    ]
    verdict.write_text(
        json.dumps(
            {"capabilities": [{"capability": "made-up capability", "found": found}]}
        )
    )
    expect("the audit is checked", g.cmd_audit_check(root, "r1-sol", verdict) == 0)
    audit = json.loads((root / "audit-r1-sol.json").read_text())["capabilities"][0][
        "found"
    ]
    expect(
        "a true quote is verified and an invented one is not",
        [row["quote_is_in_the_file"] for row in audit] == [True, False],
        audit,
    )
    expect("score runs", g.cmd_score(root, "r1-sol") == 0)
    score = json.loads((root / "score-r1-sol.json").read_text())
    pair = score["pairs"]["X over C"]
    expect(
        "X over C: five higher, four of them newly raised, none lower",
        (pair["higher"], pair["newly_raised"], pair["lower"], pair["net"])
        == (
            [wanted[7], wanted[9], wanted[10], wanted[11], wanted[19]],
            [wanted[9], wanted[10], wanted[11], wanted[19]],
            [],
            5,
        ),
        pair,
    )
    expect(
        "C over A: nothing higher under both judges",
        score["pairs"]["C over A"]["higher"] == [],
    )
    expect(
        "capability in X alone turns the gain into harm",
        score["capability_in_x_alone"] == ["made-up capability"]
        and score["outcome"] == "a signal of harm",
        score["outcome"],
    )
    verdict.write_text(json.dumps({"capabilities": []}))
    g.cmd_audit_check(root, "r1-sol", verdict)
    g.cmd_score(root, "r1-sol")
    expect(
        "with no added capability the same readings are a signal worth repeating",
        json.loads((root / "score-r1-sol.json").read_text())["outcome"]
        == "a signal worth repeating",
    )

    print("== the rule, case by case")
    fine, gain = (
        dict.fromkeys(g.ARMS, True),
        {"higher": list("abcd"), "newly_raised": list("ab"), "lower": [], "net": 4},
    )
    expect(
        "unknown delivery comes first",
        g.outcome({**fine, "C": None}, gain, []).startswith("delivery unknown"),
    )
    expect(
        "failed delivery comes before any signal",
        g.outcome({**fine, "X": False}, gain, []).startswith("delivery failed"),
    )
    expect(
        "four lower on net is harm",
        g.outcome(
            fine,
            {"higher": [], "newly_raised": [], "lower": list("abcd"), "net": -4},
            [],
        )
        == "a signal of harm",
    )
    expect(
        "four higher with two newly raised is worth repeating",
        g.outcome(fine, gain, []) == "a signal worth repeating",
    )
    expect(
        "four higher with one newly raised is not",
        g.outcome(fine, {**gain, "newly_raised": ["a"]}, [])
        == "described only: no rule applies",
    )
    expect(
        "five higher and two lower is not",
        g.outcome(
            fine,
            {
                "higher": list("abcde"),
                "newly_raised": list("abc"),
                "lower": list("xy"),
                "net": 3,
            },
            [],
        )
        == "described only: no rule applies",
    )
    expect(
        "one either way is no signal",
        g.outcome(
            fine, {"higher": ["a"], "newly_raised": [], "lower": ["b"], "net": 0}, []
        )
        == "no signal",
    )

    print("== set r3: X's author gives itself only the head of its packet")
    os.environ["GUIDES_STUB"] = json.dumps(
        {
            "template": str(template),
            "modes": {"A": "accept", "C": "accept", "X": "skim"},
        }
    )
    expect("run returns cleanly", g.cmd_run(root, "r3", "sol", 1.0) == 0)
    expect("collect finds the set complete", g.cmd_collect(root, "r3-sol") == 0)
    skimmed = {
        row["arm"]: row
        for row in json.loads((root / "collect-r3-sol.json").read_text())
    }
    expect(
        "X is usable and not delivered: little of the instructions, no cue, no block",
        skimmed["X"]["usable"]
        and skimmed["X"]["delivered"] is False
        and not any(skimmed["X"]["delivery_checks"].values()),
        skimmed["X"]["delivery_checks"],
    )
    expect(
        "A and C are delivered",
        skimmed["A"]["delivered"] is True and skimmed["C"]["delivered"] is True,
    )
    expect(
        "the set reads as delivery failed",
        g.outcome(
            json.loads((root / "set-r3-sol.json").read_text())["delivered"], gain, []
        ).startswith("delivery failed"),
    )

    print("== tampering is caught")
    kept = g.grades_file(manifest, None, arm_code["A"])
    original = kept.read_text()
    kept.write_text(original.replace("covered", "absent", 1))
    refuses("a grade file changed after sealing", g.cmd_score, root, "r1-sol")
    kept.write_text(original)
    slot = g.slot_dir(manifest, arm_code["A"]) / "spec.md"
    text = slot.read_text()
    slot.write_text(text + "\nan added line\n")
    refuses("a blind copy changed after collecting", g.cmd_score, root, "r1-sol")
    slot.write_text(text)
    labels = (g.LABELS / "here-opus.json").read_text()
    (g.LABELS / "here-opus.json").write_text(
        labels.replace('"applies"', '"capability"', 1)
    )
    refuses("a label file changed after the first launch", g.frozen_items, root)
    (g.LABELS / "here-opus.json").write_text(labels)

    print(
        "== set r2: a run that never accepts, a launch that makes no folder, a run that ends by itself"
    )
    os.environ["GUIDES_STUB"] = json.dumps(
        {
            "template": str(template),
            "modes": {"A": "never", "C": "nofolder", "X": "exit"},
        }
    )
    began = time.time()
    expect("run returns cleanly", g.cmd_run(root, "r2", "sol", 0.1) == 0)
    expect(
        "the six-second limit is kept (all three decided within twenty seconds)",
        time.time() - began < 20,
        round(time.time() - began, 1),
    )
    told = {
        arm: json.loads((root / "samples" / f"r2-sol-{arm}.sample.json").read_text())
        for arm in g.ARMS
    }
    expect(
        "A: the time limit, and a stop file",
        told["A"]["watcher"] == "the time limit" and told["A"]["stop_written"],
        told["A"],
    )
    expect(
        "C: the time limit with no folder, so the launch was ended",
        told["C"]["watcher"].startswith("the time limit; no output folder")
        and told["C"]["returncode"] not in (0, None),
        told["C"],
    )
    expect(
        "X: the run ended with no acceptance",
        told["X"]["watcher"] == "the run ended with no acceptance"
        and not told["X"]["stop_written"],
        told["X"],
    )
    expect("collect reports the set incomplete", g.cmd_collect(root, "r2-sol") == 1)
    left = json.loads((root / "set-r2-sol.json").read_text())
    expect(
        "an incomplete set gets no blind copies",
        left["complete"] is False and left["round"] is None and left["slots"] == {},
    )
    refuses("judging an incomplete set", g.cmd_judge, root, "r2-sol", 60)
    endings = {
        row["arm"]: row.get("host_ending")
        for row in json.loads((root / "collect-r2-sol.json").read_text())
    }
    expect(
        "the endings are told apart",
        endings == {"A": "the stop file", "C": None, "X": "the host ended by itself"},
        endings,
    )

    print(f"\n{len(FAILED)} failed" if FAILED else "\nall held")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(
        stub() if os.environ.get("GUIDES_STUB") and "--output" in sys.argv else main()
    )
