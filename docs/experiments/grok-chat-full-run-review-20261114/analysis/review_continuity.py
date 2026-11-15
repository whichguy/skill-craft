"""How often an independent review drops a known finding while the flagged code is unchanged.

    python3 -I review_continuity.py RUN_DIR/platform/grok-chat-quality

Each subfolder holds ``request.json`` (``source.files``: the path and sha256 of every file the reviewer was given) and
``review.json`` (``findings``: a ``location`` of ``path:lines; path:lines``, a ``reason`` and ``actionable``).  The reviews
are ordered by ``requested_at``.  For each actionable finding of review N, with review N+1 the next in time:

* ``carried``           N+1 has a finding on the same file with an overlapping line range;
* ``dropped, same code``  N+1 has none, and every file the finding names has the same sha256 in N+1;
* ``dropped, code changed`` N+1 has none, and at least one named file differs.

A drop with the same code is a candidate false negative of N+1.  It is not proof: a later reviewer may rightly judge a
finding wrong, or the fix may sit in a file the location does not name.  This reads records only and runs no model.
"""
import glob
import json
import re
import sys

root = sys.argv[1]
records = []
for req_path in sorted(glob.glob(root + "/*/request.json")):
    folder = req_path.rsplit("/", 1)[0]
    review_path = folder + "/review.json"
    try:
        request = json.load(open(req_path))
        review = json.load(open(review_path))
    except (OSError, ValueError):
        continue
    records.append({
        "at": request["requested_at"],
        "sha": request["source"]["sha256"][:8],
        "files": {f["path"]: f["sha256"] for f in request["source"]["files"]},
        "status": review.get("status"),
        "findings": review.get("findings") or [],
    })
records.sort(key=lambda r: r["at"])


def parse(location):
    """``path:1-5,9-10; other:3`` -> {path: [(lo, hi), ...]} (an empty list when no range parses)."""
    out = {}
    for part in re.split(r";\s*", location or ""):
        part = part.strip()
        if not part:
            continue
        path, _, ranges = part.partition(":")
        spans = []
        for piece in ranges.split(","):
            m = re.fullmatch(r"\s*(\d+)(?:-(\d+))?\s*", piece)
            if m:
                lo = int(m.group(1))
                spans.append((lo, int(m.group(2) or lo)))
        out.setdefault(path.strip(), []).extend(spans)
    return out


def overlaps(a, b):
    for path, spans in a.items():
        other = b.get(path)
        if other is None:
            continue
        if not spans or not other:
            return True
        if any(lo <= hi2 and lo2 <= hi for lo, hi in spans for lo2, hi2 in other):
            return True
    return False


print("reviews in time order: index, requested_at, source, status, findings (actionable)")
for i, r in enumerate(records):
    actionable = sum(1 for f in r["findings"] if f.get("actionable"))
    print("  %2d  %s  %s  %-7s %2d (%d)" % (i + 1, r["at"], r["sha"], r["status"], len(r["findings"]), actionable))

carried = same_code = changed_code = 0
drops = []
pass_over_same = []
for i in range(len(records) - 1):
    a, b = records[i], records[i + 1]
    later = [parse(f.get("location")) for f in b["findings"]]
    same_files_all = []
    for f in a["findings"]:
        if not f.get("actionable"):
            continue
        spans = parse(f.get("location"))
        if any(overlaps(spans, other) for other in later):
            carried += 1
            continue
        unchanged = all(a["files"].get(p) is not None and a["files"].get(p) == b["files"].get(p) for p in spans)
        if unchanged:
            same_code += 1
            same_files_all.append(f)
            drops.append((i + 1, i + 2, f))
        else:
            changed_code += 1
    if a["status"] == "FAIL" and b["status"] == "PASS" and same_files_all:
        pass_over_same.append((i + 1, i + 2, len(same_files_all)))

total = carried + same_code + changed_code
print("\nactionable findings with a next review: %d" % total)
print("  carried to the next review:        %d" % carried)
print("  dropped, flagged code unchanged:   %d" % same_code)
print("  dropped, flagged code changed:     %d" % changed_code)
print("PASS reviews that followed a FAIL with an unchanged flagged file: %d" % len(pass_over_same))
for a, b, n in pass_over_same:
    print("   review %d (FAIL) -> review %d (PASS), %d finding(s) on unchanged files" % (a, b, n))
print("\ndrops with the flagged code unchanged (and what else changed between the two sources):")
for a, b, f in drops:
    before, after = records[a - 1]["files"], records[b - 1]["files"]
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    edited = sorted(p for p in set(before) & set(after) if before[p] != after[p])
    print(("  review %d -> %d  %s\n      %s" % (a, b, f["location"][:150], f.get("reason", "")[:150].replace("\n", " "))).rstrip())
    print("      files added %d, removed %d, edited %d: %s" % (len(added), len(removed), len(edited),
                                                              ", ".join((added + edited)[:5])[:200]))

# A region is a (file, line range) a review flagged.  Follow each across every later review: is the file still the same
# bytes, and is the region flagged again?  "silent while unchanged" is a review that did not flag it although the file
# is byte-identical to the one that was flagged; "resurfaced" means a later review flagged it again after such a gap.
print("\nregions followed across all later reviews (flagged file kept the same bytes):")
threads = []
for i, r in enumerate(records):
    for f in r["findings"]:
        if not f.get("actionable"):
            continue
        for path, spans in parse(f.get("location")).items():
            if not spans:
                continue
            for span in spans:
                threads.append((i, path, span))
seen_keys = set()
resurfaced = silent_only = 0
for i, path, span in threads:
    key = (i, path, span)
    if key in seen_keys:
        continue
    seen_keys.add(key)
    base = records[i]["files"].get(path)
    timeline = []
    for k in range(i + 1, len(records)):
        if records[k]["files"].get(path) != base:
            break
        flagged = any(overlaps({path: [span]}, parse(g.get("location"))) for g in records[k]["findings"] if g.get("actionable"))
        timeline.append((k + 1, flagged, records[k]["status"]))
    silent = [t for t in timeline if not t[1]]
    again = [t for t in timeline if t[1]]
    if silent and again and min(t[0] for t in silent) < max(t[0] for t in again):
        resurfaced += 1
        print("  RESURFACED  %s:%d-%d first flagged in review %d; silent in reviews %s; flagged again in %s" % (
            path.split("/")[-1], span[0], span[1], i + 1, [t[0] for t in silent], [t[0] for t in again]))
    elif silent:
        silent_only += 1
print("regions that were silent while unchanged and then flagged again: %d; silent while unchanged and never flagged again: %d"
      % (resurfaced, silent_only))
