#!/usr/bin/env bash
# Operator-only provisioning for a separately distributed DevLoop engine.
# This script intentionally lives outside skills/devloop so marketplace-loaded
# skill code cannot fetch, install, or execute an operator override.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
default_pin="$root/scripts/devloop-engine-pin.json"

usage() {
  cat <<'EOF'
Usage: scripts/devloop-setup.sh [flags]

Operator-only: verify and materialize a DevLoop engine outside a marketplace
skill package. Never invoke this script automatically from a loaded skill.

Flags:
  --host NAME          grok|hermes|claude|codex|cursor|auto (default: auto)
  --pin FILE           Engine pin JSON (default: scripts/devloop-engine-pin.json)
  --data-home DIR      Parent for DIR/devloop (default: XDG data / ~/.local/share)
  --force              Re-materialize an owned host-local engine
  --force-hard         With --force, replace an unmarked engine tree
  --allow-hermes-seed  Permit an installed Hermes engine as an offline seed

Environment (operator input only):
  DEVLOOP_ENGINE_PIN, DEVLOOP_DATA_HOME, DEVLOOP_ENGINE_URL,
  DEVLOOP_ENGINE_SHA256, DEVLOOP_BOOTSTRAP_CMD, DEVLOOP_HOST,
  DEVLOOP_ALLOW_HERMES_SEED, HERMES_HOME.

The pin URL must be accompanied by a SHA-256 for https downloads. A file://
URL may be used for an air-gapped verified archive. The result is an owned
host-local engine at DATA_HOME/devloop; it never overwrites Hermes' skill leaf.
The selected engine interpreter must already provide pytest; this operator
script verifies dependencies and the CLI import surface but never installs them.
EOF
}

host="${DEVLOOP_HOST:-auto}"
pin_file="${DEVLOOP_ENGINE_PIN:-$default_pin}"
data_home="${DEVLOOP_DATA_HOME:-${XDG_DATA_HOME:-${HOME}/.local/share}}"
force=0
force_hard=0
allow_hermes_seed="${DEVLOOP_ALLOW_HERMES_SEED:-0}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --host)
      host="${2:-}"
      [[ -n "$host" ]] || { printf 'devloop-setup: --host requires NAME\n' >&2; exit 64; }
      shift 2
      ;;
    --pin)
      pin_file="${2:-}"
      [[ -n "$pin_file" ]] || { printf 'devloop-setup: --pin requires FILE\n' >&2; exit 64; }
      shift 2
      ;;
    --data-home)
      data_home="${2:-}"
      [[ -n "$data_home" ]] || { printf 'devloop-setup: --data-home requires DIR\n' >&2; exit 64; }
      shift 2
      ;;
    --force|--force-bootstrap) force=1; shift ;;
    --force-hard) force_hard=1; shift ;;
    --allow-hermes-seed) allow_hermes_seed=1; shift ;;
    *) printf 'devloop-setup: unknown option: %s\n' "$1" >&2; usage >&2; exit 64 ;;
  esac
done

case "$host" in
  grok|hermes|claude|codex|cursor|auto) ;;
  *) printf 'devloop-setup: unsupported host: %s\n' "$host" >&2; exit 64 ;;
esac
if [[ "$force_hard" -eq 1 && "$force" -eq 0 ]]; then
  printf 'devloop-setup: --force-hard requires --force\n' >&2
  exit 64
fi

require_python3() {
  if command -v python3 >/dev/null 2>&1; then
    return 0
  fi
  printf 'devloop-setup: python3 is required for verified extraction and marker creation.\n' >&2
  exit 2
}

is_engine_root() {
  local dir="$1"
  [[ -n "$dir" && -d "$dir" && -f "$dir/scripts/devloop_cli.py" ]]
}

# This is deliberately the same preference order as the distributed runtime.
# Archives normally omit .venv, but an operator-owned bootstrap source may
# supply one. Do not replace missing dependencies with an installer here.
select_engine_python() {
  local engine_root="$1"
  if [[ -x "$engine_root/.venv/bin/python3" ]]; then
    printf '%s\n' "$engine_root/.venv/bin/python3"
    return 0
  fi
  command -v python3
}

verify_engine_runtime() {
  local engine_root="$1"
  local engine_python
  if ! engine_python="$(select_engine_python "$engine_root")"; then
    printf 'devloop-setup: no usable Python interpreter for staged engine at %s\n' "$engine_root" >&2
    return 1
  fi
  # The prior runtime used `uv run --with pytest`; pytest is therefore a known
  # current engine dependency and must be supplied by the operator environment.
  if ! "$engine_python" -c 'import pytest'; then
    printf 'devloop-setup: selected engine interpreter lacks required pytest dependency.\n' >&2
    return 1
  fi
  if ! "$engine_python" "$engine_root/scripts/devloop_cli.py" --help >/dev/null; then
    printf 'devloop-setup: staged engine CLI import/--help preflight failed.\n' >&2
    return 1
  fi
}

read_pin() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    printf '|||\n'
    return 0
  fi
  python3 - "$file" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    print("|||")
    raise SystemExit(0)
print("%s|%s|%s|%s" % (
    data.get("version") or "",
    data.get("url") or "",
    data.get("sha256") or "",
    ",".join(str(item) for item in data["transports"])
    if isinstance(data.get("transports"), list) else "",
))
PY
}

sha256_file() {
  if ! command -v shasum >/dev/null 2>&1; then
    printf 'devloop-setup: shasum is required to verify the engine archive.\n' >&2
    return 1
  fi
  shasum -a 256 "$1" | awk '{print $1}'
}

safe_extract_tgz() {
  local archive="$1"
  local dest="$2"
  python3 - "$archive" "$dest" <<'PY'
import os, shutil, sys, tarfile

archive, dest = sys.argv[1], sys.argv[2]
dest = os.path.realpath(dest)
os.makedirs(dest, exist_ok=True)

def safe_member(name: str) -> bool:
    if name.startswith(("/", "\\")):
        return False
    return ".." not in name.replace("\\", "/").split("/")

with tarfile.open(archive, "r:gz") as tf:
    members = tf.getmembers()
    for member in members:
        if not safe_member(member.name):
            sys.stderr.write(f"devloop-setup: refused unsafe tar member: {member.name}\n")
            raise SystemExit(2)
        if not (member.isdir() or member.isfile()):
            sys.stderr.write(
                f"devloop-setup: refused non-file tar member: {member.name}\n"
            )
            raise SystemExit(2)
    if hasattr(tarfile, "data_filter"):
        tf.extractall(dest, filter="data")
    else:
        # Python versions before data_filter need an explicit conservative
        # extractor. Every member was checked above, so this never materializes
        # symlinks, hard links, FIFOs, devices, or other special file types.
        for member in members:
            target = os.path.join(dest, *member.name.replace("\\", "/").split("/"))
            if member.isdir():
                os.makedirs(target, mode=member.mode, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            source = tf.extractfile(member)
            if source is None:
                sys.stderr.write(
                    f"devloop-setup: could not read tar file member: {member.name}\n"
                )
                raise SystemExit(2)
            with source, open(target, "wb") as output:
                shutil.copyfileobj(source, output)
            os.chmod(target, member.mode)

entry = os.path.join(dest, "scripts", "devloop_cli.py")
if not os.path.isfile(entry):
    for name in os.listdir(dest):
        if name.startswith("._"):
            continue
        top = os.path.join(dest, name)
        if not (os.path.isdir(top) and os.path.isfile(os.path.join(top, "scripts", "devloop_cli.py"))):
            continue
        for child in os.listdir(top):
            if not child.startswith("._"):
                os.rename(os.path.join(top, child), os.path.join(dest, child))
        try:
            os.rmdir(top)
        except OSError:
            pass
        break
PY
}

download_url_to() {
  local url="$1"
  local out="$2"
  if [[ "$url" == file://* ]]; then
    local path="${url#file://}"
    [[ "$path" == /* ]] || path="/$path"
    if [[ -f "$path" ]]; then
      cp "$path" "$out"
      return 0
    fi
    printf 'devloop-setup: file URL not found: %s\n' "$url" >&2
    return 1
  fi
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --progress-bar "$url" -o "$out"
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$out" "$url"
  else
    printf 'devloop-setup: need curl or wget to fetch the verified engine archive.\n' >&2
    return 1
  fi
}

write_engine_marker() {
  local engine_root="$1"
  local source="$2"
  local version="$3"
  local sha="$4"
  local timestamp
  timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"
  python3 - "$engine_root/.skill-craft-engine.json" "$source" "$version" "$sha" "$timestamp" <<'PY'
import json, sys
path, source, version, sha, timestamp = sys.argv[1:6]
data = {"schema": 1, "mode": "host-local", "source": source,
        "version": version, "timestamp": timestamp}
if sha:
    data["sha256"] = sha
with open(path, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
    handle.write("\n")
PY
}

validate_destination() {
  local dest="$1"
  [[ "$(basename "$dest")" == "devloop" && "$dest" != "/devloop" ]] || {
    printf 'devloop-setup: unsafe host-local destination: %s\n' "$dest" >&2
    exit 64
  }
}

require_python3
destination="$data_home/devloop"
validate_destination "$destination"
parent="$(dirname "$destination")"
mkdir -p "$parent"

if [[ "$force" -eq 0 ]] && is_engine_root "$destination"; then
  if ! verify_engine_runtime "$destination"; then
    printf 'devloop-setup: existing engine failed dependency/CLI preflight; re-run --force after repairing its interpreter.\n' >&2
    exit 2
  fi
  printf 'devloop-setup: engine already present and preflight-valid at %s\n' "$destination"
  exit 0
fi
if [[ "$force" -eq 1 && -e "$destination" && ! -f "$destination/.skill-craft-engine.json" && "$force_hard" -eq 0 ]]; then
  printf 'devloop-setup: refusing --force on unmarked engine at %s\n' "$destination" >&2
  printf '  Re-run with --force-hard only after confirming ownership.\n' >&2
  exit 2
fi

lock_dir="$parent/devloop.bootstrap.lock.d"
attempt=0
while ! mkdir "$lock_dir" 2>/dev/null; do
  attempt=$((attempt + 1))
  if [[ "$attempt" -gt 200 ]]; then
    printf 'devloop-setup: timeout waiting for provisioning lock\n' >&2
    exit 2
  fi
  sleep 0.05
done
cleanup_lock() { rmdir "$lock_dir" 2>/dev/null || true; }
trap cleanup_lock EXIT

if [[ "$force" -eq 0 ]] && is_engine_root "$destination"; then
  if ! verify_engine_runtime "$destination"; then
    printf 'devloop-setup: existing engine failed dependency/CLI preflight; re-run --force after repairing its interpreter.\n' >&2
    exit 2
  fi
  printf 'devloop-setup: engine already present and preflight-valid at %s\n' "$destination"
  exit 0
fi

stage="$parent/.devloop-stage.$$"
rm -rf "$stage"
mkdir -p "$stage"
cleanup_stage() { rm -rf "$stage"; }
trap 'cleanup_stage; cleanup_lock' EXIT

IFS='|' read -r pin_version pin_url pin_sha pin_transports <<<"$(read_pin "$pin_file")"
if [[ "$host" == "grok" && -n "$pin_transports" && ",$pin_transports," != *",grok,"* ]]; then
  printf 'devloop-setup: pin at %s declares transports without "grok" (%s).\n' "$pin_file" "$pin_transports" >&2
  exit 2
fi

url="${DEVLOOP_ENGINE_URL:-$pin_url}"
sha="${DEVLOOP_ENGINE_SHA256:-$pin_sha}"
version="${pin_version:-unknown}"
source_label=""

if [[ -n "${DEVLOOP_BOOTSTRAP_CMD:-}" ]]; then
  if ! "$DEVLOOP_BOOTSTRAP_CMD" "$stage"; then
    printf 'devloop-setup: DEVLOOP_BOOTSTRAP_CMD failed\n' >&2
    exit 2
  fi
  source_label="DEVLOOP_BOOTSTRAP_CMD"
elif [[ -n "$url" && "$url" != REPLACE_WITH_RELEASE_URL/* && "$url" != *REPLACE_WITH* ]]; then
  archive="$(mktemp "${TMPDIR:-/tmp}/devloop-engine.XXXXXX")"
  cleanup_archive() { rm -f "$archive"; cleanup_stage; cleanup_lock; }
  trap cleanup_archive EXIT
  if ! download_url_to "$url" "$archive"; then
    exit 2
  fi
  if [[ -z "$sha" && "$url" != file://* ]]; then
    printf 'devloop-setup: refusing network archive without SHA-256.\n' >&2
    exit 2
  fi
  if [[ -n "$sha" ]]; then
    got="$(sha256_file "$archive")" || exit 2
    if [[ "$got" != "$sha" ]]; then
      printf 'devloop-setup: sha256 mismatch\n  expected: %s\n  got:      %s\n' "$sha" "$got" >&2
      exit 2
    fi
  fi
  safe_extract_tgz "$archive" "$stage"
  source_label="$url"
else
  seed=""
  if [[ "$host" == "hermes" || "$allow_hermes_seed" == "1" ]]; then
    for candidate in \
      "${HERMES_HOME:+$HERMES_HOME/skills/software-development/devloop}" \
      "${HOME}/.hermes/skills/software-development/devloop" \
      "/opt/data/skills/software-development/devloop"; do
      [[ -n "$candidate" ]] || continue
      if is_engine_root "$candidate"; then
        seed="$candidate"
        break
      fi
    done
  fi
  if [[ -z "$seed" ]]; then
    printf 'devloop-setup: no verified pin/archive or allowed installed Hermes seed.\n' >&2
    printf '  Supply --pin FILE, DEVLOOP_ENGINE_URL + DEVLOOP_ENGINE_SHA256, or an allowed seed.\n' >&2
    exit 2
  fi
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete --exclude '.venv' --exclude '__pycache__' --exclude '.devloop' \
      --exclude '.git' --exclude '.mypy_cache' --exclude '.pytest_cache' \
      "$seed/" "$stage/"
  else
    cp -R "$seed/." "$stage/"
    rm -rf "$stage/.venv" "$stage/__pycache__" "$stage/.devloop" "$stage/.git" 2>/dev/null || true
  fi
  source_label="$seed"
  version="seeded"
  sha=""
fi

if ! is_engine_root "$stage"; then
  printf 'devloop-setup: provisioning source did not produce scripts/devloop_cli.py\n' >&2
  exit 2
fi
if ! verify_engine_runtime "$stage"; then
  printf 'devloop-setup: refusing to activate an engine that fails dependency/CLI preflight.\n' >&2
  printf '  Preinstall pytest and required engine dependencies in the selected interpreter, then retry.\n' >&2
  exit 2
fi
write_engine_marker "$stage" "$source_label" "$version" "$sha"

previous=""
if [[ -d "$destination" ]]; then
  previous="${destination}.prev.$$"
  rm -rf "$previous"
  if ! mv "$destination" "$previous"; then
    printf 'devloop-setup: failed to park previous engine at %s\n' "$previous" >&2
    exit 2
  fi
fi
if ! mv "$stage" "$destination"; then
  printf 'devloop-setup: failed to activate staged engine at %s\n' "$destination" >&2
  if [[ -n "$previous" && -d "$previous" ]]; then
    mv "$previous" "$destination" 2>/dev/null || true
  fi
  exit 2
fi
if [[ -n "$previous" && -d "$previous" ]]; then
  rm -rf "$previous"
fi
cleanup_lock
trap - EXIT
printf 'devloop-setup: engine activated at %s (pytest + CLI preflight passed)\n' "$destination"
