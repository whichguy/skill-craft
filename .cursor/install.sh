#!/usr/bin/env bash
# Cloud Agent install phase for skill-craft.
#
# This repo is a prompt-first, host-neutral skills monorepo. It has no compiled
# artifacts and no package-manager dependencies (the Node helper uses only the
# stdlib). The only durable setup is ensuring the system toolchain the hermetic
# suite and install.sh expect is present.
#
# Must be idempotent and non-interactive: it may run repeatedly and against a
# cached/partially-prepared VM, and it must terminate.
set -euo pipefail

log() { printf 'install: %s\n' "$*"; }

# rsync is optional for the repo (install.sh and scripts/sync-plugin-views.sh
# fall back to `cp -R -L`), but the ARCHITECTURE contract and CI's ubuntu-latest
# runner prefer the `rsync -aL` path. Install it best-effort so the preferred
# code path is exercised; never fail setup if it cannot be installed.
if ! command -v rsync >/dev/null 2>&1; then
  log "rsync missing; attempting best-effort install"
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -qq \
      && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq rsync \
      || log "rsync install failed; continuing with cp fallback"
  else
    log "no apt-get; continuing with cp fallback"
  fi
else
  log "rsync already present ($(rsync --version | head -1))"
fi

# Verify the required, non-optional toolchain. These are provided by the base
# image; fail loudly if any is missing so the failure is attributed correctly.
missing=0
for tool in bash git node python3 jq; do
  if command -v "$tool" >/dev/null 2>&1; then
    log "found $tool -> $(command -v "$tool")"
  else
    log "MISSING required tool: $tool"
    missing=1
  fi
done
if [[ "$missing" -ne 0 ]]; then
  log "required toolchain incomplete"
  exit 1
fi

# Test and script files ship executable; normalize the bit so a fresh checkout
# on any filesystem can invoke them directly. Idempotent.
chmod +x install.sh 2>/dev/null || true
chmod +x scripts/*.sh scripts/*.js 2>/dev/null || true
chmod +x test/*.sh 2>/dev/null || true

log "done"
