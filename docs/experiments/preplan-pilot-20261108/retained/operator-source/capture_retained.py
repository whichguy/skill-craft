"""Retain compact reviewable evidence after all registered calls finish.

Full command transcripts stay in the local evidence root. In particular, the
out-of-scope directory-name listing is not copied into the repository.
"""
from pathlib import Path
import hashlib
import json
import shutil

from pair_judge import view

ROOT = Path(__file__).resolve().parent.parent
OP = ROOT / "operator"
SUITE = ROOT / "source/docs/experiments/preplan-pilot-20261108"
DEST = SUITE / "retained"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def copy(source, relative):
    destination = DEST / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return {"source": str(source.relative_to(ROOT)), "retained": relative, "sha256": sha(destination)}


manifest = json.loads((OP / "manifest.json").read_text())
audit = json.loads((OP / "closeout-audit.json").read_text())
results = json.loads((OP / "results.json").read_text())
assert audit["complete"] and audit["pass"], "Complete mechanical audit required; known scope deviations remain explicit."
assert results["status"] == "complete"
assert not DEST.exists(), "Do not overwrite an existing retained capture."
DEST.mkdir()
copied = []
raw = []
for cell in manifest["cells"]:
    name = cell["id"]
    snapshot = view(cell)
    save(DEST / "plans" / (name + ".json"), snapshot)
    # No command transcript is present in this paired decision view.
    copied.append({"source": "pair_judge.view(" + name + ")", "retained": "plans/" + name + ".json", "sha256": sha(DEST / "plans" / (name + ".json"))})
    for filename in ("judge.json", "metadata.json"):
        copied.append(copy(OP / "graded" / name / filename, "individual/" + name + "/" + filename))
    for filename in ("invocation.json", "events.jsonl", "timeline.jsonl", "metrics.json", "slice-result.json", "resources.jsonl"):
        path = Path(cell["out"]) / filename
        if path.exists():
            raw.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path), "bytes": path.stat().st_size})
    for filename in ("bundle.json", "prompt.txt", "judge.events.jsonl"):
        path = OP / "graded" / name / filename
        raw.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path), "bytes": path.stat().st_size})
for case in manifest["registration"]["cases"]:
    for rep in range(1, 3):
        name = f"{case}-{rep}"
        for filename in ("judge.json", "mapping.json"):
            copied.append(copy(OP / "pairs" / name / filename, "paired/" + name + "/" + filename))
        for filename in ("prompt.txt", "judge.events.jsonl"):
            path = OP / "pairs" / name / filename
            raw.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path), "bytes": path.stat().st_size})
for filename in (
    "manifest.json", "results.json", "closeout-audit.json", "scope-audit-findings.json", "scope-disposition.json",
    "grading-protocol.json", "pair-grading-protocol.json", "pair-view-v2.json", "judge-transport-v2.json",
    "launcher-correction-01.json", "quote-decoding-correction.json", "calibration-interpretation.md",
    "method-background.json", "concurrency-context.json", "concurrency-snapshot-02.json", "runtime-identity-note.json",
    "judge-calibration-stdin-v2.json", "sol-plan-review.json", "queue-complete.json",
):
    copied.append(copy(OP / filename, "protocol/" + filename))
copied.append(copy(OP / "preflight-01/completion.json", "protocol/preflight-completion.json"))
copied.append(copy(OP / "final-verification-01/completion.json", "protocol/final-verification.json"))
for filename in ("registration.json", "obligations.json"):
    copied.append(copy(SUITE / filename, "protocol/" + filename))
for filename in (
    "dispatch_pilot.py", "collect.py", "grade.py", "judge_call.py", "pair_judge.py", "analyze.py",
    "scope_audit.py", "closeout_audit.py", "summarize.py", "finish_grading.py", "identity.py", "capture_retained.py",
):
    copied.append(copy(OP / filename, "operator-source/" + filename))
(DEST / "operator-source/README.md").write_text(
    "# Operator source capture\n\nThese are the exact analysis and orchestration scripts used in the retained local evidence root. "
    "They are audit copies, not installed skill code or standalone entry points at this location. Their paths and "
    "imports assume the original `operator/`, `source/`, `arms/` and `runs/` layout recorded in "
    "`../protocol/manifest.json`. Copying them here does not modify that layout or the frozen study. "
    "The original launcher was named queue.py; its byte-identical rename and later judge transport/view "
    "adjustments are recorded under `../protocol/`. No runtime candidate is adopted by this capture.\n"
)
save(DEST / "evidence-index.json", {
    "local_root": str(ROOT),
    "source_freeze": manifest["source_commit"],
    "retained": copied,
    "raw_local_evidence": raw,
    "scope": "Retained decision views omit full command transcripts and duplicate runtime artifacts. Full local evidence remains hashed above. A known out-of-scope name listing is intentionally not published here.",
})
shutil.copyfile(OP / "report-flow.mmd", SUITE / "report-flow.mmd")
shutil.copyfile(OP / "report-flow.svg", SUITE / "report-flow.svg")
print(json.dumps({"destination": str(DEST), "copied": len(copied), "raw_indexed": len(raw), "bytes": sum(p.stat().st_size for p in DEST.rglob('*') if p.is_file())}))
