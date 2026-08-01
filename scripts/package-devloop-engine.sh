#!/usr/bin/env bash
# Package a sanitized devloop engine tree into a versioned .tar.gz + .sha256
#
# Usage:
#   ./scripts/package-devloop-engine.sh --from DIR --version 0.1.0 [--out DIR]
#
# Excludes: .venv, __pycache__, .devloop, .git, caches, *.pyc
set -euo pipefail

from=""
version=""
out_dir=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from) from="$2"; shift 2 ;;
    --version) version="$2"; shift 2 ;;
    --out) out_dir="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *) printf 'unknown arg: %s\n' "$1" >&2; exit 64 ;;
  esac
done

[[ -n "$from" && -d "$from" ]] || { printf 'need --from DIR\n' >&2; exit 64; }
[[ -n "$version" ]] || { printf 'need --version X.Y.Z\n' >&2; exit 64; }
[[ -f "$from/scripts/devloop_cli.py" ]] || {
  printf 'not an engine root (missing scripts/devloop_cli.py): %s\n' "$from" >&2
  exit 1
}

from="$(cd "$from" && pwd -P)"
root="$(cd "$(dirname "$0")/.." && pwd -P)"
out_dir="${out_dir:-$root/dist}"
mkdir -p "$out_dir"
out_dir="$(cd "$out_dir" && pwd -P)"

stage="$(mktemp -d "${TMPDIR:-/tmp}/devloop-engine-pkg.XXXXXX")"
cleanup() { rm -rf "$stage"; }
trap cleanup EXIT

# Copy with excludes (rsync preferred)
if command -v rsync >/dev/null 2>&1; then
  rsync -a \
    --exclude '.venv/' \
    --exclude '__pycache__/' \
    --exclude '.devloop/' \
    --exclude '.git/' \
    --exclude '.mypy_cache/' \
    --exclude '.pytest_cache/' \
    --exclude '.ruff_cache/' \
    --exclude '*.pyc' \
    --exclude '.DS_Store' \
    "$from"/ "$stage"/
else
  cp -R "$from"/. "$stage"/
  rm -rf "$stage/.venv" "$stage/__pycache__" "$stage/.devloop" "$stage/.git" \
    "$stage/.mypy_cache" "$stage/.pytest_cache" "$stage/.ruff_cache" 2>/dev/null || true
  find "$stage" -name '*.pyc' -delete 2>/dev/null || true
fi

# Top-level directory name inside tarball for strip-friendly extract
inner="devloop-engine-${version}"
bundle="$(mktemp -d "${TMPDIR:-/tmp}/devloop-engine-bundle.XXXXXX")"
mkdir -p "$bundle/$inner"
# move stage contents into named root
shopt -s dotglob nullglob
mv "$stage"/* "$bundle/$inner"/ 2>/dev/null || true
shopt -u dotglob nullglob

tgz="$out_dir/devloop-engine-${version}.tar.gz"
# portable tar (disable macOS AppleDouble resource forks in archives)
(
  cd "$bundle"
  COPYFILE_DISABLE=1 tar -czf "$tgz" "$inner"
)

sha="$(shasum -a 256 "$tgz" | awk '{print $1}')"
printf '%s  %s\n' "$sha" "$(basename "$tgz")" >"${tgz}.sha256"

printf 'package: %s\n' "$tgz"
printf 'sha256: %s\n' "$sha"
printf 'size:   %s\n' "$(wc -c <"$tgz" | tr -d ' ')"

# Emit pin fragment for convenience
pin="$out_dir/engine-pin-${version}.json"
python3 - "$version" "$sha" "$(basename "$tgz")" "$pin" <<'PY'
import json, sys
version, sha, name, out = sys.argv[1:5]
# URL filled later by release step; file:// for local pin override in tests
d = {
    "version": version,
    "url": f"REPLACE_WITH_RELEASE_URL/{name}",
    "sha256": sha,
    "tarball": name,
}
json.dump(d, open(out, "w"), indent=2)
open(out, "a").write("\n")
print("pin_fragment", out)
PY

rm -rf "$bundle"
trap - EXIT
rm -rf "$stage"
