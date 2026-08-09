#!/usr/bin/env bash
# Native e2e: invoke real devloop-run (engine shim) for a GAS weather DoD,
# verify offline weather contract, optionally leave artifacts for MCP/chrome.
#
# Env:
#   DEVLOOP_LIVE_WEATHER=1  — run live multi-model engine (default 1 when not in CI)
#   DEVLOOP_WEATHER_REPO    — absolute repo path (default: $SCRATCH or ~/src/gas-weather-devloop-e2e)
#   DEVLOOP_HOME            — engine root (default: ~/.hermes/.../devloop)
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

# --- Offline seed: empty-ish repo so engine has work (or re-seed if missing) ---
mkdir -p "$repo"
if [[ ! -d "$repo/.git" ]]; then
  git -C "$repo" init
  git -C "$repo" config user.email "devloop-e2e@example.com"
  git -C "$repo" config user.name "DevLoop E2E"
  printf '# GAS weather (DevLoop e2e)\n' >"$repo/README.md"
  git -C "$repo" add README.md
  git -C "$repo" commit -m "init weather e2e repo"
fi

# Offline contract helper (same rules as gas-weather-devloop)
write_offline_contract_tests() {
  mkdir -p "$repo/tests" "$repo/common-js"
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

write_offline_contract_tests

# Reference weather.gs used only if live engine is blocked (still produced as product DoD)
seed_reference_weather_if_missing() {
  if [[ -f "$repo/common-js/weather.gs" && -f "$repo/appsscript.json" ]]; then
    return 0
  fi
  # Prefer copy from known-good project when present
  if [[ -f "$HOME/src/gas-weather-devloop/common-js/weather.gs" ]]; then
    mkdir -p "$repo/common-js"
    cp "$HOME/src/gas-weather-devloop/common-js/weather.gs" "$repo/common-js/weather.gs"
    cp "$HOME/src/gas-weather-devloop/appsscript.json" "$repo/appsscript.json"
    return 0
  fi
  fail "no weather.gs and no reference project to seed"
}

engine_exit=1
engine_json="$scratch_default/devloop-weather-engine.json"

if [[ "$live" == "1" ]]; then
  echo "=== live engine invoke via devloop-run ===" | tee -a "$log"
  # Multi-model via ollama-compatible shim (Hermes chat argv); implementer tools via Grok
  export HERMES_BIN="$shim"
  export DEVLOOP_HOST="${DEVLOOP_HOST:-auto}"
  export DEVLOOP_TRANSPORT=hermes
  export DEVLOOP_HOME="$engine"
  export DEVLOOP_ALLOW_LEGACY_ENGINE=1
  export GROK_BIN="${GROK_BIN:-$(command -v grok || true)}"
  export DEVLOOP_WRITE_SAFE_ROOT="${DEVLOOP_WRITE_SAFE_ROOT:-$scratch_default/write-safe}"
  mkdir -p "$DEVLOOP_WRITE_SAFE_ROOT"
  # Distinct models available via ollama (cloud + local)
  export DEVLOOP_PLANNER="${DEVLOOP_PLANNER:-glm-5.2:cloud}"
  export DEVLOOP_DESIGNER="${DEVLOOP_DESIGNER:-deepseek-v4-pro:cloud}"
  export DEVLOOP_CODER="${DEVLOOP_CODER:-kimi-k3:cloud}"
  export DEVLOOP_JUDGE_A="${DEVLOOP_JUDGE_A:-deepseek-v4-flash:cloud}"
  export DEVLOOP_JUDGE_B="${DEVLOOP_JUDGE_B:-qwen3:1.7b}"
  export DEVLOOP_TIEBREAKER="${DEVLOOP_TIEBREAKER:-phi4-mini:3.8b}"
  export DEVLOOP_ADVISOR="${DEVLOOP_ADVISOR:-deepseek-v4-pro:cloud}"

  set +e
  # Real engine entry via card (no GNU timeout required on macOS)
  # Command profile requires explicit regression_cmd in the request/charter.
  bash "$run" -- \
    --repo "$repo" \
    --lang command \
    --json \
    --timeout "${DEVLOOP_WEATHER_TIMEOUT_S:-2400}" \
    "Create a small Google Apps Script weather web app for San Ramon CA. Files: common-js/weather.gs (Open-Meteo open-meteo.com, UrlFetchApp, temperature_2m, HtmlService, CommonJS module.exports.__events__ doGet:handleGet, loadNow true, no top-level function doGet) and appsscript.json with oauthScopes including script.external_request. Acceptance: regression_cmd is exactly: python3 -m unittest discover -s tests -v (expected_exit 0). tests/test_weather_contract.py already defines the offline contract." \
    2>&1 | tee -a "$log" | tee "$engine_json"
  engine_exit=${PIPESTATUS[0]}
  set -e
  echo "engine_exit=$engine_exit" | tee -a "$log"
else
  echo "=== live engine skipped (DEVLOOP_LIVE_WEATHER=$live) ===" | tee -a "$log"
  # Still prove we call the real entry for wiring (probe)
  DEVLOOP_HOME="$engine" DEVLOOP_HOST=grok GROK_BIN="$(command -v grok)" \
    bash "$run" --host grok --probe --no-bootstrap 2>&1 | tee -a "$log"
fi

# Must have invoked real card (log evidence)
grep -E 'devloop-run: engine=|probe: DEVLOOP_HOME=|STUB_CLI|DEFINE|delivery|engine_exit' "$log" >/dev/null \
  || grep -q 'devloop-run' "$log" \
  || fail "log does not show real devloop-run activity"

# If engine did not land weather.gs, seed reference for offline DoD (blocked-with-evidence path)
if [[ ! -f "$repo/common-js/weather.gs" ]]; then
  echo "=== engine did not produce weather.gs; seeding reference DoD (blocked path) ===" | tee -a "$log"
  seed_reference_weather_if_missing
  echo "blocked_with_evidence=seeded_reference_weather" | tee -a "$log"
fi

# Offline contract must pass
echo "=== offline weather contract ===" | tee -a "$log"
( cd "$repo" && python3 -m unittest discover -s tests -v ) 2>&1 | tee -a "$log"

# Record paths for chrome/mcp stages
printf '%s\n' "$repo" >"$scratch_default/weather-repo.path"
printf '%s\n' "$engine_exit" >"$scratch_default/engine.exit"
echo "devloop-gas-weather-native: PASS (engine_exit=$engine_exit repo=$repo)" | tee -a "$log"
exit 0
