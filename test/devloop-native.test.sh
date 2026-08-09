#!/usr/bin/env bash
# Hermetic DevLoop native CLI tests (no network, no host harness CLIs).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cli="$root/skills/devloop-native/scripts/devloop-native"
fixtures="$root/test/fixtures/devloop-native"

fail() {
  printf 'devloop-native.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -x "$cli" ]] || fail "cli not executable"
[[ -f "$root/skills/devloop-native/SKILL.md" ]] || fail "missing SKILL.md"
[[ ! -d "$root/skills/devloop-native/prompts" ]] || fail "prompts/ must not exist"
[[ ! -d "$root/skills/devloop" ]] || fail "reserved skills/devloop must not exist"
grep -q 'kind: script-backed' "$root/skills/devloop-native/SKILL.md" || fail "frontmatter kind"
grep -q 'name: devloop-native' "$root/skills/devloop-native/SKILL.md" || fail "frontmatter name"
# Demoted: description must not own bare "devloop" as primary product trigger
skill_md="$root/skills/devloop-native/SKILL.md"
# Extract YAML description block (folded >- lines under description:)
desc="$(awk '
  /^description:[[:space:]]*>-/ {grab=1; next}
  grab && /^  / {print; next}
  grab && /^[^ ]/ {exit}
' "$skill_md")"
[[ -n "$desc" ]] || fail "no description block"
printf '%s\n' "$desc" | grep -qi 'devloop-run' || fail "description must redirect to devloop-run"
printf '%s\n' "$desc" | grep -qiE '/devloop-native|offline evidence|freeze prove stop|evidence gates' \
  || fail "description must use demoted triggers"
# Frontmatter description must not claim bare NL "user says devloop"
if printf '%s\n' "$desc" | grep -qiE 'user says devloop|says devloop, DevLoop'; then
  fail "description must not claim bare devloop trigger"
fi
grep -qiE 'Not the default DevLoop|not the default DevLoop|demoted' \
  "$skill_md" || fail "body must demote default claim"
# purity: no peer harness transport tokens in scripts
if rg -n 'HERMES_BIN|hermes chat|devloop-run|codex exec' "$root/skills/devloop-native/scripts" 2>/dev/null; then
  fail "purity: forbidden transport tokens in scripts"
fi
printf 'LAYER simple: entry+structure+purity OK\n'

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/devloop-native-test.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

# --- self-check ---
out="$("$cli" self-check)"
printf '%s\n' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["ok"] and d["mode"]=="native"' || fail "self-check"
printf 'LAYER simple: self-check OK\n'

# --- usage fail-closed: no subcommand ---
set +e
out_usage="$("$cli" 2>&1)"
rc_usage=$?
set -e
[[ "$rc_usage" -ne 0 ]] || fail "no-cmd usage want non-zero got $rc_usage: $out_usage"
printf '%s\n' "$out_usage" | grep -qiE 'usage|required|cmd' || fail "no-cmd usage text: $out_usage"
printf 'LAYER simple: no-cmd usage fail-closed OK\n'

# --- happy path: red then green ---
repo="$tmpdir/repo-happy"
mkdir -p "$repo"
# guard file for optional digest tests
printf 'GUARD_V1\n' >"$repo/guard.txt"
# charter: fails until marker file exists
cat >"$repo/charter.json" <<'JSON'
{
  "goal": "create marker with ok",
  "criteria": [
    {
      "id": "C1",
      "role": "change",
      "outcome": "marker says ok",
      "verifier": {
        "argv": ["python3", "-c", "import pathlib,sys; p=pathlib.Path('marker.txt'); sys.exit(0 if p.is_file() and p.read_text()=='ok\\n' else 1)"],
        "cwd": ".",
        "expected_exit": 0,
        "timeout_seconds": 30,
        "guard_paths": ["guard.txt"]
      }
    }
  ]
}
JSON

run="$repo/.devloop-native/run"
"$cli" freeze --charter "$repo/charter.json" --repo "$repo" --run-dir "$run" >/dev/null
[[ -f "$run/charter.json" && -f "$run/charter.sha256" ]] || fail "freeze artifacts"

set +e
"$cli" prove --run-dir "$run" >/dev/null
rc=$?
set -e
[[ "$rc" -eq 1 ]] || fail "prove should fail red (exit 1) got $rc"
python3 -c 'import json; d=json.load(open("'"$run"'/prove.json")); assert d["change_observed_red"]["C1"] is True' || fail "prove red flag"

# stop before build must fail verifiers or block if never red — red was observed so stop runs and fails
set +e
"$cli" stop --run-dir "$run" >/dev/null
rc=$?
set -e
[[ "$rc" -eq 1 ]] || fail "stop red should exit 1 got $rc"

printf 'ok\n' >"$repo/marker.txt"
# Re-prove after green BUILD must keep sticky red baseline (not erase never_red history)
"$cli" prove --run-dir "$run" >/dev/null || fail "re-prove after build should exit 0"
python3 -c 'import json; d=json.load(open("'"$run"'/prove.json")); assert d["change_observed_red"]["C1"] is True' \
  || fail "sticky red lost after green re-prove"
"$cli" stop --run-dir "$run" >/dev/null || fail "stop green"
python3 -c 'import json; d=json.load(open("'"$run"'/receipt.json")); assert d["status"]=="PASS" and d["mode"]=="native"' || fail "receipt"
printf 'LAYER e2e: freeze→prove(red)→build→prove(sticky)→stop PASS OK\n'

# charter content drift after freeze
repo_d="$tmpdir/repo-charter-drift"
mkdir -p "$repo_d"
cat >"$repo_d/charter.json" <<'JSON'
{
  "goal": "g",
  "criteria": [{
    "id": "R1",
    "role": "regression",
    "outcome": "true",
    "verifier": {
      "argv": ["python3", "-c", "raise SystemExit(0)"],
      "expected_exit": 0,
      "timeout_seconds": 10,
      "guard_paths": []
    }
  }]
}
JSON
run_d="$repo_d/.devloop-native/run"
"$cli" freeze --charter "$repo_d/charter.json" --repo "$repo_d" --run-dir "$run_d" >/dev/null
python3 -c 'import json;p="'"$run_d"'/charter.json";d=json.load(open(p));d["goal"]="TAMPER";json.dump(d,open(p,"w"),indent=2)'
set +e
out="$("$cli" prove --run-dir "$run_d" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "charter drift want 2 got $rc: $out"
printf '%s\n' "$out" | grep -q charter_drift || fail "charter_drift reason: $out"

# --- guard drift ---
repo2="$tmpdir/repo-guard"
mkdir -p "$repo2"
printf 'G1\n' >"$repo2/guard.txt"
cat >"$repo2/charter.json" <<'JSON'
{
  "goal": "always pass true",
  "criteria": [{
    "id": "R1",
    "role": "regression",
    "outcome": "true",
    "verifier": {
      "argv": ["python3", "-c", "raise SystemExit(0)"],
      "expected_exit": 0,
      "timeout_seconds": 10,
      "guard_paths": ["guard.txt"]
    }
  }]
}
JSON
run2="$repo2/.devloop-native/run"
"$cli" freeze --charter "$repo2/charter.json" --repo "$repo2" --run-dir "$run2" >/dev/null
printf 'G2\n' >"$repo2/guard.txt"
set +e
out="$("$cli" prove --run-dir "$run2" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "guard drift want exit 2 got $rc: $out"
printf '%s\n' "$out" | grep -q guard_drift || fail "guard_drift reason: $out"

# --- never_red (change criterion green at prove) ---
repo3="$tmpdir/repo-never-red"
mkdir -p "$repo3"
cat >"$repo3/charter.json" <<'JSON'
{
  "goal": "already green change",
  "criteria": [{
    "id": "C1",
    "role": "change",
    "outcome": "always 0",
    "verifier": {
      "argv": ["python3", "-c", "raise SystemExit(0)"],
      "expected_exit": 0,
      "timeout_seconds": 10,
      "guard_paths": []
    }
  }]
}
JSON
run3="$repo3/.devloop-native/run"
"$cli" freeze --charter "$repo3/charter.json" --repo "$repo3" --run-dir "$run3" >/dev/null
set +e
"$cli" prove --run-dir "$run3" >/dev/null
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail "prove green change exit 0 got $rc"
set +e
out="$("$cli" stop --run-dir "$run3" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "never_red want 2 got $rc: $out"
printf '%s\n' "$out" | grep -q never_red || fail "never_red reason missing: $out"

# --- refuse package root as repo ---
set +e
out="$("$cli" freeze --charter "$repo3/charter.json" --repo "$root/skills/devloop-native" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "package root refuse want 2 got $rc: $out"
printf '%s\n' "$out" | grep -q package_root_write || fail "package_root_write reason: $out"

# --- shell -c rejected (bare name and path form) ---
cat >"$tmpdir/bad-charter.json" <<'JSON'
{
  "criteria": [{
    "id": "X",
    "role": "change",
    "outcome": "x",
    "verifier": { "argv": ["bash", "-c", "true"], "expected_exit": 0 }
  }]
}
JSON
set +e
out="$("$cli" freeze --charter "$tmpdir/bad-charter.json" --repo "$repo3" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 64 ]] || fail "shell -c want 64 got $rc: $out"

cat >"$tmpdir/bad-charter-path.json" <<'JSON'
{
  "criteria": [{
    "id": "X",
    "role": "change",
    "outcome": "x",
    "verifier": { "argv": ["/bin/bash", "-lc", "true"], "expected_exit": 0 }
  }]
}
JSON
set +e
out="$("$cli" freeze --charter "$tmpdir/bad-charter-path.json" --repo "$repo3" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 64 ]] || fail "/bin/bash -lc want 64 got $rc: $out"

# --- missing executable at freeze ---
cat >"$tmpdir/missing-exe.json" <<'JSON'
{
  "criteria": [{
    "id": "M1",
    "role": "regression",
    "outcome": "x",
    "verifier": {
      "argv": ["devloop_native_definitely_missing_xyzzy_99", "--version"],
      "expected_exit": 0,
      "timeout_seconds": 5,
      "guard_paths": []
    }
  }]
}
JSON
set +e
out="$("$cli" freeze --charter "$tmpdir/missing-exe.json" --repo "$repo3" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "missing exec want 2 got $rc: $out"
printf '%s\n' "$out" | grep -q missing_executable || fail "missing_executable reason: $out"

# --- missing guard at freeze ---
cat >"$tmpdir/missing-guard.json" <<'JSON'
{
  "criteria": [{
    "id": "G1",
    "role": "regression",
    "outcome": "x",
    "verifier": {
      "argv": ["python3", "-c", "raise SystemExit(0)"],
      "expected_exit": 0,
      "timeout_seconds": 5,
      "guard_paths": ["no_such_guard_file.txt"]
    }
  }]
}
JSON
set +e
out="$("$cli" freeze --charter "$tmpdir/missing-guard.json" --repo "$repo3" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "missing guard want 2 got $rc: $out"
printf '%s\n' "$out" | grep -q missing_guard || fail "missing_guard reason: $out"

# --- stop without prove ---
repo4="$tmpdir/repo-no-prove"
mkdir -p "$repo4"
cat >"$repo4/charter.json" <<'JSON'
{
  "goal": "g",
  "criteria": [{
    "id": "R1",
    "role": "regression",
    "outcome": "true",
    "verifier": {
      "argv": ["python3", "-c", "raise SystemExit(0)"],
      "expected_exit": 0,
      "timeout_seconds": 10,
      "guard_paths": []
    }
  }]
}
JSON
run4="$repo4/.devloop-native/run"
"$cli" freeze --charter "$repo4/charter.json" --repo "$repo4" --run-dir "$run4" >/dev/null
set +e
out="$("$cli" stop --run-dir "$run4" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "no_prove want 2 got $rc: $out"
printf '%s\n' "$out" | grep -q no_prove || fail "no_prove reason: $out"

# --- regression-only green path can COMPLETE without never_red ---
"$cli" prove --run-dir "$run4" >/dev/null || fail "regression prove green"
"$cli" stop --run-dir "$run4" >/dev/null || fail "regression stop green"
python3 -c 'import json; d=json.load(open("'"$run4"'/receipt.json")); assert d["status"]=="PASS"' \
  || fail "regression receipt PASS"

# --- multi-criterion: stop re-runs all (one fail → FAIL) ---
repo5="$tmpdir/repo-multi"
mkdir -p "$repo5"
printf 'ok\n' >"$repo5/a.txt"
cat >"$repo5/charter.json" <<'JSON'
{
  "goal": "two checks",
  "criteria": [
    {
      "id": "A",
      "role": "regression",
      "outcome": "a exists",
      "verifier": {
        "argv": ["python3", "-c", "import pathlib,sys; sys.exit(0 if pathlib.Path('a.txt').is_file() else 1)"],
        "expected_exit": 0,
        "timeout_seconds": 10,
        "guard_paths": []
      }
    },
    {
      "id": "B",
      "role": "regression",
      "outcome": "b missing fails",
      "verifier": {
        "argv": ["python3", "-c", "import pathlib,sys; sys.exit(0 if pathlib.Path('b.txt').is_file() else 1)"],
        "expected_exit": 0,
        "timeout_seconds": 10,
        "guard_paths": []
      }
    }
  ]
}
JSON
run5="$repo5/.devloop-native/run"
"$cli" freeze --charter "$repo5/charter.json" --repo "$repo5" --run-dir "$run5" >/dev/null
set +e
"$cli" prove --run-dir "$run5" >/dev/null
set -e
set +e
out="$("$cli" stop --run-dir "$run5" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 1 ]] || fail "multi stop partial fail want 1 got $rc: $out"
python3 -c 'import json; d=json.load(open("'"$run5"'/stop.json")); ids={r["id"]:r["ok"] for r in d["results"]}; assert ids["A"] is True and ids["B"] is False' \
  || fail "stop must re-run all criteria with per-id results"

# --- mixed change: one never red blocks stop even if other was red ---
repo6="$tmpdir/repo-mixed-change"
mkdir -p "$repo6"
cat >"$repo6/charter.json" <<'JSON'
{
  "goal": "mixed",
  "criteria": [
    {
      "id": "C1",
      "role": "change",
      "outcome": "file",
      "verifier": {
        "argv": ["python3", "-c", "import pathlib,sys; sys.exit(0 if pathlib.Path('c1.txt').is_file() else 1)"],
        "expected_exit": 0,
        "timeout_seconds": 10,
        "guard_paths": []
      }
    },
    {
      "id": "C2",
      "role": "change",
      "outcome": "always green",
      "verifier": {
        "argv": ["python3", "-c", "raise SystemExit(0)"],
        "expected_exit": 0,
        "timeout_seconds": 10,
        "guard_paths": []
      }
    }
  ]
}
JSON
run6="$repo6/.devloop-native/run"
"$cli" freeze --charter "$repo6/charter.json" --repo "$repo6" --run-dir "$run6" >/dev/null
set +e
"$cli" prove --run-dir "$run6" >/dev/null
set -e
printf 'x\n' >"$repo6/c1.txt"
set +e
out="$("$cli" stop --run-dir "$run6" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "mixed never_red want 2 got $rc: $out"
printf '%s\n' "$out" | grep -q never_red || fail "mixed never_red reason"
printf '%s\n' "$out" | grep -q C2 || fail "mixed never_red should name C2: $out"

# --- cwd escape and run-dir outside repo ---
cat >"$tmpdir/cwd-escape.json" <<'JSON'
{
  "goal": "g",
  "criteria": [{
    "id": "C",
    "role": "regression",
    "outcome": "o",
    "verifier": {
      "argv": ["python3", "-c", "raise SystemExit(0)"],
      "cwd": "../",
      "expected_exit": 0,
      "timeout_seconds": 5,
      "guard_paths": []
    }
  }]
}
JSON
run_esc="$repo3/.devloop-native/run-esc"
"$cli" freeze --charter "$tmpdir/cwd-escape.json" --repo "$repo3" --run-dir "$run_esc" >/dev/null
set +e
out="$("$cli" prove --run-dir "$run_esc" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 64 ]] || fail "cwd escape want 64 got $rc: $out"

set +e
out="$("$cli" freeze --charter "$repo3/charter.json" --repo "$repo3" --run-dir "$tmpdir/outside-run" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 64 ]] || fail "run-dir outside want 64 got $rc: $out"


# --- not_frozen / invalid JSON / empty criteria / duplicate id / doctor / timeout / missing_repo / missing_cwd ---
set +e
out="$("$cli" prove --run-dir "$tmpdir/no-such-run" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "not_frozen want 2 got $rc: $out"
printf '%s\n' "$out" | grep -q not_frozen || fail "not_frozen reason: $out"

printf 'not-json\n' >"$tmpdir/bad.json"
set +e
out="$("$cli" freeze --charter "$tmpdir/bad.json" --repo "$repo3" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 64 ]] || fail "invalid json want 64 got $rc: $out"

printf '{"criteria":[]}\n' >"$tmpdir/empty-crit.json"
set +e
out="$("$cli" freeze --charter "$tmpdir/empty-crit.json" --repo "$repo3" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 64 ]] || fail "empty criteria want 64 got $rc: $out"

printf '{"criteria":[{"id":"A","role":"regression","outcome":"o","verifier":{"argv":["python3","-c","raise SystemExit(0)"]}},{"id":"A","role":"regression","outcome":"o2","verifier":{"argv":["python3","-c","raise SystemExit(0)"]}}]}\n' >"$tmpdir/dup.json"
set +e
out="$("$cli" freeze --charter "$tmpdir/dup.json" --repo "$repo3" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 64 ]] || fail "duplicate id want 64 got $rc: $out"

out="$("$cli" doctor)" || fail "doctor exit"
printf '%s\n' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["ok"] and d["mode"]=="native" and d.get("issues")==[]' || fail "doctor json"
printf 'LAYER simple: doctor clean OK\n'

# doctor purity fail-closed: dirty *copy* of package (do not pollute SoT)
dirty_pkg="$tmpdir/dirty-pkg"
rm -rf "$dirty_pkg"
cp -R "$root/skills/devloop-native" "$dirty_pkg"
chmod +x "$dirty_pkg/scripts/devloop-native"
# Inject banned transport token into a sibling script file (token assembled in test only)
python3 -c 'open("'"$dirty_pkg"'/scripts/pollute.txt","w").write("pollute " + "HERMES" + "_BIN" + "\n")'
set +e
out="$("$dirty_pkg/scripts/devloop-native" doctor 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "doctor dirty want exit 2 got $rc: $out"
printf '%s\n' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("ok") is False and d.get("issues") and any("purity" in i for i in d["issues"])' \
  || fail "doctor dirty issues: $out"
printf 'LAYER simple: doctor purity fail-closed OK\n'

# timeout
repo_t="$tmpdir/repo-timeout"
mkdir -p "$repo_t"
cat >"$repo_t/charter.json" <<'JSON'
{
  "goal": "timeout",
  "criteria": [{
    "id": "T1",
    "role": "regression",
    "outcome": "sleep",
    "verifier": {
      "argv": ["python3", "-c", "import time; time.sleep(5)"],
      "expected_exit": 0,
      "timeout_seconds": 1,
      "guard_paths": []
    }
  }]
}
JSON
run_t="$repo_t/.devloop-native/run"
"$cli" freeze --charter "$repo_t/charter.json" --repo "$repo_t" --run-dir "$run_t" >/dev/null
set +e
out="$("$cli" prove --run-dir "$run_t" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "timeout want 2 got $rc: $out"
printf '%s\n' "$out" | grep -q timeout || fail "timeout reason: $out"

# missing_repo: freeze then remove repo path while keeping run dir copy
repo_m="$tmpdir/repo-missing"
mkdir -p "$repo_m"
cat >"$repo_m/charter.json" <<'JSON'
{
  "goal": "g",
  "criteria": [{
    "id": "R",
    "role": "regression",
    "outcome": "o",
    "verifier": {
      "argv": ["python3", "-c", "raise SystemExit(0)"],
      "expected_exit": 0,
      "timeout_seconds": 5,
      "guard_paths": []
    }
  }]
}
JSON
run_m="$repo_m/.devloop-native/run"
"$cli" freeze --charter "$repo_m/charter.json" --repo "$repo_m" --run-dir "$run_m" >/dev/null
orphan_run="$tmpdir/orphan-run"
cp -R "$run_m" "$orphan_run"
rm -rf "$repo_m"
set +e
out="$("$cli" prove --run-dir "$orphan_run" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "missing_repo want 2 got $rc: $out"
printf '%s\n' "$out" | grep -q missing_repo || fail "missing_repo reason: $out"

# missing_cwd
repo_c="$tmpdir/repo-missing-cwd"
mkdir -p "$repo_c"
cat >"$repo_c/charter.json" <<'JSON'
{
  "goal": "g",
  "criteria": [{
    "id": "R",
    "role": "regression",
    "outcome": "o",
    "verifier": {
      "argv": ["python3", "-c", "raise SystemExit(0)"],
      "cwd": "no_such_subdir",
      "expected_exit": 0,
      "timeout_seconds": 5,
      "guard_paths": []
    }
  }]
}
JSON
run_c="$repo_c/.devloop-native/run"
"$cli" freeze --charter "$repo_c/charter.json" --repo "$repo_c" --run-dir "$run_c" >/dev/null
set +e
out="$("$cli" prove --run-dir "$run_c" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "missing_cwd want 2 got $rc: $out"
printf '%s\n' "$out" | grep -q missing_cwd || fail "missing_cwd reason: $out"

# charter not found
set +e
out="$("$cli" freeze --charter "$tmpdir/no-charter-file.json" --repo "$repo_c" 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 64 ]] || fail "charter not found want 64 got $rc: $out"

# --- copy layout: run CLI from a copied package tree ---
copy="$tmpdir/pkg-copy"
mkdir -p "$copy"
cp -R "$root/skills/devloop-native/." "$copy/"
chmod +x "$copy/scripts/devloop-native"
"$copy/scripts/devloop-native" self-check >/dev/null || fail "copy self-check"

# --- symlink layout ---
linkroot="$tmpdir/link-home/skills"
mkdir -p "$linkroot"
ln -s "$root/skills/devloop-native" "$linkroot/devloop-native"
"$linkroot/devloop-native/scripts/devloop-native" self-check >/dev/null || fail "symlink self-check"
printf 'LAYER integration: copy+symlink package layouts OK\n'

# --- mock-host e2e: single charter file, agent-like argv sequence ---
repo_e2e="$tmpdir/mock-host-e2e"
mkdir -p "$repo_e2e"
cat >"$repo_e2e/charter.json" <<'JSON'
{
  "goal": "mock host e2e marker",
  "criteria": [{
    "id": "E1",
    "role": "change",
    "outcome": "result.txt is ready",
    "verifier": {
      "argv": ["python3", "-c", "import pathlib,sys; p=pathlib.Path('result.txt'); sys.exit(0 if p.is_file() and p.read_text()=='devloop-ok\\n' else 1)"],
      "expected_exit": 0,
      "timeout_seconds": 15,
      "guard_paths": []
    }
  }]
}
JSON
run_e2e="$repo_e2e/.devloop-native/run"
"$cli" freeze --charter "$repo_e2e/charter.json" --repo "$repo_e2e" --run-dir "$run_e2e" >/dev/null
set +e
"$cli" prove --run-dir "$run_e2e" >/dev/null
rc=$?
set -e
[[ "$rc" -eq 1 ]] || fail "mock-host prove red want 1 got $rc"
printf 'devloop-ok\n' >"$repo_e2e/result.txt"
"$cli" stop --run-dir "$run_e2e" >/dev/null || fail "mock-host stop"
python3 -c 'import json; d=json.load(open("'"$run_e2e"'/receipt.json")); assert d["status"]=="PASS" and d["mode"]=="native" and d.get("goal")' \
  || fail "mock-host receipt"
printf 'LAYER e2e: mock-host freeze/prove/edit/stop OK\n'

printf 'devloop-native.test.sh: PASS\n'
