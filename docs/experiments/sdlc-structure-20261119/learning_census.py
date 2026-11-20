#!/usr/bin/env python3
"""Do the learnings ShipLoop already records change what a later step does, and do refusals repeat within a run?

Reads iteration_census.py's output (ITERATION.json: every build step with its action ids, its refusals and its
seconds, and every refused callback of the run with its text) and, from each run folder, the accepted `implement`
result (`learned`, `decisions`, `learned_from`), the look-back block of the `implement` packet, and the
carry-forward result's skill decision.

It prints:
  1. how often each learning field is filled, and how often `learned_from` names a commit, by whether the packet's
     look-back showed an earlier step's learning;
  2. whether steps that cite an earlier learning are refused less or take less time than steps that could have and
     did not, pooled and within the same case and model (a Mantel-Haenszel difference);
  3. whether the seeded-fault refusal of the `test` stage becomes rarer as an item's steps go on, and whether a
     refusal at one step predicts one at the next, pooled and within case and model;
  4. how many refusals repeat a refusal already met earlier in the same run at another action, by ShipLoop's own
     refusal text, and what the repeats cost in seconds.

With --sample N it also writes N `learned` lines (fixed seed) for judges to label.

Usage: python3 -I learning_census.py ITERATION.json [--sample N OUT.jsonl]
"""
import collections
import json
import pathlib
import random
import re
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import iteration_census as base

SEED = 20261120


def result_of(rundir, action):
    record = base.state(rundir / "results" / f"{action}.md") or {}
    inner = record.get("result")
    return inner if isinstance(inner, dict) else record


def klass(text):
    """A refusal's class: ShipLoop's own first words, with paths, ids and numbers taken out."""
    text = text.split("the check says no.", 1)[-1] if "the check says no." in text else text
    text = re.sub(r"/Users/\S+", "PATH", text.strip())
    text = re.sub(r"nav-[0-9a-f]+", "ID", text)
    text = re.sub(r"\b[A-Za-z]{1,4}[-_]?\d+[a-z]?\b", "N", text)
    text = re.sub(r"\d+", "N", text)
    return " ".join(text.split())[:64]


def mantel_haenszel(strata):
    """Risk difference of group 1 against group 0 over strata of (events1, n1, events0, n0)."""
    weight = sum(n1 * n0 / (n1 + n0) for _, n1, _, n0 in strata if n1 and n0)
    if not weight:
        return None, 0
    total = sum((e1 / n1 - e0 / n0) * n1 * n0 / (n1 + n0) for e1, n1, e0, n0 in strata if n1 and n0)
    return total / weight, sum(1 for _, n1, _, n0 in strata if n1 and n0)


def rate(events, total):
    return f"{events} of {total} ({events / total:.0%})" if total else "0 of 0"


def main(argv):
    data = json.loads(pathlib.Path(argv[0]).read_text())
    by_run = collections.defaultdict(list)
    for step in data["steps"]:
        by_run[step["run"]].append(step)
    rows, samples = [], []
    for run, steps in by_run.items():
        rundir = pathlib.Path(run).parent
        index = collections.Counter()
        for step in steps:
            index[step["item"]] += 1
            action = step["actions"]["implement"]
            result = result_of(rundir, action)
            learned = [line for line in result.get("learned") or [] if isinstance(line, str)]
            real = [line for line in learned if line.strip().lower() != "none"]
            try:
                packet = (rundir / "packets" / f"{action}.md").read_text(errors="replace")
            except OSError:
                packet = ""
            block = packet[packet.find("Look back"):][:4000] if "Look back" in packet else ""
            test = step.get("test") or {}
            rows.append({
                "run": run, "case": step.get("case"), "model": step.get("model"), "item": step["item"],
                "index": index[step["item"]], "has_field": "learned" in result, "real": len(real),
                "chars": sum(len(line) for line in real), "cited": bool(result.get("learned_from")),
                "shown": "| learned:" in block, "looked": bool(block),
                "refused": bool(step.get("test_refused")), "weak": "tests too weak (a seeded fault survived)" in (test.get("refusals") or []),
                "has_test": "test" in step, "seconds": step["implement_s"] + step.get("test_s", 0.0)})
            for line in real:
                samples.append({"case": step.get("case"), "model": step.get("model"), "step": index[step["item"]],
                                "summary": str(result.get("summary") or result.get("headline") or "")[:300], "learned": line})

    print(f"build steps read: {len(rows)} in {len(by_run)} runs")
    print("\n== 1. are the fields filled, and is an earlier learning cited? ==")
    done = [r for r in rows if r["has_field"]]
    print(f"implement results that hold a `learned` list: {rate(len(done), len(rows))}; with at least one line that is not \"none\": "
          f"{rate(sum(r['real'] > 0 for r in done), len(done))}; lines per step median "
          f"{statistics.median(r['real'] for r in done):.0f}, characters median {statistics.median(r['chars'] for r in done):.0f}")
    looked = [r for r in rows if r["looked"]]
    shown = [r for r in looked if r["shown"]]
    blank = [r for r in looked if not r["shown"]]
    print(f"implement packets with a look-back block: {rate(len(looked), len(rows))}; it showed an earlier step's learning in "
          f"{rate(len(shown), len(looked))}")
    print(f"`learned_from` names a commit: when a learning was shown {rate(sum(r['cited'] for r in shown), len(shown))}; "
          f"when none was shown {rate(sum(r['cited'] for r in blank), len(blank))}")

    print("\n== 2. do steps that cite an earlier learning do better? (steps whose look-back showed one, with a test stage) ==")
    pool = [r for r in shown if r["has_test"]]
    cited = [r for r in pool if r["cited"]]
    plain = [r for r in pool if not r["cited"]]
    for label, key in (("`test` refused at least once", "refused"), ("refused for a seeded fault", "weak")):
        strata = collections.defaultdict(lambda: [0, 0, 0, 0])
        for r in pool:
            cell = strata[(r["case"], r["model"])]
            cell[0 if r["cited"] else 2] += r[key]
            cell[1 if r["cited"] else 3] += 1
        difference, used = mantel_haenszel([tuple(c) for c in strata.values()])
        print(f"  {label}: cited {rate(sum(r[key] for r in cited), len(cited))}; not cited "
              f"{rate(sum(r[key] for r in plain), len(plain))}; within case and model "
              f"{'no stratum holds both' if difference is None else f'{difference:+.0%} points over {used} strata'}")
    ratios = []
    strata = collections.defaultdict(lambda: ([], []))
    for r in pool:
        strata[(r["case"], r["model"])][0 if r["cited"] else 1].append(r["seconds"])
    for with_citation, without in strata.values():
        if len(with_citation) >= 2 and len(without) >= 2:
            ratios.append(statistics.median(with_citation) / statistics.median(without))
    print(f"  implement plus test seconds: cited median {statistics.median(r['seconds'] for r in cited):.0f}, not cited "
          f"{statistics.median(r['seconds'] for r in plain):.0f}; within case and model the cited median is "
          f"{statistics.median(ratios):.2f} times the other (median over {len(ratios)} strata with two or more of each)"
          if cited and plain and ratios else "  seconds: too few to compare")

    print("\n== 3. does the seeded-fault refusal fade as an item's steps go on? (items of two or more steps) ==")
    items = collections.defaultdict(list)
    for r in rows:
        if r["has_test"]:
            items[(r["run"], r["item"])].append(r)
    multi = {key: sorted(group, key=lambda r: r["index"]) for key, group in items.items() if len(group) >= 2}
    by_index = collections.defaultdict(lambda: [0, 0])
    pairs = collections.defaultdict(lambda: [0, 0, 0, 0])
    after, fresh = [0, 0], [0, 0]
    for group in multi.values():
        for position, r in enumerate(group):
            slot = by_index[min(position + 1, 4)]
            slot[0] += r["weak"]
            slot[1] += 1
            if position:
                earlier = group[position - 1]["weak"]
                cell = pairs[(r["case"], r["model"])]
                cell[0 if earlier else 2] += r["weak"]
                cell[1 if earlier else 3] += 1
                target = after if earlier else fresh
                target[0] += r["weak"]
                target[1] += 1
    print(f"  items: {len(multi)}; refused for a seeded fault at step 1 {rate(*by_index[1])}, step 2 {rate(*by_index[2])}, "
          f"step 3 {rate(*by_index[3])}, step 4 or later {rate(*by_index[4])}")
    difference, used = mantel_haenszel([tuple(c) for c in pairs.values()])
    print(f"  the next step is refused: after a refused step {rate(*after)}; after a step that was not {rate(*fresh)}; within "
          f"case and model {'no stratum holds both' if difference is None else f'{difference:+.0%} points over {used} strata'}")

    print("\n== 4. refusals that repeat one already met earlier in the same run, at another action ==")
    total = repeats = 0
    seconds = repeat_seconds = run_seconds = 0.0
    classes, repeated_stage = collections.Counter(), collections.Counter()
    for run in data["runs"]:
        seen = {}
        run_seconds += run.get("seconds") or 0.0
        for refusal in run.get("refusals") or []:
            key = (refusal["stage"], klass(refusal["text"]))
            total += 1
            seconds += refusal["tail"] or 0.0
            if key in seen and seen[key] != refusal["action"]:
                repeats += 1
                repeat_seconds += refusal["tail"] or 0.0
                classes[key] += 1
                repeated_stage[refusal["stage"]] += 1
            seen.setdefault(key, refusal["action"])
    print(f"  refused check or complete commands with a text: {total}; repeats of a class met earlier in the run at another action: "
          f"{rate(repeats, total)}")
    print(f"  seconds from a refusal to the next accepted check of its action: all refusals {seconds / run_seconds:.1%} of run time; "
          f"the repeats {repeat_seconds / run_seconds:.1%}")
    print("  repeats by stage: " + ", ".join(f"{stage} {count}" for stage, count in repeated_stage.most_common()))
    for (stage, text), count in classes.most_common(8):
        print(f"    {count:>4}  {stage}: {text}")

    decisions = collections.Counter()
    for run in by_run:
        rundir = pathlib.Path(run).parent
        for path in (rundir / "results").glob("nav-*.md"):
            record = base.state(path) or {}
            if record.get("stage") == "carry-forward":
                skill = (record.get("result") or {}).get("skill")
                if isinstance(skill, dict):
                    decisions[skill.get("decision")] += 1
    print(f"\n== carry-forward skill decisions: {dict(decisions)} ==")

    if "--sample" in argv:
        count, out = int(argv[argv.index("--sample") + 1]), pathlib.Path(argv[argv.index("--sample") + 2])
        random.Random(SEED).shuffle(samples)
        with out.open("w") as handle:
            for number, sample in enumerate(samples[:count], 1):
                handle.write(json.dumps({"id": number, **sample}) + "\n")
        print(f"\nwrote {min(count, len(samples))} of {len(samples)} learned lines to {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
