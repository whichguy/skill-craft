#!/usr/bin/env python3
"""Build X2's spec-stage prompts (README.md, "X2"): arms A, D and C for each case and sample of one subject's intakes.

The frame mirrors the shipped spec packet (rendered by ``shiploop graph-dry-run --scenario delivery``): its Goal, Done
when and Checked by lines, the shipped duty ``shiploop_prompts.duty("spec", delegation="inline")``, the unattended rule,
the result template, the earlier results quoted by value and the original request.  The exercise has no tools, so spec.md
is written in a fenced ``spec.md`` block.  Discovery and research results are fixed per case and identical in every arm.
Arm D adds duty item 13 for prose; arm C quotes intake C's ledger and adds the same item phrased for Q-rows.

Arm B (X2b) is intake B's result with the shipped duty.  Writes spec/prompts/<slug>-<case>-<arm>-s<k>.md and
jobs-spec-<slug>[-<arms>].tsv.  Usage: build_spec.py [SUBJECT_SLUG] [ARMS, default A,D,C]
"""
import json
import subprocess
import sys

from common import CASES, HERE, SAMPLES, SKILL_SCRIPTS, SUBJECTS, envelope_text, intake_out, state_block

ARMS = ("A", "D", "C")

sys.path.insert(0, str(SKILL_SCRIPTS))
import shiploop_prompts  # noqa: E402

DUTY = shiploop_prompts.duty("spec", delegation="inline").rstrip("\n")
COMMIT = subprocess.run(["git", "-C", str(HERE), "rev-parse", "--short=8", "HEAD"], capture_output=True,
                        text=True).stdout.strip()

ITEM13 = {
    "A": "",
    "B": "",
    "D": ("13. Open questions and defaults. Every open question and every default the earlier results record (intake,\n"
          "    discovery, research) becomes an acceptance line under the R-<n> it shapes that pins the answer or the\n"
          "    default; mark a default `default` in that line. List each default you pin under `## Open questions` in\n"
          "    KNOWLEDGE/spec.md as `<the question> — default taken: <the value>; shapes R-<n>`, so the owner can confirm\n"
          "    it later."),
    "C": ("13. Questions. The intake result's `questions` rows (Q1..Qn) are the run's open questions. Each row becomes an\n"
          "    acceptance line under the R-<n> it shapes that pins the answer or the row's default and cites the row as\n"
          "    `(Q<n>)`; mark a default `default` in that line. List each row you settle by a default under\n"
          "    `## Open questions` in KNOWLEDGE/spec.md as `Q<n>: <the question> — default taken: <the value>; shapes\n"
          "    R-<n>`, so the owner can confirm it later."),
}

GREENFIELD_DISCOVERY = {
    "outcome": "done",
    "headline": "The repository is empty: no code, tests, conventions or configuration to build on.",
    "summary": ("Baseline: the checkout holds no code and no test suite, so there is nothing to run; missing coverage is "
                "recorded, not a failure. Installed runtimes: Node.js 26 and Python 3.13; git is available. No "
                "conventions, existing specs, repository skills, CI or deploy configuration exist; the result is "
                "returned as the repository checkout. Intake's open questions have no repository answer, so each stays "
                "with what intake recorded."),
}
GREENFIELD_RESEARCH = {
    "outcome": "done",
    "headline": "No consequential unknown needed a source beyond the request and the empty repository.",
    "summary": ("Research consulted no external source: the request names standard, well-documented runtimes, and the "
                "empty repository holds no convention to follow. Open questions and defaults stand as intake recorded "
                "them."),
}
BROWNFIELD_DISCOVERY = {
    "outcome": "done",
    "headline": "An existing dependency-free Node.js project; `npm test` passes 7 tests on the unchanged checkout.",
    "summary": ("Baseline: `npm test` (`node --test`) on the unchanged checkout exits 0: 7 tests pass "
                "(test/server.test.js 1, test/users.test.js 2, test/paginate.test.js 2, test/strings.test.js 2). "
                "package.json: no dependencies; scripts test=`node --test`, start=`node src/server.js`; engines "
                "node>=20; CommonJS. src/server.js: createServer() on node:http; GET /users answers 200 with "
                "listUsers() as a JSON array; GET /users/:id answers the user or 404 {\"error\": \"not found\"}; any "
                "other path 404; run directly, it listens on Number(process.env.PORT) || 3000. src/users.js: an "
                "in-memory store of three users {id, name, email}; listUsers() in id order; getUser(id). "
                "src/paginate.js: paginate(items, page, size) returns {page, pages, items}, throws RangeError unless "
                "page and size are integers >= 1, and computes pages with Math.floor, so a last partial page is lost. "
                "src/strings.js: capitalize and truncate. Tests use node:test and node:assert/strict and start the "
                "server on port 0. Installed runtime: Node.js 26. Intake's questions the code answers are answered "
                "above; the rest stay with what intake recorded."),
}
BROWNFIELD_RESEARCH = {
    "outcome": "done",
    "headline": "No consequential unknown needed a source beyond the repository read at discovery.",
    "summary": ("Research consulted no external source: the change depends only on the repository's own code, read at "
                "discovery. Open questions and defaults stand as intake and discovery recorded them."),
}

FRAME = """\
ShipLoop navigator | spec (exercise)
You are the host model of ShipLoop, a script-driven software-delivery harness, doing its `spec` stage for the request
below. The run is unattended: no person will answer questions during it. Do only this stage and implement nothing. In
this exercise you have no tools and no files: KNOWLEDGE/spec.md does not exist yet, so write its complete contents in a
fenced ```spec.md block instead of to the file; the earlier stages' results are quoted below by value. {context}
Goal: Define each requirement and its acceptance lines as R-<n> in KNOWLEDGE/spec.md; ShipLoop derives this run's ID
changes from the spec diff.
Done when (confirm each before answering):
- every request outcome maps to at least one acceptance line
- each acceptance line is independently verifiable and says how it will be confirmed
- non-functional requirements are assessed, or excluded with a reason
- unaffected existing requirements are preserved
Checked by: at done ShipLoop refuses a missing primary list, or a primary ID with no current entry in KNOWLEDGE/spec.md;
a change to KNOWLEDGE/ that loses an earlier requirement (R-<n>) or decision (AD-<n>) ID. It does not judge the work:
you confirm each condition.

Current stage guidance:
{duty}

RULES:
- Do only this stage.
- Unattended: take the best default and record it as an assumption; a person-only step is an open item; report
  blocked only when nothing can proceed without a person.

Result template:
```shiploop-state
{{
  "evidence_refs": ["KNOWLEDGE/spec.md"],
  "headline": "<one line for the user: what this step established>",
  "outcome": "done",
  "primary": ["<R-<n> that carries an outcome the user asked for directly>"],
  "summary": "<decisions, defaults, open questions and owners only this result records; no restatement>"
}}
```
Answer with exactly two fenced blocks and nothing else: first ```spec.md holding the complete contents of
KNOWLEDGE/spec.md, then ```shiploop-state holding the filled result (each key once, every placeholder replaced).

Results this stage builds on (quoted by value; report a conflict instead of choosing silently):
----- intake stage result -----
{intake}
----- discovery stage result -----
{discovery}
----- research stage result -----
{research}

Original request (preserve user scope):
----- BEGIN ORIGINAL REQUEST -----
{request}
----- END ORIGINAL REQUEST -----
Sentence index of this request (cite S<n>): {index}
"""


def intake_result(path) -> str:
    text = envelope_text(path)
    result = state_block(text)
    return json.dumps(result, indent=2, ensure_ascii=False) if result is not None else text.strip()


def main() -> None:
    slug = sys.argv[1] if len(sys.argv) > 1 else "terra"
    global ARMS
    ARMS = tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else ("A", "D", "C")
    out = HERE / "spec" / "prompts"
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for case in CASES:
        brownfield = case["id"] == "user-listing"
        discovery = BROWNFIELD_DISCOVERY if brownfield else GREENFIELD_DISCOVERY
        research = BROWNFIELD_RESEARCH if brownfield else GREENFIELD_RESEARCH
        for sample in SAMPLES:
            for arm in ARMS:
                source = intake_out(slug, case["id"], {"C": "C", "B": "B"}.get(arm, "A"), sample)
                duty = DUTY + ("\n" + ITEM13[arm] if ITEM13[arm] else "")
                text = FRAME.format(context=case["context"], duty=duty, intake=intake_result(source),
                                    discovery=json.dumps(discovery, indent=2), research=json.dumps(research, indent=2),
                                    request=" ".join(case["vague"]),
                                    index=" ".join(f"S{i}: {s}" for i, s in enumerate(case["vague"], 1)))
                name = f"{slug}-{case['id']}-{arm}-s{sample}"
                (out / f"{name}.md").write_text(text)
                jobs.append(f"{SUBJECTS[slug]}\tspec/prompts/{name}.md\tspec/{slug}/{case['id']}-{arm}-s{sample}.json")
    suffix = "" if ARMS == ("A", "D", "C") else "-" + "".join(ARMS).lower()
    (HERE / f"jobs-spec-{slug}{suffix}.tsv").write_text("\n".join(jobs) + "\n")
    (HERE / "spec" / "BUILT_FROM.txt").write_text(f"spec duty from main {COMMIT}; duty {len(DUTY)} chars\n")
    print(f"wrote {len(jobs)} spec prompts for {slug} (duty from {COMMIT}, {len(DUTY)} chars)")


if __name__ == "__main__":
    main()
