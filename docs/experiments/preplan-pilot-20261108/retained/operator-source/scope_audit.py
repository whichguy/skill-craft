"""Uniform supplemental audit of retained command outputs, without printing names."""
from pathlib import Path
import json

OP = Path(__file__).resolve().parent
findings = []
checked = []
manifest = json.loads((OP / "manifest.json").read_text())
for cell in manifest["cells"]:
    path = Path(cell["out"]) / "events.jsonl"
    if not path.exists() or not (OP / (cell["id"] + "-complete.json")).exists():
        continue
    checked.append(cell["id"])
    for number, line in enumerate(path.read_text().splitlines(), 1):
        event = json.loads(line)
        raw = event.get("rawOutput") or {}
        if not isinstance(raw, dict):
            continue
        output = str(raw.get("output_for_prompt", ""))
        if output.count("?? ../") >= 3:
            findings.append({
                "sample": cell["id"],
                "event": number,
                "command": raw.get("command"),
                "type": "ancestor-repository-status-path-enumeration",
                "upward_path_entries": output.count("?? ../"),
                "evidence": "Retained bundle application_tool_evidence; output contains unrelated ancestor-directory path names. No file-content read is established by this command.",
            })
record = {
    "method": "Uniform scan of every completed measured run's normalized tool outputs, including framework outputs, for ancestor-relative Git status output; complements the argument-path heuristic. Path names are not reproduced here.",
    "checked": checked,
    "findings": findings,
    "limits": "This targeted pattern catches the observed deviation; it is not a comprehensive filesystem-read audit.",
}
(OP / "scope-audit-findings.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"checked": len(checked), "findings": findings}, indent=2))
