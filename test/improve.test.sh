#!/usr/bin/env bash
# Relocation regression for the self-contained Improve package.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
default_package="$root/skills/improve"
package="${IMPROVE_PACKAGE_ROOT:-$default_package}"

fail() {
  printf 'improve.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

pass() {
  printf 'improve.test.sh: PASS %s\n' "$*"
}

usage() {
  printf 'usage: %s [--package <improve-package-root>]\n' "${BASH_SOURCE[0]}" >&2
  exit 64
}

if [[ $# -gt 0 ]]; then
  [[ $# -eq 2 && "$1" == "--package" ]] || usage
  [[ -z "${IMPROVE_PACKAGE_ROOT:-}" ]] || fail 'use IMPROVE_PACKAGE_ROOT or --package, not both'
  package="$2"
fi

[[ -d "$package" ]] || fail "package directory does not exist: $package"
package="$(cd "$package" && pwd -P)"
[[ "$(basename "$package")" == 'improve' ]] || fail "package leaf must be improve: $package"

for required in \
  SKILL.md LICENSE README.md agents/openai.yaml \
  references/review-policy.md references/evidence-capture.md \
  references/callback-evidence.md references/legacy-standalone.md \
  scripts/capture_evidence.py \
  runtime/until-loop/ADAPTER.md runtime/until-loop/LICENSE \
  runtime/until-loop/PROVENANCE.json \
  runtime/until-loop/scripts/until-loop \
  runtime/until-loop/scripts/until_loop_ephemeral.py \
  runtime/until-loop/scripts/until_loop_v2.py \
  runtime/until-loop/scripts/until_loop_packet.py \
  runtime/until-loop/references/decision-rubric.md \
  runtime/until-loop/references/legacy-skill.md \
  runtime/until-loop/references/runtime-ephemeral.md \
  runtime/until-loop/references/runtime-v2.md \
  runtime/until-loop/references/runtime.md \
  runtime/until-loop/references/state.md \
  runtime/until-loop/references/packet.md; do
  [[ -f "$package/$required" ]] || fail "missing package file: $required"
done

run_python() {
  env -i PATH="$PATH" HOME="${HOME:-/tmp}" PYTHONNOUSERSITE=1 \
    PYTHONDONTWRITEBYTECODE=1 python3 "$@"
}

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/improve-package-test.XXXXXX")"
cleanup() {
  rm -rf "$tmpdir"
}
trap cleanup EXIT

copy_parent="$tmpdir/isolated package parent with spaces"
mkdir -p "$copy_parent"
cp -R "$package" "$copy_parent/improve"
bundle="$copy_parent/improve"

# The copied leaf has no parent checkout to satisfy a source-relative import.
run_python - "$bundle" "$package" <<'PY'
import os
import re
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
source_root = Path(sys.argv[2]).resolve()
errors = []
cards = sorted(path.relative_to(root).as_posix() for path in root.rglob("SKILL.md"))
if cards != ["SKILL.md"]:
    errors.append(f"unexpected discoverable skills: {cards}")
for path in root.rglob("*"):
    if path.is_symlink():
        target = (path.parent / os.readlink(path)).resolve(strict=False)
        try:
            target.relative_to(root)
        except ValueError:
            errors.append(f"external symlink: {path.relative_to(root)} -> {target}")
    if not path.is_file() or path.suffix not in {".json", ".md", ".py", ".sh"}:
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    if str(source_root) in text:
        errors.append(f"source-checkout path leaked into {path.relative_to(root)}")
    if re.search(r"(?:/Users/|/home/|/opt/|/private/var/)", text):
        errors.append(f"absolute host path leaked into {path.relative_to(root)}")
    if path.suffix == ".py" and re.search(
        r"(?:sys\.path\.(?:append|insert)|SourceFileLoader)\([^\n]*['\"](?:/|~)", text
    ):
        errors.append(f"absolute Python import path in {path.relative_to(root)}")
for forbidden in (".git", "__pycache__"):
    if any(path.name == forbidden for path in root.rglob("*")):
        errors.append(f"forbidden package artifact: {forbidden}")
if errors:
    raise SystemExit("; ".join(errors))
PY
pass isolated_tree_has_no_external_binding

workspace="$tmpdir/workspace with spaces"
mkdir -p "$workspace"
git -C "$workspace" init -q
printf 'baseline\n' >"$workspace/tracked.txt"
git -C "$workspace" add tracked.txt
git -C "$workspace" -c user.name='Improve test' -c user.email='improve@test.invalid' \
  commit -qm 'initial candidate'

contract="$tmpdir/preview contract.json"
run_python - "$contract" <<'PY'
import json
import sys
from pathlib import Path

contract = {
    "version": 1,
    "policy": "decision-rubric/2",
    "original_request": "Preview an Improve review without changing the workspace.",
    "interpretation": (
        "Execute: inspect the selected candidate. Continue while a required "
        "criterion lacks current evidence. Success: every criterion has "
        "current evidence. Early stop: a real blocker prevents useful progress."
    ),
    "criteria": [
        {
            "id": "C1",
            "text": "The candidate is reviewed before any change is proposed.",
            "basis": {"kind": "request", "reference": "Preview an Improve review"},
        }
    ],
}
Path(sys.argv[1]).write_text(json.dumps(contract) + "\n", encoding="utf-8")
PY

before_status="$(git -C "$workspace" status --porcelain=v1 --untracked-files=all)"
[[ ! -e "$workspace/.until-loop" ]] || fail 'workspace unexpectedly has a runtime directory before preview'
preview="$tmpdir/preview.json"
(
  cd "$workspace"
  run_python "$bundle/runtime/until-loop/scripts/until-loop" v2 preview \
    --contract-file "$contract" >"$preview"
)
run_python - "$preview" <<'PY'
import json
import sys

preview = json.load(open(sys.argv[1], encoding="utf-8"))
assert preview["mode"] == "preview"
assert preview["status"] == "not_initialized"
assert preview["execution"] == "not_executed"
assert preview["contract"]["criteria"][0]["id"] == "C1"
assert isinstance(preview["contract_digest"], str) and len(preview["contract_digest"]) == 64
PY
after_status="$(git -C "$workspace" status --porcelain=v1 --untracked-files=all)"
[[ "$before_status" == "$after_status" ]] || fail 'v2 preview changed workspace status'
[[ ! -e "$workspace/.until-loop" ]] || fail 'v2 preview initialized runtime state'
if find "$bundle" \( -name __pycache__ -o -name '*.pyc' \) -print -quit | grep -q .; then
  fail 'v2 preview wrote bytecode into the copied package'
fi
pass relocated_v2_preview_is_read_only

run_python - "$bundle" "$package" <<'PY'
import hashlib
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
manifest = json.loads((root / "runtime/until-loop/PROVENANCE.json").read_text(encoding="utf-8"))
card = (root / "SKILL.md").read_text(encoding="utf-8")
adapter = (root / "runtime/until-loop/ADAPTER.md").read_text(encoding="utf-8")
# Relocation must preserve the selected package version, not pin a prior release.
source_card = (Path(sys.argv[2]) / "SKILL.md").read_text(encoding="utf-8")
assert card == source_card, "relocation changed the selected skill card"
source_version = re.search(r"(?m)^version: (\S+)$", source_card.split("---", 2)[1])
assert source_version is not None, "selected Improve card requires a declared version"
card_version = re.search(r"(?m)^version: (\S+)$", card.split("---", 2)[1])
assert card_version is not None, "relocated Improve card requires a declared version"
assert card_version.group(1) == source_version.group(1)
assert "runtime/until-loop/scripts/until_loop_ephemeral.py" in card
assert "version: 0.4.0-rc.2" in adapter
assert manifest["format"] == "skill-craft-until-loop-runtime-provenance/v1"
assert manifest["upstream"] == {
    "repository": "https://github.com/whichguy/until-loop.git",
    "commit": "458f40ac35c8254906898890c25a784a6e3eb39c",
    "version": "0.4.0-rc.2",
}
entries = {entry["bundled_path"]: entry for entry in manifest["default_ephemeral_runtime"]}
script = root / "runtime/until-loop/scripts/until_loop_ephemeral.py"
assert entries["scripts/until_loop_ephemeral.py"]["sha256"] == (
    "6a4131f8a70b56a361556fbc61e924f060ebf1ba5d5f1387a6d6d735e89b4212"
)
assert hashlib.sha256(script.read_bytes()).hexdigest() == entries[
    "scripts/until_loop_ephemeral.py"
]["sha256"]
assert hashlib.sha256((root / "runtime/until-loop/ADAPTER.md").read_bytes()).hexdigest() == entries[
    "ADAPTER.md"
]["sha256"]
assert entries["ADAPTER.md"]["upstream_sha256"] == (
    "609959649f69f3ee5408bedbd6331806799495a8f59418e8d097c3d9f3c08028"
)
assert entries["ADAPTER.md"]["adaptation_reason"].strip()
assert entries["ADAPTER.md"]["sha256"] != entries["ADAPTER.md"]["upstream_sha256"]
PY
pass ephemeral_runtime_provenance_matches_v0_4_0_rc_2

ephemeral_runtime="$bundle/runtime/until-loop/scripts/until_loop_ephemeral.py"
ephemeral_contract="$tmpdir/ephemeral contract.json"
ephemeral_state_dir="$tmpdir/ephemeral state with spaces"
mkdir -p "$ephemeral_state_dir"
run_python - "$workspace" "$bundle" "$ephemeral_contract" <<'PY'
import json
import sys
from pathlib import Path

workspace = Path(sys.argv[1])
bundle = Path(sys.argv[2])
contract = {
    "workspace": str(workspace),
    "work": (
        "Read the scoped candidate and recent history, plan worthwhile authorized work, "
        "run applicable checks, and retain one completed review record."
    ),
    "exit_condition": (
        "Two distinct qualifying clean reviews and current evidence establish the scoped result."
    ),
    "repeat_condition": "A distinct required review remains unless an actual blocker or stop applies.",
    "required_trivial_reviews": 2,
    "context": {
        "request": "Relocated Improve callback test with two distinct clean reviews.",
        "scope": "Frozen initial candidate: tracked.txt only; preserve all other files.",
        "authority": "Do not commit, push, publish, or change files for this protocol test.",
        "environment": "Use the relocated bundled runtime and the initialized test workspace.",
        "resources": [
            {"purpose": "candidate", "locator": str(workspace / "tracked.txt")},
            {"purpose": "selected Improve card", "locator": str(bundle / "SKILL.md")},
        ],
    },
}
Path(sys.argv[3]).write_text(json.dumps(contract) + "\n", encoding="utf-8")
PY

ephemeral_initial="$tmpdir/ephemeral initial.json"
run_python "$ephemeral_runtime" start --directory "$ephemeral_state_dir" \
  <"$ephemeral_contract" >"$ephemeral_initial"
ephemeral_state="$(run_python - "$ephemeral_initial" <<'PY'
import json
import sys

packet = json.load(open(sys.argv[1], encoding="utf-8"))
assert packet["status"] == "active"
assert packet["progress"] == {
    "action_number": 1,
    "trivial_streak": 0,
    "required_trivial_reviews": 2,
}
assert packet["context"]["request"].startswith("Relocated Improve callback")
assert packet["next_argv"]
assert packet["done_argv"]
print(packet["state_file"])
PY
)"
[[ -f "$ephemeral_state" ]] || fail 'ephemeral start did not create a state file'
[[ "$(cd "$(dirname "$ephemeral_state")" && pwd -P)" == \
   "$(cd "$ephemeral_state_dir" && pwd -P)" ]] \
  || fail "ephemeral state escaped requested directory: $ephemeral_state"

ephemeral_next="$tmpdir/ephemeral next.json"
run_python "$ephemeral_runtime" next --state "$ephemeral_state" >"$ephemeral_next"
run_python - "$ephemeral_initial" "$ephemeral_next" <<'PY'
import json
import sys

assert json.load(open(sys.argv[1], encoding="utf-8")) == json.load(
    open(sys.argv[2], encoding="utf-8")
)
PY

ephemeral_first_report="$tmpdir/ephemeral first report.json"
run_python - "$ephemeral_first_report" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(
    json.dumps(
        {
            "classification": "trivial",
            "exit_assessment": "satisfied",
            "continuation_assessment": "allowed",
            "evidence": "First distinct clean review completed with current scoped evidence.",
            "handoff": "First clean review complete; preserve the frozen scope and perform one more distinct review.",
        }
    )
    + "\n",
    encoding="utf-8",
)
PY
ephemeral_second="$tmpdir/ephemeral second packet.json"
run_python - "$ephemeral_initial" "$ephemeral_first_report" >"$ephemeral_second" <<'PY'
import json
import subprocess
import sys

packet = json.load(open(sys.argv[1], encoding="utf-8"))
report = json.load(open(sys.argv[2], encoding="utf-8"))
result = subprocess.run(
    packet["done_argv"], input=json.dumps(report), text=True, capture_output=True, check=False
)
if result.returncode:
    raise SystemExit(result.stderr or result.stdout)
sys.stdout.write(result.stdout)
PY
run_python - "$ephemeral_second" "$ephemeral_first_report" "$ephemeral_state" <<'PY'
import json
import sys
from pathlib import Path

packet = json.load(open(sys.argv[1], encoding="utf-8"))
report = json.load(open(sys.argv[2], encoding="utf-8"))
assert packet["status"] == "active"
assert packet["progress"]["action_number"] == 2
assert packet["progress"]["trivial_streak"] == 1
assert packet["last_report"] == report
assert packet["state_file"] == sys.argv[3]
assert Path(sys.argv[3]).is_file()
PY

ephemeral_second_report="$tmpdir/ephemeral second report.json"
run_python - "$ephemeral_second_report" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(
    json.dumps(
        {
            "classification": "trivial",
            "exit_assessment": "satisfied",
            "continuation_assessment": "allowed",
            "evidence": "Second distinct clean review completed with current scoped evidence.",
            "handoff": "Two qualifying reviews complete; terminal response carries the final receipt.",
        }
    )
    + "\n",
    encoding="utf-8",
)
PY
ephemeral_terminal="$tmpdir/ephemeral terminal packet.json"
run_python - "$ephemeral_second" "$ephemeral_second_report" >"$ephemeral_terminal" <<'PY'
import json
import subprocess
import sys

packet = json.load(open(sys.argv[1], encoding="utf-8"))
report = json.load(open(sys.argv[2], encoding="utf-8"))
result = subprocess.run(
    packet["done_argv"], input=json.dumps(report), text=True, capture_output=True, check=False
)
if result.returncode:
    raise SystemExit(result.stderr or result.stdout)
sys.stdout.write(result.stdout)
PY
run_python - "$ephemeral_terminal" "$ephemeral_second_report" <<'PY'
import json
import sys

packet = json.load(open(sys.argv[1], encoding="utf-8"))
report = json.load(open(sys.argv[2], encoding="utf-8"))
assert packet["status"] == "complete"
assert packet["progress"]["trivial_streak"] == 2
assert packet["last_report"] == report
assert packet["next_argv"] is None
assert packet["done_argv"] is None
PY
[[ ! -e "$ephemeral_state" ]] || fail 'ephemeral terminal transition did not delete its state file'
[[ -z "$(find "$ephemeral_state_dir" -mindepth 1 -maxdepth 1 -print -quit)" ]] \
  || fail 'ephemeral terminal transition left a state artifact'
[[ ! -e "$workspace/.until-loop" ]] || fail 'ephemeral runtime created durable workspace state'
pass relocated_ephemeral_start_next_done_two_trivial_gate_and_terminal_deletion

runtime="$bundle/runtime/until-loop/scripts/until-loop"
collector="$bundle/scripts/capture_evidence.py"
run_python "$runtime" v2 init --repo "$workspace" --contract-file "$contract" \
  >"$tmpdir/init.json"
record="$(run_python "$collector" snapshot --repo "$workspace" \
  --owner standalone-improve --history-window 1 --scope tracked.txt)"
[[ -f "$record" ]] || fail 'collector did not create an evidence record'
run_python - "$record" <<'PY'
import json
import sys

record = json.load(open(sys.argv[1], encoding="utf-8"))
runtime = record["tool_facts"]["runtime"]
assert runtime["kind"] == "v2"
assert runtime["validation"] == "v2_action_revision_and_result_path_checked"
assert isinstance(runtime["action_id"], str) and len(runtime["action_id"]) == 32
PY
pass collector_uses_bundled_v2_validator

run_python - "$workspace/.until-loop/state.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
state = json.loads(path.read_text(encoding="utf-8"))
state["phase"] = "corrupt"
path.write_text(json.dumps(state) + "\n", encoding="utf-8")
PY
set +e
bad_output="$(run_python "$collector" snapshot --repo "$workspace" \
  --owner standalone-improve --history-window 1 --scope tracked.txt 2>&1)"
bad_status=$?
set -e
[[ "$bad_status" -eq 2 ]] || fail "bad v2 state exit: want 2 got $bad_status: $bad_output"
printf '%s\n' "$bad_output" | grep -q 'invalid v2 runtime state' \
  || fail "bad v2 state rejection missing: $bad_output"
pass collector_rejects_bad_bundled_v2_state

printf 'improve.test.sh: PASS package=%s\n' "$package"
