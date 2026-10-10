"""The `packets` and `commits` blocks of metrics.json (SPEC, "How the harness checks the clauses", 2026-10-10).

Two records, built the way fidelity.py's block is (once, in run.py's main, so a regrade adds them too), changing no verdict, exit code
or baseline row. Absent means unknown: a part this module cannot read is null with its reason in a sibling ``*_unmeasured`` map, never
0 and never a pass; an empty list or a zero is a measured none.

``packets``    one entry per file in the run's ``packets/`` folder, ``{action, stage, file_bytes, head_bytes}``.
               ``action`` is the file's name without ``.md`` (the second packet a bound Improve child gets for one action is its
               own file, ``<action>-improve``, so the key is unique), ``stage`` the stage of the file's ``ShipLoop navigator |``
               line (first in some files, below a delegation preamble in others), ``file_bytes`` the size on disk (a recovery
               ``next`` rewrites the file, so it is the last write), and ``head_bytes`` the bytes of the head ShipLoop first printed
               for the packet, as the host recorded the reply. One reader for every host (``metrics.ToolLog.replies``): Claude's
               ``tool_result`` block, Grok's final ``output_for_prompt`` (after its ``exit: N`` line) and Codex's after the harness
               translator. The head is whole when it runs from its ``ShipLoop navigator |`` line to its own closing line (the
               status block's, or the narrative block's when one follows), its ``Full packet:`` line names the file, and its
               callback and keepalive lines are not shortened; whatever the reply holds before it (a command's own output, Grok's
               exit line) or after it (the host's ``Shell cwd was reset`` note, output the model chained) is not the head. A reply
               the model cut (``| head``, ``sed -n``, a script of its own), a head printed as a pointer and a prefix (a long packet in
               a state that prints whole), a call that names a packet file (the model reading it) and a packet no reply shows
               leave ``head_bytes`` null. Saved Claude runs are cut in most replies, so most of their heads are null.
``commits``    not built in this file yet.
"""

from __future__ import annotations

import re
from pathlib import Path

import runrecord

# ShipLoop's own words, pinned to its source by test/shiploop-e2e-commit-counters.test.py (a reworded line fails there, and does not
# silently turn every head into null).
HEAD_START = re.compile(r"^ShipLoop navigator \| (?P<stage>[\w-]+) \|", re.M)
HEADER = re.compile(r"^ShipLoop navigator \| (?P<stage>[\w-]+) \| revision (?P<revision>\d+)", re.M)
FULL_PACKET = re.compile(r"^Full packet: (?P<path>\S[^\n]*\.md)$", re.M)
STATUS_BEGIN = "=== ShipLoop status ==="
STATUS_END = "=== end ShipLoop status ==="
NARRATIVE_BEGIN = "=== ShipLoop narrative ==="
NARRATIVE_END = "=== end ShipLoop narrative ==="
# The host's own note on the end of a Claude Bash reply; the replies of the other hosts have none. The newline before it is kept:
# ShipLoop's head ends with one, and a host that trims a reply's last newline leaves the count one byte short.
HOST_NOTE = re.compile(r"Shell cwd was reset to [^\n]*\Z")
# A line the head prints whole, which a cut by column shortens: its end is how the cut is told.
CALLBACK_LINE = re.compile(r"^Callback for this stage[^\n]*$", re.M)
KEEPALIVE_LINE = re.compile(r"^Keepalive marker:[^\n]*$", re.M)

HEAD_BYTES_WHY = ("a reply is a whole print only from its head's first line to the head's own closing line, with the packet's "
                  "`Full packet:` line and unshortened callback and keepalive lines; no recorded reply is one for these packets "
                  "({cut} recorded head replies were cut by the model's own pipe or script or by the host, and the rest of the "
                  "packets are shown by no reply)")


def _whole_head(reply: str) -> str | None:
    """The head at the start of ``reply`` (which starts at its ``ShipLoop navigator |`` line) up to its closing line, or None
    when the reply stops before it: the status block's end, then the narrative block when one follows it."""
    end = reply.find(STATUS_END)
    if end < 0:
        return None
    cut = end + len(STATUS_END)
    if re.match(r"\n*" + re.escape(NARRATIVE_BEGIN), reply[cut:]):
        close = reply.find(NARRATIVE_END, cut)
        if close < 0:
            return None
        cut = close + len(NARRATIVE_END)
    if reply[cut:cut + 1] == "\n":
        cut += 1
    head = reply[:cut]
    # A cut by column keeps every line and shortens the long ones: the callback line must still end with its result path and the
    # keepalive line with the run directory, as ShipLoop prints them.
    if any(not line.rstrip().endswith(".md") for line in CALLBACK_LINE.findall(head)):
        return None
    if any(not re.search(r"\bdir=\S+$", line.rstrip()) for line in KEEPALIVE_LINE.findall(head)):
        return None
    return head


def _heads(reply: str):
    """Each head in a reply as (text from its first line to the next head's first line or the end of the reply)."""
    reply = HOST_NOTE.sub("", reply)
    starts = [match.start() for match in HEAD_START.finditer(reply)]
    for index, start in enumerate(starts):
        yield reply[start:starts[index + 1] if index + 1 < len(starts) else len(reply)]


def _packet_file(path: Path) -> tuple[str | None, int]:
    """(stage, revision) of the first navigator line of a packet file, or (None, a large number) when it has none."""
    try:
        found = HEADER.search(path.read_text(errors="replace"))
    except OSError:
        found = None
    return (found.group("stage"), int(found.group("revision"))) if found else (None, 10 ** 9)


def packets(out: Path, run_dir: Path | None, tools) -> tuple[list[dict] | None, dict]:
    """(the ``packets`` block, the ``packets_unmeasured`` map): see the module docstring. ``tools`` is the ToolLog the run's events
    filled."""
    folder = Path(run_dir) / "packets" if run_dir else None
    if run_dir is None:
        return None, {"packets": "the output folder holds no ShipLoop run directory, so there is no packets folder to read"}
    if not folder.is_dir():
        return None, {"packets": "the run directory has no packets folder"}
    files = {path.stem: path for path in folder.glob("*.md") if path.is_file()}
    printed: dict[str, int] = {}
    cut = 0
    for reply in tools.replies:
        if reply["packet"]:
            continue
        for text in _heads(reply["text"]):
            head = _whole_head(text)
            found = FULL_PACKET.search(head) if head else None
            stem = Path(found.group("path")).stem if found else None
            if head is None:
                cut += 1
            elif stem in files:
                printed.setdefault(stem, len(head.encode("utf-8")))
    rows = []
    for stem, path in files.items():
        stage, revision = _packet_file(path)
        rows.append((revision, stem, {"action": stem, "stage": stage, "file_bytes": path.stat().st_size,
                                      "head_bytes": printed.get(stem)}))
    block = [row for _revision, _stem, row in sorted(rows, key=lambda item: item[:2])]
    missing = sum(row["head_bytes"] is None for row in block)
    if not missing:
        return block, {}
    hosts = ", ".join(runrecord.hosts_used(out)) or "host not recorded"
    return block, {"head_bytes": f"{hosts}: {missing} of {len(block)} packets have no whole print in the recorded replies: "
                                 + HEAD_BYTES_WHY.format(cut=cut)}


def commits(out, tools):
    return None, {"commits": "the commits block is not built yet"}


def build(out, run_dir, tools):
    block, why = packets(out, run_dir, tools)
    cblock, cwhy = commits(out, tools)
    return {"packets": block, "packets_unmeasured": why, "commits": cblock, "commits_unmeasured": cwhy}
