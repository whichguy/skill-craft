#!/usr/bin/env bash
# Explicit optional integrations.  This entrypoint is intentionally absent from
# default CI; list/help are host-independent and selected checks fail closed.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

usage() {
  cat <<'EOF'
Usage: test/run-integration.sh <command>

Optional commands (never part of default CI):
  list, --list       List available optional integrations.
  help, --help, -h   Show this help without checking host prerequisites.
  weather-offline    Validate the weather project through a local DevLoop probe.
  weather-live       Run the explicitly selected live weather integration.
  cursor-imports     Verify imported Cursor skills are available on this host.
  marketplace-claude  Install local candidate plugins in a disposable Claude profile.
  marketplace-grok    Install local candidate plugins in a disposable Grok profile.
  marketplace-codex   Install local candidate plugins in a disposable Codex profile.

weather-* requires DEVLOOP_HOME and DEVLOOP_WEATHER_REPO. weather-live is the
only command that can enter the live weather path; it sets the mode itself.
EOF
}

require_weather_environment() {
  local missing=0 name
  for name in DEVLOOP_HOME DEVLOOP_WEATHER_REPO; do
    if [[ -z "${!name:-}" ]]; then
      printf 'run-integration: %s is required for weather integrations\n' "$name" >&2
      missing=1
    fi
  done
  [[ "$missing" == "0" ]] || exit 2
}

case "${1:-list}" in
  list|--list|help|--help|-h)
    [[ "$#" == "0" || "$#" == "1" ]] || { usage >&2; exit 64; }
    usage
    ;;
  weather-offline)
    [[ "$#" == "1" ]] || { usage >&2; exit 64; }
    require_weather_environment
    DEVLOOP_LIVE_WEATHER=0 exec bash "$root/test/devloop-gas-weather-native.test.sh"
    ;;
  weather-live)
    [[ "$#" == "1" ]] || { usage >&2; exit 64; }
    require_weather_environment
    DEVLOOP_LIVE_WEATHER=1 exec bash "$root/test/devloop-gas-weather-native.test.sh"
    ;;
  cursor-imports)
    [[ "$#" == "1" ]] || { usage >&2; exit 64; }
    exec bash "$root/test/cursor-imported-skills.test.sh"
    ;;
  marketplace-claude|marketplace-grok|marketplace-codex)
    [[ "$#" == "1" ]] || { usage >&2; exit 64; }
    exec python3 "$root/test/marketplace-host-smoke.py" --host "${1#marketplace-}"
    ;;
  *)
    printf 'run-integration: unknown command %q\n' "$1" >&2
    usage >&2
    exit 64
    ;;
esac
