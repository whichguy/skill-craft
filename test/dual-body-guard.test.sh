#!/usr/bin/env bash
# Fail if the monorepo ships a second body for one skill identity.
# - External pins: lennox-s40 → whichguy/lennox-s40 (standalone wins).
# - Plugin bundles: a member skill lives only inside its bundle. It must never
#   also be a skills/<leaf> (install.sh would install a duplicate) or get its
#   own plugins/<member> view. plugins/<name> exists only for a leaf or a
#   bundle name. skill-craft owns skill-interop, so no bundle may vendor it.
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

# Names that must not appear under skills/, bundles/ or plugins/ in this monorepo.
external_leaves=(lennox-s40)

for leaf in "${external_leaves[@]}"; do
  [[ ! -e "$root/skills/$leaf" ]] || fail "skills/$leaf must not exist (external SoT)"
  [[ ! -e "$root/bundles/$leaf" ]] || fail "bundles/$leaf must not exist (external SoT)"
  [[ ! -e "$packages/plugins/$leaf" ]] || fail "plugins/$leaf must not exist (external SoT)"
done

python3 - "$root" "$packages" "${external_leaves[@]}" <<'PY' || exit 1
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
plugins = Path(sys.argv[2]) / "plugins"
external = set(sys.argv[3:])
leaves = {path.parent.name for path in (root / "skills").glob("*/SKILL.md")}
bundles = {}
for declaration in sorted((root / "bundles").glob("*/bundle.json")):
    bundles[declaration.parent.name] = json.loads(declaration.read_text())["skills"]
if "backchain" not in bundles:
    sys.exit("dual-body-guard.test.sh: FAIL expected the vendored backchain bundle")

problems = []
for name, members in bundles.items():
    if name in leaves:
        problems.append(f"bundle {name} is also skills/{name}")
    for member in members:
        if member == "skill-interop":
            problems.append(f"bundle {name} must not vendor skill-interop (skill-craft owns it)")
        if member in external:
            problems.append(f"bundle {name} member {member} is an external pin")
        if member != name:
            if member in leaves or (root / "skills" / member).exists():
                problems.append(f"bundle {name} member {member} also exists as skills/{member}")
            if (plugins / member).exists():
                problems.append(f"bundle {name} member {member} has its own plugins/{member} view")
publishable = leaves | set(bundles)


def packaged(view):
    # Empty or noise-only remnants are harmless (same rule as sync --check).
    return any(
        path.is_file() and path.name != ".DS_Store" and path.suffix != ".pyc"
        and "__pycache__" not in path.parts
        for path in view.rglob("*")
    )


for view in sorted(plugins.iterdir()):
    if view.is_dir() and view.name not in publishable and packaged(view):
        problems.append(f"plugins/{view.name} has no skills/{view.name} or bundles/{view.name}")
if problems:
    sys.exit("dual-body-guard.test.sh: FAIL " + "; ".join(problems))
PY

printf 'dual-body-guard.test.sh: PASS\n'
