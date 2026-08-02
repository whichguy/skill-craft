#!/usr/bin/env bash
# Package a sanitized devloop engine tree into a versioned .tar.gz + .sha256
#
# Usage:
#   ./scripts/package-devloop-engine.sh --from DIR --version 0.1.1 [--out DIR]
#
# Excludes: .venv, __pycache__, .devloop, .git, caches, *.pyc, and known path-leaking
# reference docs. After stage: deny-check fails on host-absolute paths / home PII.
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
# Also drop known path-leaking reference docs from Hermes export trees.
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
    --exclude 'references/archive-verification.md' \
    --exclude 'references/prompt-iteration-loop.md' \
    --exclude 'references/retirement-readiness-2026-06-30.md' \
    "$from"/ "$stage"/
else
  cp -R "$from"/. "$stage"/
  rm -rf "$stage/.venv" "$stage/__pycache__" "$stage/.devloop" "$stage/.git" \
    "$stage/.mypy_cache" "$stage/.pytest_cache" "$stage/.ruff_cache" 2>/dev/null || true
  rm -f "$stage/references/archive-verification.md" \
    "$stage/references/prompt-iteration-loop.md" \
    "$stage/references/retirement-readiness-2026-06-30.md" 2>/dev/null || true
  find "$stage" -name '*.pyc' -delete 2>/dev/null || true
fi

# Deny-check: no host-absolute paths / home PII / hermes profile tree in file *contents*
# (text files only; binary skipped). Exit 1 on first hit.
python3 - "$stage" <<'PY'
import os, re, sys

root = sys.argv[1]
# Patterns that must not appear in a public engine release
PATTERNS = [
    re.compile(r"/Users/[A-Za-z0-9._-]+"),
    re.compile(r"/home/[A-Za-z0-9._-]+"),
    re.compile(r"\.hermes/profiles/"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
]
# Skip binary-ish extensions
SKIP_EXT = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".pdf", ".zip", ".tgz", ".gz"}

hits = []
for dirpath, _, files in os.walk(root):
    for name in files:
        path = os.path.join(dirpath, name)
        ext = os.path.splitext(name)[1].lower()
        if ext in SKIP_EXT:
            continue
        try:
            data = open(path, "rb").read(2_000_000)
        except OSError:
            continue
        if b"\0" in data[:4096]:
            continue
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            continue
        for pat in PATTERNS:
            m = pat.search(text)
            if m:
                rel = os.path.relpath(path, root)
                hits.append("%s: %s" % (rel, m.group(0)[:80]))
                break

if hits:
    sys.stderr.write("package-devloop-engine: deny-check FAILED (%d hit(s))\n" % len(hits))
    for h in hits[:30]:
        sys.stderr.write("  %s\n" % h)
    if len(hits) > 30:
        sys.stderr.write("  ... +%d more\n" % (len(hits) - 30))
    sys.stderr.write("  Scrub host paths / PII before packaging, or exclude leaking files.\n")
    sys.exit(1)
sys.stderr.write("package-devloop-engine: deny-check OK\n")
PY

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
