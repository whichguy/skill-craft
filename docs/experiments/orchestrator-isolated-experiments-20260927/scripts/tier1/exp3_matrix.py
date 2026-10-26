"""X4 matrix (adapted from exp3_onepass.py helpers): which edits can the one-trivial-pass exit see?
Change vs original: action token read from done_argv's --action= (the packet has no `action` key); matrix run here."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exp3_onepass as e

def action_of(packet):
    return next(a.split("=", 1)[1] for a in packet["done_argv"] if a.startswith("--action="))

def trial(label, edit, required=2):
    repo = e.workspace()
    contract = {"workspace": str(repo), "work": "Review the candidate.", "exit_condition": "Nothing material remains.",
                "repeat_condition": "Repeat while a change remains.", "required_trivial_reviews": required, "context": e.CTX}
    packet = e.ul.start(contract, directory=str(repo.parent))
    edit(repo)
    after = e.ul.done(packet["state_file"], action_of(packet), e.TRIVIAL)
    print(f"{label:28s} status={after['status']:8s} unchanged_first_pass={after['progress'].get('unchanged_first_pass')}")

outside = e.BASE / "outside.txt"
trial("control: no edit", lambda r: None)
trial("tracked edit", lambda r: (r / "plan.md").write_text("tracked plan v2\n"))
trial("new untracked file", lambda r: (r / "new.md").write_text("new\n"))
trial("ignored file (scratch/)", lambda r: (r / "scratch/draft.md").write_text("draft v2\n"))
trial(".shiploop/ file", lambda r: (r / ".shiploop/results/spec.md").write_text("spec v2 REWRITTEN\n"))
trial("outside workspace", lambda r: outside.write_text("changed\n"))
