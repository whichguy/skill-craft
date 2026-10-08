#!/usr/bin/env python3
"""Compact extracts of recorded Claude tool calls, for the hermetic tests of metrics.collect's Claude tool-block reading.

  python3 docs/experiments/claude-tool-blocks-20261008/extract.py [/Users/dadleet/e2e-runs]

Reads, never writes, two recorded round-1 run folders (outside the repository) and writes beside this script the
tool_use blocks the tests need, each with its tool_result, as Claude wrote them to events.jsonl: the assistant and
user events with their message ids, tool_use ids and per-message usage, in the recorded order. What is changed:
the run folder prefix is rewritten (/runs/r1 for Battleship, /runs/r2 for Checkers; the work-directory stamp becomes
work-1, and any other user name becomes `user`), so none is kept; thinking signatures are dropped; a result over 800 characters is cut to its first
300 characters plus every line that begins `ShipLoop ` (a refusal's own line), with the cut marked. manifest.json names
each call, its lines here and its original (uncut, unrewritten) and kept result sizes; verify-records.json holds three
test-loop records of the Battleship run, two of which ran red. The tests
expect the figures of these cut results; the figures of the uncut runs are in the journal.
"""
import json
from pathlib import Path
import re
import sys

RUNS = Path(sys.argv[1] if len(sys.argv) > 1 else "/Users/dadleet/e2e-runs")
HERE = Path(__file__).resolve().parent
CUT_OVER, KEEP_HEAD = 800, 300
USAGE_KEYS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens")

# name -> source event number of the assistant event holding the tool_use block (the result is its tool_use_id's).
BATTLESHIP = {
    "workspace-start": 4,          # variable-form CLI: CLI="$SKILL_ROOT/scripts/shiploop"; python3 "$CLI" workspace start
    "read-packet-whole": 24,       # Read of a packet with no offset or limit
    "refusal-behind-head": 30,     # a refusal behind `| head -30`, exit 0, after a thinking block of the same message
    "write-and-run-sub": 44,       # writes scratch/sub.sh (wraps the CLI) and runs it; its output is a packet head
    "sed-a-packet": 50,            # a shell command on a packet file
    "exit-1-not-shiploop": 78,     # `Exit code 1` from sed of a SKILL.md: a failed command that is not a ShipLoop one
    "write-idone": 102,            # writes scratch/idone.py (does not wrap the CLI by name)
    "write-istart": 133,           # writes scratch/istart.sh (wraps the CLI)
    "read-packet-range-1": 151,    # two Reads of one packet with offset and limit, in one message
    "read-packet-range-2": 153,
    "edit-tool-error": 309,        # an Edit refused by the host: is_error, no `Exit code`
    "run-idone-exit-1": 373,       # `Exit code 1` inside the model's own idone.py: not a ShipLoop failure
    "run-sub-piped": 386,          # sub.sh run behind grep/cut/head; its output is a packet head
    "refusal-knowledge-file": 448, # a direct `shiploop complete` refused behind `| head -12 | cut`, exit 0
    "git-by-the-model": 463,       # git -C $WT add / commit by the model
    "workspace-blocked-plan": 471, # `workspace return` refused after a return plan, exit 0 behind tail
    "workspace-blocked-status": 487,
}
CHECKERS = {
    "assignment-shadowed-by-sh-c": 372,  # R=<run dir> then, inside a quoted sh -c '...', R=$?
}


def rewrite(text: str, folder: str, alias: str) -> str:
    text = text.replace(f"/Users/dadleet/e2e-runs/20261008/{folder}", f"/runs/{alias}")
    text = re.sub(r"\.shiploop-runs/work-\d{8}-\d{6}-[0-9a-f]{6}", ".shiploop-runs/work-1", text)
    return text.replace("dadleet", "user")  # the owner column of an `ls -l`


def cut_result(text: str) -> str:
    if len(text) <= CUT_OVER:
        return text
    kept = [line for line in text[KEEP_HEAD:].splitlines() if line.startswith("ShipLoop ")]
    return text[:KEEP_HEAD] + f"\n[... {len(text) - KEEP_HEAD} chars cut]\n" + "".join(line + "\n" for line in kept)


def result_text(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, list):
        content = "".join(str(part.get("text") or "") for part in content if isinstance(part, dict))
    return str(content or "")


def assistant_event(event: dict, folder: str, alias: str) -> dict:
    message = event["message"]
    content = []
    for block in message["content"]:
        if block.get("type") == "thinking":
            block = {"type": "thinking", "thinking": block.get("thinking") or ""}
        elif block.get("type") == "tool_use":
            block = json.loads(rewrite(json.dumps(block), folder, alias))
        content.append(block)
    usage = {k: message["usage"][k] for k in USAGE_KEYS if k in (message.get("usage") or {})}
    return {"type": "assistant", "message": {"id": message["id"], "role": "assistant", "content": content, "usage": usage}}


def extract(folder: str, alias: str, wanted: dict[str, int]) -> tuple[list[dict], dict]:
    events = [json.loads(line) for line in (RUNS / "20261008" / folder / "events.jsonl").open()]
    results = {}  # tool_use id -> (event number, block)
    for number, event in enumerate(events):
        if event.get("type") == "user":
            for block in event["message"]["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    results[block["tool_use_id"]] = (number, block)
    picked = []  # (event number, event) in recorded order
    manifest = {}
    for name, number in sorted(wanted.items(), key=lambda item: item[1]):
        use = next(b for b in events[number]["message"]["content"] if b.get("type") == "tool_use")
        lines = []
        # A thinking block of the same message is its own event: keep it, so a message is one call however many events.
        before = events[number - 1]
        if before.get("type") == "assistant" and before["message"]["id"] == events[number]["message"]["id"]:
            lines.append(number - 1)
        lines.append(number)
        result_number, block = results[use["id"]]
        lines.append(result_number)
        original = result_text(block)
        kept = cut_result(rewrite(original, folder, alias))
        for line in lines[:-1]:
            if not any(n == line for n, _ in picked):
                picked.append((line, assistant_event(events[line], folder, alias)))
        user = {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": use["id"], "content": kept,
             **({"is_error": block["is_error"]} if "is_error" in block else {})}]}}
        picked.append((result_number, user))
        manifest[name] = {"run": folder, "source_events": lines, "tool_use": use["name"], "tool_use_id": use["id"],
                          "original_result_chars": len(original), "kept_result_chars": len(kept)}
    picked.sort(key=lambda item: item[0])
    index = {number: place for place, (number, _) in enumerate(picked)}
    for entry in manifest.values():
        entry["lines"] = [index[n] for n in entry.pop("source_events")]
    text = "".join(json.dumps(event, ensure_ascii=False) + "\n" for _, event in picked)
    assert "dadleet" not in text, [m.group(0) for m in re.finditer(r".{60}dadleet.{40}", text)][:5]
    return [event for _, event in picked], manifest, text


# The three test-loop records of r1 Battleship the verification tests read: the test-red record (`expect: red`, both commands
# ran red and the record passed), the test-author probe (`expect: a test ran`, which accepts red or passed, and ran red), and a
# green system-test record. Stdout and stderr are cut to 200 characters, the working directory and time are dropped.
VERIFY = {"test-red": "nav-70f6c0cd", "test-author": "nav-dfe0a994", "system-test": "nav-8c62dc57"}


def verify_records() -> dict:
    tests = next((RUNS / "20261008" / "r1-battleship-sonnet" / ".shiploop-runs").glob("*/run")) / "tests"
    found = {}
    for number, (stage, prefix) in enumerate(VERIFY.items(), 1):
        path = next(tests.glob(f"{prefix}*-verify1.md"))
        record = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", path.read_text(), re.S).group(1))
        runs = [{k: (rewrite_text(v)[:200] if k in ("stdout", "stderr") else v) for k, v in run.items()}
                for run in record["runs"]]
        found[stage] = {**{k: v for k, v in record.items() if k not in ("cwd", "created_at", "runs")},
                        "action": f"a{number}", "runs": runs}
    return found


def rewrite_text(text: str) -> str:
    return rewrite(text, "r1-battleship-sonnet", "r1")


def main() -> None:
    manifest = {}
    for file, folder, alias, wanted in (("battleship-sonnet-calls.jsonl", "r1-battleship-sonnet", "r1", BATTLESHIP),
                                         ("checkers-sonnet-calls.jsonl", "r1-checkers-sonnet", "r2", CHECKERS)):
        _, found, text = extract(folder, alias, wanted)
        (HERE / file).write_text(text)
        manifest[file] = found
        print(file, len(text), "bytes")
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    (HERE / "verify-records.json").write_text(json.dumps(verify_records(), indent=1) + "\n")


if __name__ == "__main__":
    main()
