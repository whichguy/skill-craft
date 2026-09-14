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
  scripts/capture_evidence.py \
  runtime/until-loop/ADAPTER.md runtime/until-loop/LICENSE \
  runtime/until-loop/scripts/until-loop \
  runtime/until-loop/scripts/until_loop_v2.py \
  runtime/until-loop/scripts/until_loop_packet.py \
  runtime/until-loop/references/decision-rubric.md \
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
    if not path.is_file() or path.suffix not in {".md", ".py", ".sh"}:
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
