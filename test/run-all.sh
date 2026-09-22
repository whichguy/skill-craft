#!/usr/bin/env bash
# Stable public entrypoint for the declarative hermetic suite catalog.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"
exec python3 -B test/run_suites.py "$@"
