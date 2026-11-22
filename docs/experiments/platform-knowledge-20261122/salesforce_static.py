"""Static counts on saved deliveries of a Salesforce project: do the delivered files follow a few of the platform card's rules?

Reads each run's product checkout (<run>/work) and its events.jsonl; calls no model and changes nothing. The checks
C1 to C8 are described in docs/platform-knowledge-journal.md section 8. C6 counts lines, not commands.

usage: salesforce_static.py RUNS.txt      (one absolute run folder a line)
"""

import glob
import os
import re
import sys
from pathlib import Path

EXC = {"node_modules", ".git", ".sf", ".sfdx", ".shiploop-runs"}


CARD_TAIL = "skills/shiploop/references/platforms/salesforce.md"


def home_card(r):
    """The run's copy of the platform card under <run>/home, hidden folders (.codex, .grok) included.

    The original picked the first hit of `find <run>/home -path '*skills/shiploop/references/platforms/salesforce.md'`,
    which is the file system's own listing order and differs between runs. Here: the smallest path in sort order, or ''
    if there is none. On the nine saved runs every copy of the card inside one run is byte-identical, so the choice
    does not change the C8 column.
    """
    found = []
    for dp, _dn, fn in os.walk(r + "/home"):
        found.extend(os.path.join(dp, f) for f in fn if f == "salesforce.md")
    return min((p for p in found if p.endswith(CARD_TAIL)), default="")


def walk(root):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in EXC]
        for f in fn:
            yield os.path.join(dp, f)


def rd(p):
    try:
        return Path(p).read_text(errors="replace")
    except OSError:
        return ""


SHARE = re.compile(r"\b(with|without|inherited)\s+sharing\b", re.IGNORECASE)
CLASSDECL = re.compile(r"^[^\n/*]*\bclass\b", re.IGNORECASE | re.MULTILINE)
QUERY = re.compile(r"\[\s*SELECT|Database\.query", re.IGNORECASE)
DML = re.compile(
    r"^\s*(insert|update|delete|upsert)\b|Database\.(insert|update|delete|upsert)",
    re.IGNORECASE | re.MULTILINE,
)
ENF = [
    "WITH USER_MODE",
    "WITH SECURITY_ENFORCED",
    "AccessLevel.USER_MODE",
    "as user",
    "Security.stripInaccessible",
    "isAccessible()",
    "isCreateable()",
    "isUpdateable()",
    "isDeletable()",
]
PHR = [
    "lightning__Tab",
    ".sfdx",
    "result-format tap",
    "PermissionSetTabSetting",
    "with sharing",
    "bulk",
]


def cls_has_sharing(t):
    # sharing keyword in a class declaration line (strip comments crudely)
    t2 = re.sub(r"/\*.*?\*/", "", t, flags=re.DOTALL)
    t2 = re.sub(r"//[^\n]*", "", t2)
    for m in re.finditer(r"^[^\n]*\bclass\b[^\n]*", t2, re.MULTILINE | re.IGNORECASE):
        if SHARE.search(m.group(0)):
            return True
    return False


def run(r):
    w = r + "/work"
    files = list(walk(w))
    out = {}
    gi = w + "/.gitignore"
    if not os.path.exists(gi):
        out["C1"] = "no .gitignore"
    else:
        lines = [l.strip() for l in rd(gi).splitlines()]
        sf = any(l in (".sf", ".sf/", "/.sf", "/.sf/") for l in lines)
        sfdx = any(l in (".sfdx", ".sfdx/", "/.sfdx", "/.sfdx/") for l in lines)
        out["C1"] = (
            "both"
            if sf and sfdx
            else ("one(%s)" % (".sf" if sf else ".sfdx") if sf or sfdx else "none")
        )
    lwcmeta = [f for f in files if f.endswith(".js-meta.xml") and "/lwc/" in f]
    tabcmp = [f for f in lwcmeta if "lightning__Tab" in rd(f)]
    tabs = [f for f in files if f.endswith(".tab-meta.xml")]
    lw = [t for t in tabs if "<lwcComponent>" in rd(t)]
    out["C2"] = f"{len(tabcmp)} / {len(tabs)} / lwcComponent in {len(lw)}"
    ps = [f for f in files if f.endswith(".permissionset-meta.xml")]
    apps = [f for f in files if f.endswith(".app-meta.xml")]
    out["C3"] = (
        f"{len(ps)} / tabSettings {sum('<tabSettings>' in rd(f) for f in ps)} / classAccesses {sum('<classAccesses>' in rd(f) for f in ps)} / app {len(apps)}"
    )
    cls = [f for f in files if f.endswith(".cls")]
    test = [f for f in cls if re.search("@isTest", rd(f), re.IGNORECASE)]
    non = [f for f in cls if f not in test]
    sh = [f for f in non if cls_has_sharing(rd(f))]
    out["C4"] = f"{len(non)} / {len(sh)}"
    cand = [f for f in non if QUERY.search(rd(f)) or DML.search(rd(f))]
    enf = [f for f in cand if any(e.lower() in rd(f).lower() for e in ENF)]
    out["C5"] = f"{len(enf)} of {len(cand)}"
    ev = r + "/events.jsonl"
    n = t = 0
    if os.path.exists(ev):
        with open(ev, errors="replace") as fh:
            for l in fh:
                if "sf apex run test" in l:
                    n += 1
                    if "--result-format tap" in l:
                        t += 1
    out["C6"] = f"{n} / tap {t}"
    out["C7"] = str(len(test))
    card = glob.glob(
        r + "/build/plugins/*/skills/shiploop/references/platforms/salesforce.md"
    )
    if card:
        c = card[0]
    else:
        c = home_card(r)
    txt = rd(c) if c else ""
    out["C8"] = " ".join(("Y" if p in txt else "n") for p in PHR) if c else "no card"
    out["_card"] = c
    out["_extra"] = f"nonTestCls={[os.path.relpath(f, w) for f in non][:0]}"
    return out


print(
    "run\tC1\tC2(tabcmp/tabfiles/lwcComp)\tC3(ps/tabSet/classAcc/app)\tC4(nontest/sharing)\tC5\tC6(lines/tap)\tC7\tC8(lightning__Tab,.sfdx,tap,PSTabSetting,with sharing,bulk)"
)
for r in Path(sys.argv[1]).read_text().split():
    o = run(r)
    print(
        os.path.basename(r)
        + "\t"
        + "\t".join(o[k] for k in ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"])
    )
    print("   card:", o["_card"], file=sys.stderr)
