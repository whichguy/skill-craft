"""Exp 3: which edits can a one-trivial-pass exit see?  Until Loop Python API, real git workspace."""
import json, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/skills/improve/runtime/until-loop/scripts"))
import until_loop_ephemeral as ul
BASE = Path(__file__).resolve().parent

def git(repo, *a): return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout

def workspace():
    repo = Path(tempfile.mkdtemp(prefix="ul-", dir=BASE)).resolve()
    git(repo, "init", "-q"); git(repo, "config", "user.email", "e@x.invalid"); git(repo, "config", "user.name", "E")
    (repo / "plan.md").write_text("tracked plan v1\n"); (repo / ".gitignore").write_text("scratch/\n")
    (repo / ".shiploop/results").mkdir(parents=True); (repo / ".shiploop/results/spec.md").write_text("spec v1\n")
    (repo / "scratch").mkdir(); (repo / "scratch/draft.md").write_text("draft v1\n")
    git(repo, "add", "plan.md", ".gitignore"); git(repo, "commit", "-qm", "base")
    return repo

TRIVIAL = {"classification": "trivial", "exit_assessment": "satisfied", "continuation_assessment": "allowed",
           "evidence": "Synthetic review found nothing material.", "handoff": "none"}
CTX = {"request": "exp", "scope": "the candidate", "authority": "exp", "environment": "exp", "resources": []}

def trial(label, edit, required=2):
    repo = workspace()
    contract = {"workspace": str(repo), "work": "Review the candidate.", "exit_condition": "Nothing material remains.",
                "repeat_condition": "Repeat while a change remains.", "required_trivial_reviews": required, "context": CTX}
    packet = ul.start(contract, directory=str(repo.parent))
    state = packet["state_file"]; action = packet.get("action") or packet.get("action_id") or packet["callbacks"]
    edit(repo)
    after = ul.done(state, _action(packet), TRIVIAL)
    print(f"## {label}: after one trivial pass -> status={after['status']}"
          + (f", unchanged_first_pass={after.get('progress',{}).get('unchanged_first_pass')}" ))
    return after

def _action(packet):
    for key in ("action", "action_id", "action_token"):
        if key in packet: return packet[key]
    return packet["progress"]["action"] if "action" in packet.get("progress", {}) else json.dumps(packet)[:0]

if __name__ == "__main__":
    p = ul.start({"workspace": str(workspace()), "work": "w", "exit_condition": "e", "repeat_condition": "r", "required_trivial_reviews": 2, "context": CTX}, directory=str(BASE))
    print(json.dumps(p, indent=1)[:1500])
