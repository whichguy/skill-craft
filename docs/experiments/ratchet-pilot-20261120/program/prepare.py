#!/usr/bin/env python3
"""Make the folder and the prompt of one session of the program of journal section 26. No model is called.

    python3 prepare.py question RUN OUT [--text NAME] [--at LABEL]
        the one question to the requester; RUN is a ratchet.py run that wrote a specification, and the folder is its
        work tree as the spec stage left it; --text names another text of this folder (question-three.md,
        spec-reader.md); --at plan-1 takes the specification as the plan stage left it (the plan itself is left out)
    python3 prepare.py revise QUESTION_RUN ANSWER OUT
        the specification after the answer; QUESTION_RUN is the output of the question session; ANSWER is `point`
        (the case's reply in replies.json) or `otherwise` (the requester has no preference)
    python3 prepare.py review ARM CASE PRODUCT OUT [--record RUN]
        a review of a finished change; ARM is `delivery` (start from the delivery's own record) or `request` (start
        from the request and the starting product); PRODUCT is the delivered tree; --record lays the specification,
        plan and acceptance checks of another run over it (a product tree that brings none of its own)

OUT gets `folder/`, what the session's work folder starts as, `prompt.md`, and `made.json`, what both were made from.
A review also gets `tools/starting-product/`, the product before the change: it stands outside the work folder
because the product's own test command (`node --test`) runs every test file under the folder it is started in.
`one_session.py --folder OUT/folder --prompt OUT/prompt.md [--tools OUT/tools] ...` then runs the session. A prompt
names no path of this repository; the answer sheet (replies.json) and every held-out file stay out of both folders.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent
REPO = PILOT.parents[2]
FIXTURES = REPO / "test" / "shiploop_e2e" / "fixtures"
RECORD = ("ratchet/spec.md", "ratchet/plan.md", "ratchet/acceptance.json")  # a delivery's own record, beside acceptance/
SKIP = shutil.ignore_patterns(".git", "node_modules", "tmp")

# The rules every such session works under: ratchet.py's own (CONDUCT), less the two exceptions a stage has (the
# loop's tools and its contract files), which these sessions do not have. A review has one exception of its own.
OUTSIDE = {"none": "Nothing outside it is yours to read for this task or to change.",
           "starting-product": ("Nothing outside it is yours to read for this task or to change, with one exception: "
                                "the folder\n  {tools}/starting-product (read it and run it; leave it as it is).")}
CONDUCT = """## Rules of conduct
- Work only inside this folder: {work}. [[OUTSIDE]]
- Temporary files go under {tmp} (TMPDIR is set to it).
- A server you start listens on a port that is free at that moment (ask the system for port 0, or pick a random high
  port), never a fixed default. Stop every process you started, by its process id. Never stop processes by name
  (no pkill, no killall).
- Install nothing from the network. Do not commit, push or change Git history: the script that runs you commits.
- You run unattended. Where you must choose, choose, and write the choice where this text says."""


def case_of(name):
    cases = json.loads((PILOT / "cases.json").read_text())
    if name not in cases:
        raise SystemExit(f"unknown case {name!r}")
    return cases[name]


def text_of(name, outside="none", **fields):
    text = (HERE / name).read_text()
    for key, value in {**fields, "CONDUCT": CONDUCT.replace("[[OUTSIDE]]", OUTSIDE[outside])}.items():
        marker = f"[[{key}]]"
        if text.count(marker) != 1:
            raise SystemExit(f"{name} does not hold {marker} exactly once")
        text = text.replace(marker, value.strip())
    if "[[" in text:
        raise SystemExit(f"{name} still holds an unfilled field")
    return text


def fresh(out):
    out = Path(out).resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty; give a new folder")
    (out / "folder").mkdir(parents=True)
    return out


def finish(out, prompt, made):
    (out / "prompt.md").write_text(prompt)
    (out / "made.json").write_text(json.dumps(made, indent=1) + "\n")
    print(f"{out.name}: folder of {sum(1 for path in (out / 'folder').rglob('*') if path.is_file())} files, prompt of {len(prompt)} characters")


def question(run, out, text="question.md", at="spec"):
    run, out = Path(run).resolve(), fresh(out)
    record = json.loads((run / "run.json").read_text())
    commit = next(snap["commit"] for snap in record["snapshots"] if snap["label"] == at)
    archive = subprocess.run(["git", "-C", str(run / "work"), "archive", commit], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(out / "folder")], input=archive, check=True)
    for path in (out / "folder" / "ratchet").iterdir():  # the specification alone: no plan and no report of a later stage
        if path.name != "spec.md":
            shutil.rmtree(path) if path.is_dir() else path.unlink()
    finish(out, text_of(text, REQUEST=case_of(record["case"])["request"]),
           {"verb": "question", "text": text, "at": at, "run": str(run), "case": record["case"], "enrich": record.get("enrich"), "spec_commit": commit})


def revise(question_run, answer, out):
    question_run, out = Path(question_run).resolve(), fresh(out)
    record = json.loads((question_run / "run.json").read_text())
    replies = json.loads((HERE / "replies.json").read_text())
    if answer not in ("point", "otherwise"):
        raise SystemExit("ANSWER is `point` or `otherwise`")
    reply = replies[record["case"]]["reply"] if answer == "point" else replies["otherwise"]
    shutil.rmtree(out / "folder")
    shutil.copytree(question_run / "work", out / "folder", symlinks=True, ignore=SKIP)
    asked = (out / "folder" / "ratchet" / "question.md").read_text()
    (out / "folder" / "ratchet" / "question.md").unlink()
    finish(out, text_of("revise.md", REQUEST=case_of(record["case"])["request"], QUESTION=asked, ANSWER=reply),
           {"verb": "revise", "question_run": str(question_run), "case": record["case"], "enrich": record.get("enrich"), "answer": answer})


def review(arm, case, product, out, record_from=None):
    if arm not in ("delivery", "request"):
        raise SystemExit("ARM is `delivery` or `request`")
    product, out = Path(product).resolve(), fresh(out)
    folder = out / "folder"
    shutil.rmtree(folder)
    shutil.copytree(product, folder, symlinks=True, ignore=SKIP)
    source = Path(record_from).resolve() / "work" if record_from else product
    kept = {}
    for name in RECORD:
        if (source / name).is_file():
            kept[name] = (source / name).read_bytes()
    if "ratchet/spec.md" not in kept or "ratchet/acceptance.json" not in kept or not (source / "acceptance").is_dir():
        raise SystemExit(f"{source} holds no specification with acceptance checks")
    checks = out / "acceptance-kept"
    shutil.copytree(source / "acceptance", checks, symlinks=True, ignore=SKIP)
    shutil.rmtree(folder / "ratchet", ignore_errors=True)   # the reports of the delivery's sessions are not part of what is reviewed
    shutil.rmtree(folder / "acceptance", ignore_errors=True)
    shutil.move(str(checks), str(folder / "acceptance"))
    for name, data in kept.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(data)
    shutil.copytree(FIXTURES / case_of(case)["fixture"], out / "tools" / "starting-product", symlinks=True, ignore=SKIP)
    shutil.rmtree(out / "tools" / "starting-product" / "docs" / "shiploop", ignore_errors=True)  # as ratchet.py's setup removes it
    finish(out, text_of(f"review-{arm}.md", outside="starting-product", REQUEST=case_of(case)["request"]),
           {"verb": "review", "arm": arm, "case": case, "product": str(product), "record": str(source)})


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    record_from = None
    if "--record" in argv:
        record_from = argv[argv.index("--record") + 1]
        del argv[argv.index("--record"):argv.index("--record") + 2]
    text = "question.md"
    if "--text" in argv:
        text = argv[argv.index("--text") + 1]
        del argv[argv.index("--text"):argv.index("--text") + 2]
    at = "spec"
    if "--at" in argv:
        at = argv[argv.index("--at") + 1]
        del argv[argv.index("--at"):argv.index("--at") + 2]
    if argv[:1] == ["question"] and len(argv) == 3:
        question(argv[1], argv[2], text, at)
    elif argv[:1] == ["revise"] and len(argv) == 4:
        revise(argv[1], argv[2], argv[3])
    elif argv[:1] == ["review"] and len(argv) == 5:
        review(argv[1], argv[2], argv[3], argv[4], record_from)
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
