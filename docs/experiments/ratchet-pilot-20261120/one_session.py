#!/usr/bin/env python3
"""One model session in a prepared folder, outside the Ratchet stages.

The program of journal section 26 has sessions that are no stage of the loop: a question put to the requester, a
specification revised after the answer, a fresh review of a finished product. Each is one session in a folder made
ready beforehand (program/prepare.py), run by this script the way ratchet.py runs a stage: a home of its own, the
folder a Git repository of its own, and every change outside what the session may write put back.

    python3 one_session.py --folder FOLDER --prompt FILE --allow PATH [--allow PATH ...] --output DIR
                           --host {codex,claude,grok,fake} [--model M] [--effort E] [--session-seconds N]
                           [--tools FOLDER] [--case NAME --enrich NAME --role ROLE] [--fake-write PATH=TEXT ...]

FOLDER is copied to DIR/work and committed there (`given`). With --tools, that folder is copied to DIR/tools: what a
session may read outside its work folder, and nothing it may change (a change there is not undone, only recorded). The prompt is the text of FILE with the three fields
`{work}`, `{tmp}` and `{tools}` filled in; no other brace is touched. A --allow rule is a path, or a folder ending
in `/`. After the session, every changed path no rule covers is put back, and what remains is committed (`session`).

DIR/run.json has the form ratchet.py reads from an earlier run (case, enrich, sessions with role and seconds), so a
folder whose session wrote `ratchet/spec.md` can be given to `ratchet.py run --spec-from DIR`. It also records the
paths changed and put back, and any mark of held-out material in the session's events. --host fake calls no model:
it writes each --fake-write file and is for testing this script.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ratchet


def fill(text, fields):
    """`{work}`, `{tmp}` and `{tools}` replaced; every other brace left as written (a prompt may quote JSON)."""
    return re.sub(r"\{(work|tmp|tools)\}", lambda found: str(fields[found.group(1)]), text)


def covered(name, rules):
    return any(name == rule or (rule.endswith("/") and name.startswith(rule)) for rule in rules)


def changed(work):
    names = set(ratchet.git(work, "diff", "--name-only", "HEAD", "--").splitlines())
    names |= set(ratchet.git(work, "ls-files", "--others", "--exclude-standard").splitlines())
    return sorted(name for name in names if name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--folder", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--allow", action="append", default=[])
    parser.add_argument("--output", required=True)
    parser.add_argument("--host", required=True, choices=("codex", "claude", "grok", "fake"))
    parser.add_argument("--model")
    parser.add_argument("--effort")
    parser.add_argument("--session-seconds", type=int, default=ratchet.SESSION_SECONDS)
    parser.add_argument("--case", default=None)
    parser.add_argument("--enrich", default=None)
    parser.add_argument("--role", default="session")
    parser.add_argument("--tools")
    parser.add_argument("--fake-write", action="append", default=[])
    args = parser.parse_args(argv)

    out = Path(args.output).resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty; give a new output folder")
    work, tmp, tools, session = out / "work", out / "tmp", out / "tools", out / "session"
    for folder in (tmp, session):
        folder.mkdir(parents=True, exist_ok=True)
    if args.tools:
        shutil.copytree(args.tools, tools, symlinks=True, ignore=shutil.ignore_patterns(".git", "node_modules"))
    else:
        tools.mkdir()
    listing = sorted(str(path.relative_to(tools)) + f":{path.stat().st_size}" for path in tools.rglob("*") if path.is_file())
    shutil.copytree(args.folder, work, symlinks=True, ignore=shutil.ignore_patterns(".git", "node_modules"))
    ratchet.git(work, "init", "-q", "-b", "main")
    ratchet.git(work, "config", "user.name", "Ratchet pilot")
    ratchet.git(work, "config", "user.email", "ratchet-pilot@example.invalid")
    ratchet.git(work, "add", "-A")
    ratchet.git(work, "commit", "-q", "--allow-empty", "-m", "given")
    prompt = fill(Path(args.prompt).read_text(), {"work": work, "tmp": tmp, "tools": tools})
    (session / "prompt.txt").write_text(prompt)

    record = {"case": args.case, "enrich": args.enrich, "host": args.host, "model": args.model, "effort": args.effort,
              "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "folder": str(Path(args.folder).resolve()),
              "prompt_file": str(Path(args.prompt).resolve()), "allow": args.allow,
              "local_head": ratchet.git(ratchet.REPO, "rev-parse", "HEAD").strip(), "sessions": []}
    began = time.time()
    if args.host == "fake":
        for pair in args.fake_write:
            name, _, text = pair.partition("=")
            (work / name).parent.mkdir(parents=True, exist_ok=True)
            (work / name).write_text(text)
        status = {"status": "exited", "returncode": 0}
    else:
        sys.path.insert(0, str(ratchet.E2E))
        import hosts  # the E2E harness's host launcher
        host = hosts.host(args.host)
        host.model = args.model or host.model
        record["model"], record["effort"] = host.model, args.effort or host.effort
        env = dict(host.env(out / "home"), TMPDIR=str(tmp))
        argv_, payload = host.prepare(prompt=prompt, prompt_file=session / "host-prompt.txt", cwd=work, model=record["model"],
                                      effort=record["effort"], permission_mode="auto", max_turns=None, max_budget_usd=None,
                                      plugin_dir=None)
        status = hosts.run_agent(argv_, work, env, session / "events.jsonl", session / "stderr.txt", args.session_seconds,
                                 translate=host.translator(), stdin_payload=payload)
    row = {"number": 1, "role": args.role, "label": args.role, "seconds": round(time.time() - began, 1), **status}
    events = session / "events.jsonl"
    if events.exists():
        text = events.read_text(errors="replace")
        row["held_out_marks"] = sorted(mark for mark in ratchet.HELD_OUT_MARKS if mark in text)
    names = changed(work)
    back = [name for name in names if not covered(name, args.allow)]
    for name in back:
        had = subprocess.run(["git", "-C", str(work), "cat-file", "-e", f"HEAD:{name}"], capture_output=True, check=False)
        if had.returncode == 0:
            ratchet.git(work, "checkout", "-q", "HEAD", "--", name)
        else:
            (work / name).unlink(missing_ok=True)
    ratchet.git(work, "add", "-A")
    ratchet.git(work, "commit", "-q", "--allow-empty", "-m", "session")
    record["sessions"].append(row)
    record["changed"], record["put_back"] = [name for name in names if name not in back], back
    after = sorted(str(path.relative_to(tools)) + f":{path.stat().st_size}" for path in tools.rglob("*") if path.is_file())
    record["tools_changed"] = sorted(set(listing) ^ set(after))  # a file added, removed or of another size under DIR/tools
    record["snapshots"] = [{"label": "session", "commit": ratchet.git(work, "rev-parse", "HEAD").strip()}]
    (out / "run.json").write_text(json.dumps(record, indent=1) + "\n")
    print(f"[{time.strftime('%H:%M:%S')}] {args.role}: ended {row['status']} after {row['seconds']} s; changed "
          f"{', '.join(record['changed']) or 'nothing'}" + (f"; put back {', '.join(back)}" if back else ""), flush=True)
    return 0 if row["status"] == "exited" and row.get("returncode") == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
