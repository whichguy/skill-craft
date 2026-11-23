#!/usr/bin/env python3
"""For one E2E delivery folder: every commit of the product repository that touches docs/shiploop/spec.md, in order, with its
subject, and whether it came before or after the carry-forward knowledge commit. Read-only (log, show, diff)."""
import os, re, subprocess, sys
os.environ["GIT_OPTIONAL_LOCKS"] = "0"
def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout
def main(folder):
    repo = os.path.join(folder, "work")
    commits = git(repo, "log", "--reverse", "--format=%H%x1f%s", "--all", "--", "docs/shiploop/spec.md").strip().splitlines()
    cf = git(repo, "log", "--all", "--format=%H", "--grep=after carry-forward", "--", "docs/shiploop").split()
    print("run:", folder)
    print("  carry-forward knowledge commits:", len(cf))
    order = {h: i for i, h in enumerate(git(repo, "rev-list", "--reverse", "--all").split())}
    for h in cf:
        files = git(repo, "show", "--stat", "--format=", h).strip().splitlines()
        print("   ", h[:10], "changed:", "; ".join(f.strip() for f in files))
        spec = git(repo, "show", "--format=", h, "--", "docs/shiploop/spec.md")
        if spec.strip():
            print("    !! spec.md changed by this carry-forward commit:")
            print(spec)
    for line in commits:
        h, s = line.split("\x1f")
        tag = ""
        if cf:
            tag = "after the carry-forward commit" if order.get(h, -1) > order.get(cf[0], 10**9) else "before it"
        print("  spec.md commit", h[:10], tag, "|", s[:110])
if __name__ == "__main__":
    for a in sys.argv[1:]:
        main(a)
