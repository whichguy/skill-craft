"""Per-pass minutes of the five Improve children of the Grok medium battleship run (skill-craft 1.21.0).

A pass's minutes are its review file's mtime minus the previous review file's mtime (the first pass counts from
the child's start.json). Read-only. The run directory is on the owner's machine and is not in this repository, so
passes.out is the record: 26 passes, and the five first passes add up to 13.3 minutes (the share of review work
that would move into authoring if the review were removed is unmeasured).
Run: python3 -B passes.py"""
import os, glob
R="/Users/dadleet/e2e-runs/20261005/v1210-battleship-grok-medium/.shiploop-runs/work-20261005-142606-adb654"
base=R+"/worktree/.shiploop-improve/nav-9f38c55e01ff48efa5d0d52d295891a6"
names={"nav-c8c2cdefb2b94874a95fe6a11c82d8d3":"spec","nav-1a119231eae34739af53a1566ef29039":"test-strategy","nav-26c930b3e5ed409495004476b300e9ec":"plan","nav-b3c1af194da64f6280ff3ae85831e9f0":"step-plan","nav-6e92aebca2194557bcfdb51151fa2133":"test-spec"}
first_passes=[]
for cid,st in names.items():
    d=base+"/"+cid
    t0=os.stat(d+"/start.json").st_mtime
    revs=sorted(glob.glob(d+"/reviews/review-*.md"), key=lambda p:int(p.rsplit("-",1)[1][:-3]))
    prev=t0; out=[]
    for p in revs:
        t=os.stat(p).st_mtime
        out.append(round((t-prev)/60,1)); prev=t
    rc=R+"/run/improve/"+cid+"/receipt.md"
    tend=os.stat(rc).st_mtime
    first_passes.append(out[0])
    print(st, "passes",len(revs),"per-pass(min, from start/previous review mtime)",out,"start->receipt",round((tend-t0)/60,1),"last review->receipt",round((tend-prev)/60,1))
print("first passes of the five children, minutes:", first_passes, "total", round(sum(first_passes),1))
