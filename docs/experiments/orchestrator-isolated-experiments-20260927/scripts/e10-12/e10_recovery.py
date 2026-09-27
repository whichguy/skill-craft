"""E10 add-on: after a drift refusal, does restoring the source (undo the user edit) let return proceed?"""
import e10_return_guard as e
r = e.trial("b_unrelated_tracked", "after-plan", "committed")
repo = e.WORK / r["trial"] / "source"; root = e.WORK / r["trial"] / "workspace"
print("refused:", r["return"][0])
(repo / "other.txt").write_text("other\n")          # user reverts their edit
print("after revert:", e.cli("workspace", "return", "--workspace-root", str(root))[:2])
r = e.trial("c_untracked", "after-plan", "committed")
repo = e.WORK / r["trial"] / "source"; root = e.WORK / r["trial"] / "workspace"
e.git(repo, "add", "user-notes.txt"); e.git(repo, "commit", "-qm", "user commits notes")
res = e.cli("workspace", "return", "--workspace-root", str(root)); print("after user commits:", res[0], res[2].splitlines()[0])
