#!/usr/bin/env python3
"""How the replay's concurrent readers behaved outside the folder they shared.

Reads each reviewer's recorded stream (WORK/replay/out/<case>/<slot>.jsonl) and counts what could let one reader
disturb another although none wrote in the shared case folder: process kills by name pattern, network ports more
than one reader of a case used, "address in use" errors, files written outside the reader's own folder, and
permission errors (the copied tree keeps its read-only mode).

Usage: python3 -I replay_conduct.py WORK
"""
import collections
import json
import pathlib
import re
import sys

KILL = re.compile(r"\b(?:pkill|killall)\b[^;&|\n]*")
PORT = re.compile(r"(?:PORT=|localhost:|127\.0\.0\.1:|listen\()(\d{4,5})\b")


def main(work):
    root = str(work)
    readers = 0
    kills, ports, in_use, denied, shared_tmp = [], collections.defaultdict(set), [], set(), set()
    ran_code = set()
    for stream in sorted((work / "replay" / "out").glob("[cm]*/*.jsonl")):
        case, slot = stream.parent.name, stream.stem
        readers += 1
        for line in stream.read_text(errors="replace").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "assistant":
                for block in (event.get("message") or {}).get("content") or []:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    command = (block.get("input") or {}).get("command") or ""
                    if re.search(r"\b(python3?|node|npm|pytest)\b", command):
                        ran_code.add((case, slot))
                    for found in KILL.findall(command):
                        kills.append((case, slot, found.strip().replace(root, "WORK")))
                    for port in PORT.findall(command):
                        if 1024 <= int(port) <= 65535:
                            ports[(case, port)].add(slot)
                    if re.search(r"(?:>\s*|\bmkdir -p |\bcp [^\n;|&]* )/tmp/", command):
                        shared_tmp.add((case, slot))
                    parent = f"{root}/rv/work/{case}"
                    if re.search(rf"cd {re.escape(parent)}(?:\s|&|;|$)", command) or re.search(r"cp -R \. \.\./m_", command):
                        shared_tmp.add((case, slot))
            elif event.get("type") == "user":
                text = json.dumps(event.get("message"))
                if "EADDRINUSE" in text or "Address already in use" in text:
                    in_use.append((case, slot))
                if "Permission denied" in text or "Operation not permitted" in text:
                    denied.add((case, slot))
    print(f"readers: {readers}; ran the code or its tests: {len(ran_code)}")
    print(f"readers that stopped processes by a name pattern: {len({(c, s) for c, s, _ in kills})}")
    for case, slot, command in kills:
        print(f"  {case} {slot}: {command}")
    shared = {key: sorted(slots) for key, slots in ports.items() if len(slots) > 1}
    print(f"ports used by more than one reader of the same case: {len(shared)}")
    for (case, port), slots in sorted(shared.items()):
        print(f"  {case} port {port}: {', '.join(slots)}")
    print(f"readers whose output shows an address-in-use error: {sorted(set(in_use))}")
    print(f"readers that wrote in /tmp or in the folder above their own: {sorted(shared_tmp)}")
    print(f"readers that hit a permission error (their copy of the tree keeps its read-only mode): {len(denied)}")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]).resolve())
