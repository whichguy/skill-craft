#!/usr/bin/env bash
# Fail if the monorepo ships a second body for one skill identity.
# - External pins: lennox-s40 → whichguy/lennox-s40 (standalone wins).
# - Every skill ships in the one plugins/skill-craft bundle; no other
#   plugins/<name> directory may carry packaged content.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
fail() { printf 'dual-body-guard.test.sh: FAIL %s\n' "$*" >&2; exit 1; }

# plugins/ is release output; check a build of the current source instead.
packages="${SKILL_CRAFT_PACKAGES:-}"
if [[ -z "$packages" ]]; then
  build_parent="$(mktemp -d "${TMPDIR:-/tmp}/dual-body-guard.XXXXXX")"
  trap 'rm -rf "$build_parent"' EXIT
  python3 -B "$root/scripts/build-packages.py" "$build_parent/build" >/dev/null
  packages="$build_parent/build"
fi

# Names that must not appear under skills/ or plugins/ in this monorepo.
external_leaves=(lennox-s40)

for leaf in "${external_leaves[@]}"; do
  [[ ! -e "$root/skills/$leaf" ]] || fail "skills/$leaf must not exist (external SoT)"
  [[ ! -e "$packages/plugins/$leaf" ]] || fail "plugins/$leaf must not exist (external SoT)"
  [[ ! -e "$packages/plugins/skill-craft/skills/$leaf" ]] || fail "plugins/skill-craft/skills/$leaf must not exist (external SoT)"
done

python3 - "$packages" <<'PY' || exit 1
import sys
from pathlib import Path

plugins = Path(sys.argv[1]) / "plugins"
plugin_name = "skill-craft"


def packaged(view):
    # Empty or noise-only remnants are harmless (same rule as sync --check).
    return any(
        path.is_file() and path.name != ".DS_Store" and path.suffix != ".pyc"
        and "__pycache__" not in path.parts
        for path in view.rglob("*")
    )


problems = [
    f"plugins/{view.name} is a second body; every skill ships in plugins/{plugin_name}"
    for view in sorted(plugins.iterdir())
    if view.is_dir() and view.name != plugin_name and packaged(view)
]
if problems:
    sys.exit("dual-body-guard.test.sh: FAIL " + "; ".join(problems))
PY

printf 'dual-body-guard.test.sh: PASS\n'
