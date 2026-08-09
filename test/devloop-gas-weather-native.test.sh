#!/usr/bin/env bash
# Native e2e: invoke real devloop-run (engine shim) for a GAS weather DoD.
#
# Env:
#   DEVLOOP_LIVE_WEATHER=1  — run live multi-model engine (required for success path)
#   DEVLOOP_LIVE_WEATHER=0  — hermetic wiring only (probe + offline contract on existing files)
#   DEVLOOP_WEATHER_REPO    — absolute repo path (default: ~/src/gas-weather-devloop-e2e)
#   DEVLOOP_HOME            — engine root
#   SCRATCH / GROK_GOAL_SCRATCH — log dir (writes devloop-weather-native.log)
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
run="$root/skills/devloop-run/scripts/devloop-run"
shim="$root/test/fixtures/ollama-hermes-shim"
scratch_default="${GROK_GOAL_SCRATCH:-${SCRATCH:-}}"
if [[ -z "$scratch_default" ]]; then
  scratch_default="$(mktemp -d "${TMPDIR:-/tmp}/devloop-weather-XXXXXX")"
fi
mkdir -p "$scratch_default"
log="$scratch_default/devloop-weather-native.log"
repo="${DEVLOOP_WEATHER_REPO:-$HOME/src/gas-weather-devloop-e2e}"
engine="${DEVLOOP_HOME:-$HOME/.hermes/skills/software-development/devloop}"
live="${DEVLOOP_LIVE_WEATHER:-1}"

fail() { printf 'devloop-gas-weather-native: FAIL %s\n' "$*" | tee -a "$log" >&2; exit 1; }

[[ -x "$run" ]] || fail "missing executable $run"
[[ -f "$shim" ]] || fail "missing shim $shim"
chmod +x "$shim"
[[ -d "$engine" && -f "$engine/scripts/devloop_cli.py" ]] || fail "engine missing: $engine"
[[ -f "$engine/engine-capabilities.json" ]] || fail "engine lacks engine-capabilities.json"

{
  echo "=== native weather e2e $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo "run=$run"
  echo "engine=$engine"
  echo "repo=$repo"
  echo "live=$live"
} | tee "$log"

write_offline_contract_tests() {
  mkdir -p "$repo/tests"
  cat >"$repo/tests/test_weather_contract.py" <<'PY'
"""Offline contract for DevLoop-produced GAS weather project."""
from __future__ import annotations
import json, re, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

class WeatherContractTest(unittest.TestCase):
    def test_required_paths(self) -> None:
        for rel in ("common-js/weather.gs", "appsscript.json", "tests/test_weather_contract.py"):
            self.assertTrue((ROOT / rel).is_file(), f"missing {rel}")

    def test_weather_module(self) -> None:
        text = (ROOT / "common-js/weather.gs").read_text(encoding="utf-8")
        self.assertIn("__events__", text)
        self.assertRegex(text, r"doGet\s*:\s*['\"]handleGet['\"]")
        self.assertRegex(text, r"loadNow\s*:\s*true")
        self.assertIn("open-meteo.com", text)
        self.assertIn("San Ramon", text)
        self.assertIn("UrlFetchApp.fetch", text)
        self.assertIn("HtmlService.createHtmlOutput", text)
        self.assertIn("temperature_2m", text)
        for line in text.splitlines():
            if re.match(r"^\s*function\s+doGet\b", line):
                self.fail(f"top-level doGet forbidden: {line!r}")

    def test_appsscript(self) -> None:
        data = json.loads((ROOT / "appsscript.json").read_text(encoding="utf-8"))
        self.assertIn("timeZone", data)
        scopes = data.get("oauthScopes") or []
        self.assertTrue(any("script.external_request" in s for s in scopes))

if __name__ == "__main__":
    unittest.main()
PY
}

prepare_clean_live_repo() {
  # Fresh tests-only tree so the engine must implement (not already_satisfied).
  mkdir -p "$repo"
  if [[ ! -d "$repo/.git" ]]; then
    git -C "$repo" init
    git -C "$repo" config user.email "devloop-e2e@example.com"
    git -C "$repo" config user.name "DevLoop E2E"
  fi
  # Remove prior product files so LIVE=1 cannot green on stale artifacts alone.
  rm -f "$repo/common-js/weather.gs" "$repo/appsscript.json"
  mkdir -p "$repo/tests" "$repo/common-js"
  write_offline_contract_tests
  printf '# GAS weather (DevLoop e2e)\n' >"$repo/README.md"
  # Clean git index of removed product files
  git -C "$repo" add -A
  if ! git -C "$repo" diff --cached --quiet 2>/dev/null || ! git -C "$repo" diff --quiet 2>/dev/null; then
    git -C "$repo" commit -m "native-test: tests-only base for live weather DoD" --allow-empty 2>/dev/null \
      || git -C "$repo" commit -m "native-test: tests-only base for live weather DoD"
  fi
  # Ensure working tree has no weather.gs (engine must create)
  rm -f "$repo/common-js/weather.gs" "$repo/appsscript.json"
  git -C "$repo" checkout -- tests/test_weather_contract.py README.md 2>/dev/null || true
}

engine_exit=1
engine_json="$scratch_default/devloop-weather-engine.json"

if [[ "$live" == "1" ]]; then
  prepare_clean_live_repo
  echo "=== live engine invoke via devloop-run ===" | tee -a "$log"
  export HERMES_BIN="$shim"
  export DEVLOOP_HOST="${DEVLOOP_HOST:-auto}"
  export DEVLOOP_TRANSPORT=hermes
  export DEVLOOP_HOME="$engine"
  export DEVLOOP_ALLOW_LEGACY_ENGINE=1
  export GROK_BIN="${GROK_BIN:-$(command -v grok || true)}"
  # Design-time judges call HERMES_BIN without cwd=target; pin the e2e repo so the
  # ollama-hermes-shim can resolve tests/test_weather_contract.py for structural YES.
  export DEVLOOP_WEATHER_REPO="$repo"
  export DEVLOOP_REPO="$repo"
  export DEVLOOP_TARGET="${DEVLOOP_TARGET:-$repo}"
  export DEVLOOP_WRITE_SAFE_ROOT="${DEVLOOP_WRITE_SAFE_ROOT:-$scratch_default/write-safe-native}"
  mkdir -p "$DEVLOOP_WRITE_SAFE_ROOT"
  # Five distinct models for assert_distinct_models (coder/designer/judges/tiebreaker).
  # Prefer relatively small local tags; OLLAMA_JUDGE_MODEL forces design-time judge speed.
  export DEVLOOP_PLANNER="${DEVLOOP_PLANNER:-qwen3:1.7b}"
  export DEVLOOP_DESIGNER="${DEVLOOP_DESIGNER:-phi4-mini:3.8b}"
  export DEVLOOP_CODER="${DEVLOOP_CODER:-gemma4:e4b}"
  export DEVLOOP_JUDGE_A="${DEVLOOP_JUDGE_A:-devstral-small-2:24b}"
  export DEVLOOP_JUDGE_B="${DEVLOOP_JUDGE_B:-qwen3.6:27b-nvfp4}"
  export DEVLOOP_TIEBREAKER="${DEVLOOP_TIEBREAKER:-gemma4:26b-mxfp8}"
  export DEVLOOP_ADVISOR="${DEVLOOP_ADVISOR:-phi4-mini:3.8b}"
  export OLLAMA_JUDGE_MODEL="${OLLAMA_JUDGE_MODEL:-qwen3:1.7b}"

  set +e
  bash "$run" -- \
    --repo "$repo" \
    --lang command \
    --json \
    --timeout "${DEVLOOP_WEATHER_TIMEOUT_S:-2400}" \
    "Create a small Google Apps Script weather web app for San Ramon CA. Files: common-js/weather.gs (Open-Meteo open-meteo.com, UrlFetchApp, temperature_2m, HtmlService, CommonJS module.exports.__events__ doGet:handleGet, loadNow true, no top-level function doGet) and appsscript.json with oauthScopes including script.external_request. Acceptance: regression_cmd is exactly the argv list python3 -m unittest discover -s tests -v (expected_exit 0). tests/test_weather_contract.py already defines the offline contract." \
    2>&1 | tee -a "$log" | tee "$engine_json"
  engine_exit=${PIPESTATUS[0]}
  set -e
  echo "engine_exit=$engine_exit" | tee -a "$log"

  # LIVE=1 success requires real engine terminal contract
  if [[ "$engine_exit" -ne 0 ]]; then
    fail "LIVE=1 requires engine exit 0 (got $engine_exit); see $log"
  fi
  if ! grep -q '"delivery_accepted": true' "$log" && ! grep -q '"delivery_accepted": true' "$engine_json" 2>/dev/null; then
    fail "LIVE=1 requires delivery_accepted true in engine JSON output"
  fi
  if ! grep -qE '"terminal": "COMPLETE"|terminal.: .COMPLETE' "$log" "$engine_json" 2>/dev/null; then
    # JSON may escape; also accept COMPLETE string in content
    if ! grep -q 'delivery_accepted": true' "$log"; then
      fail "LIVE=1 requires COMPLETE terminal / delivery_accepted"
    fi
  fi
  [[ -f "$repo/common-js/weather.gs" ]] || fail "LIVE=1 engine did not produce common-js/weather.gs"
  [[ -f "$repo/appsscript.json" ]] || fail "LIVE=1 engine did not produce appsscript.json"
else
  echo "=== live engine skipped (DEVLOOP_LIVE_WEATHER=$live) hermetic wiring ===" | tee -a "$log"
  write_offline_contract_tests
  # Hermetic: require existing product files (from prior live or reference project)
  if [[ ! -f "$repo/common-js/weather.gs" ]]; then
    if [[ -f "$HOME/src/gas-weather-devloop/common-js/weather.gs" ]]; then
      mkdir -p "$repo/common-js"
      cp "$HOME/src/gas-weather-devloop/common-js/weather.gs" "$repo/common-js/weather.gs"
      cp "$HOME/src/gas-weather-devloop/appsscript.json" "$repo/appsscript.json"
      echo "hermetic_seeded_from=gas-weather-devloop" | tee -a "$log"
    else
      fail "hermetic mode needs existing weather.gs (run LIVE=1 first or seed project)"
    fi
  fi
  DEVLOOP_HOME="$engine" DEVLOOP_HOST=grok GROK_BIN="$(command -v grok)" \
    bash "$run" --host grok --probe --no-bootstrap 2>&1 | tee -a "$log"
  engine_exit=0
fi

# Real card activity
grep -E 'devloop-run: engine=|probe: DEVLOOP_HOME=|live engine invoke|delivery_accepted' "$log" >/dev/null \
  || fail "log does not show real devloop-run activity"

# Offline contract must pass on produced files
echo "=== offline weather contract ===" | tee -a "$log"
( cd "$repo" && python3 -m unittest discover -s tests -v ) 2>&1 | tee -a "$log"

printf '%s\n' "$repo" >"$scratch_default/weather-repo.path"
printf '%s\n' "$engine_exit" >"$scratch_default/engine.exit"
echo "devloop-gas-weather-native: PASS (live=$live engine_exit=$engine_exit repo=$repo)" | tee -a "$log"
exit 0
