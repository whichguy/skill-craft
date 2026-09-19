#!/usr/bin/env bash
# Bash 3.2-compatible runtime calibration; does not require bats-core.
set -u

root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
fixtures="$root/fixtures/bash"
work=
passes=0
failures=0

cleanup() {
  if [ -n "${work:-}" ] && [ -d "$work" ]; then
    rm -rf -- "$work"
  fi
}

trap cleanup EXIT HUP INT TERM

pass() {
  passes=$((passes + 1))
  printf 'PASS %s\n' "$1"
}

fail() {
  failures=$((failures + 1))
  printf 'FAIL %s\n' "$1" >&2
}

expect_file_equal() {
  label=$1
  expected=$2
  actual=$3
  if cmp -s "$expected" "$actual"; then
    pass "$label"
  else
    fail "$label"
  fi
}

expect_file_different() {
  label=$1
  first=$2
  second=$3
  if cmp -s "$first" "$second"; then
    fail "$label"
  else
    pass "$label"
  fi
}

expect_text() {
  label=$1
  expected=$2
  actual=$3
  if [ "$expected" = "$actual" ]; then
    pass "$label"
  else
    fail "$label expected=[$expected] actual=[$actual]"
  fi
}

expect_status() {
  label=$1
  expected=$2
  actual=$3
  if [ "$expected" -eq "$actual" ]; then
    pass "$label"
  else
    fail "$label expected=$expected actual=$actual"
  fi
}

work=$(mktemp -d "${TMPDIR:-/tmp}/shiploop-bash-guidance.XXXXXX") || exit 70
mkdir "$work/glob" || exit 70
touch "$work/glob/alpha" "$work/glob/beta" || exit 70

# Hypothesis B1: quote argument vectors so their exact boundaries survive.
printf '%s\0' 'two words' '*' '' '--leading-dash' >"$work/unsafe.expected"
(
  cd "$work/glob" || exit 70
  "$fixtures/argv_reference.sh" "$work/argv-reference.bin" 'two words' '*' '' '--leading-dash'
)
expect_file_equal "argv reference preserves whitespace glob empty and dash arguments" "$work/unsafe.expected" "$work/argv-reference.bin"
(
  cd "$work/glob" || exit 70
  "$fixtures/argv_unquoted_mutant.sh" "$work/argv-mutant.bin" 'two words' '*' '' '--leading-dash'
)
expect_file_different "argv unquoted mutant is rejected by adversarial arguments" "$work/unsafe.expected" "$work/argv-mutant.bin"

# Negative control: ordinary nonempty tokens do not reveal the unquoted mutant.
printf '%s\0' plain tokens >"$work/plain.expected"
(
  cd "$work/glob" || exit 70
  "$fixtures/argv_reference.sh" "$work/plain-reference.bin" plain tokens
  "$fixtures/argv_unquoted_mutant.sh" "$work/plain-mutant.bin" plain tokens
)
expect_file_equal "argv reference passes plain-token control" "$work/plain.expected" "$work/plain-reference.bin"
expect_file_equal "argv mutant also passes plain-token control" "$work/plain.expected" "$work/plain-mutant.bin"

# `set -euo pipefail` does not make every command in an if-condition function fatal.
"$fixtures/conditional_function_errexit_exception.sh" "$work/conditional.audit" >"$work/conditional.out"
expect_text "conditional function counterexample exits successfully under set-euo-pipefail" 'if-branch-success' "$(cat "$work/conditional.out")"
expect_text "conditional function counterexample continues after false" 'continued-after-false' "$(cat "$work/conditional.audit")"

# Hypothesis B2: pipefail plus an if condition retains the status and lets cleanup run.
run_pipeline() {
  fixture=$1
  audit=$2
  output=$3
  "$fixture" "$audit" "$fixtures/failing_probe.sh" >"$output"
  status=$?
  printf '%s\n' "$status"
}

reference_status=$(run_pipeline "$fixtures/pipeline_reference.sh" "$work/reference.audit" "$work/reference.out")
expect_status "pipeline reference returns probe status" 42 "$reference_status"
expect_text "pipeline reference handles expected failure under errexit" 'handled-pipeline-status=42' "$(cat "$work/reference.out")"
reference_workspace=$(cat "$work/reference.audit")
if [ ! -e "$reference_workspace" ]; then
  pass "pipeline reference removes owned workspace"
else
  fail "pipeline reference removes owned workspace"
fi

last_status=$(run_pipeline "$fixtures/pipeline_last_status_mutant.sh" "$work/last-status.audit" "$work/last-status.out")
expect_status "pipeline no-pipefail mutant exposes false success" 0 "$last_status"
expect_text "pipeline no-pipefail mutant reports false success" 'unexpected-success' "$(cat "$work/last-status.out")"
last_status_workspace=$(cat "$work/last-status.audit")
if [ ! -e "$last_status_workspace" ]; then
  pass "pipeline no-pipefail mutant still cleans its workspace"
else
  fail "pipeline no-pipefail mutant still cleans its workspace"
fi

errexit_status=$(run_pipeline "$fixtures/pipeline_errexit_mutant.sh" "$work/errexit.audit" "$work/errexit.out")
expect_status "pipeline direct-errexit mutant returns probe status" 42 "$errexit_status"
expect_text "pipeline direct-errexit mutant omits recovery report" '' "$(cat "$work/errexit.out")"
errexit_workspace=$(cat "$work/errexit.audit")
if [ ! -e "$errexit_workspace" ]; then
  pass "pipeline direct-errexit mutant still runs EXIT cleanup"
else
  fail "pipeline direct-errexit mutant still runs EXIT cleanup"
fi

no_cleanup_status=$(run_pipeline "$fixtures/pipeline_no_cleanup_mutant.sh" "$work/no-cleanup.audit" "$work/no-cleanup.out")
expect_status "pipeline no-cleanup mutant preserves the status alone" 42 "$no_cleanup_status"
expect_text "pipeline no-cleanup mutant preserves the report alone" 'handled-pipeline-status=42' "$(cat "$work/no-cleanup.out")"
no_cleanup_workspace=$(cat "$work/no-cleanup.audit")
if [ -e "$no_cleanup_workspace" ]; then
  pass "pipeline no-cleanup mutant is rejected by workspace assertion"
  rm -rf -- "$no_cleanup_workspace"
else
  fail "pipeline no-cleanup mutant is rejected by workspace assertion"
fi

for script in "$fixtures"/*.sh "$root/test_bash_guidance.sh"; do
  if /bin/bash -n "$script"; then
    pass "bash-3.2 syntax $script"
  else
    fail "bash-3.2 syntax $script"
  fi
done

printf 'SUMMARY passes=%s failures=%s bash=%s\n' "$passes" "$failures" "$(/bin/bash --version | head -1)"
if [ "$failures" -ne 0 ]; then
  exit 1
fi
