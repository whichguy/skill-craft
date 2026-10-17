"""Per-packet line diff of two dump directories (from dump_packets.py): ids, request tags and temp dirs are normalised, so
only real changes show.  usage: packet_diff.py BEFORE AFTER [--show]: per packet, the lines removed and added (the obligation
check: each removed line must be a same-packet duplicate or a symbol substitution).  Sizes here are of the normalised text
(short temp paths); packet_sizes.py gives the real ones.

--only KIND (full or printed): compare only that kind; a printed head switches to the whole packet when a change brings it under
the print limit, which is a change of print mode, not of content.

--expand: before comparing, write every symbol back as its absolute path in both texts (HOME/, RUN/, GUIDES/ followed by a path,
and a bare WORKTREE, from the definitions in the packet's own References block; the definition lines stay).  What is left in
the diff is then what is not a symbol substitution."""
import sys, re, difflib
from pathlib import Path
before, after = Path(sys.argv[1]), Path(sys.argv[2]); show = "--show" in sys.argv; expand = "--expand" in sys.argv

def expanded(text):
    """``text`` with the symbols its References block defines written as their absolute paths."""
    defs = dict(re.findall(r"(HOME|RUN|WORKTREE|GUIDES) = (\S+)", text))
    if not defs:
        return text
    out = []
    for line in text.split("\n"):
        if not re.match(r"(HOME|WORKTREE) = ", line):
            line = re.sub(r"\b(HOME|RUN|GUIDES)/(?=[\w.@+~-])", lambda m: defs[m.group(1)] + "/" if m.group(1) in defs else m.group(0), line)
            if "WORKTREE" in defs:
                line = re.sub(r"\bWORKTREE\b", defs["WORKTREE"], line)
        out.append(line)
    return "\n".join(out)

def norm_factory():
    ids = {}
    def norm(text):
        text = re.sub(r"shiploop-step-packets-\w+", "TMP", text)
        text = re.sub(r"(?<=ORIGINAL REQUEST )[0-9a-f]+", "TAG", text)
        text = re.sub(r"(?<=carrying tag )[0-9a-f]+", "TAG", text)
        def sub(m):
            return ids.setdefault(m.group(0), f"nav-ID{len(ids):03d}")
        return re.sub(r"nav-[0-9a-f]{32}", sub, text)
    return norm

tot_b = tot_a = 0
only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else ""   # --only full: compare the whole renders only
for kind in [k for k in ("inline/full", "inline/printed", "ask-agent/full", "ask-agent/printed") if only in k]:
    nb, na = norm_factory(), norm_factory()
    print(f"=== {kind}")
    for f in sorted((before / kind).glob("*.txt")):
        b, a = f.read_text(), (after / kind / f.name).read_text()
        if expand:
            b, a = expanded(b), expanded(a)
        b, a = nb(b), na(a)
        tot_b += len(b); tot_a += len(a)
        bl, al = b.splitlines(), a.splitlines()
        rem, add = [], []
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, bl, al, autojunk=False).get_opcodes():
            if tag in ("replace", "delete"): rem += bl[i1:i2]
            if tag in ("replace", "insert"): add += al[j1:j2]
        print(f"{f.stem:28s} {len(b):6d} -> {len(a):6d} ({len(a)-len(b):+d})  removed {len(rem)} lines, added {len(add)} lines")
        if show:
            for l in rem: print("   - " + (l[:230] + ("…" if len(l) > 230 else "")))
            for l in add: print("   + " + (l[:230] + ("…" if len(l) > 230 else "")))
print("TOTAL", tot_b, "->", tot_a, f"({tot_a-tot_b:+d})")
