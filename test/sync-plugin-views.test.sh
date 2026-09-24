#!/usr/bin/env bash
# Plugin views must be real trees (not symlinks) matching skills/ SoT.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

# The cases below intentionally corrupt views and source fixtures. Re-run the
# same test in a disposable copy when invoked from a real checkout so no
# compatibility test can alter a collaborator's active tree.
if [[ "${SKILL_CRAFT_SYNC_FIXTURE:-}" != "1" ]]; then
  fixture_tmp="$(mktemp -d "${TMPDIR:-/tmp}/skill-craft-sync-test.XXXXXX")"
  fixture_root="$fixture_tmp/repo"
  cleanup_fixture() { rm -rf "$fixture_tmp"; }
  trap cleanup_fixture EXIT
  mkdir -p "$fixture_root"
  (cd "$root" && tar \
    --exclude='.git' \
    --exclude='.claude/worktrees' \
    --exclude='.ruff_cache' \
    --exclude='node_modules' \
    --exclude='.results' \
    --exclude='results' \
    --exclude='tasks' \
    --exclude='dist' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -cf - .) | (cd "$fixture_root" && tar -xf -)
  set +e
  SKILL_CRAFT_SYNC_FIXTURE=1 bash "$fixture_root/test/sync-plugin-views.test.sh"
  fixture_rc=$?
  set -e
  exit "$fixture_rc"
fi

cd "$root"

fail() {
  printf 'sync-plugin-views.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -x scripts/sync-plugin-views.sh ]] || fail "scripts/sync-plugin-views.sh not executable"
# plugins/ is release output; rebuild this fixture's views from source first.
bash scripts/sync-plugin-views.sh >/dev/null || fail "baseline sync"

# Leaf-only bytecode is not plugin-view drift (.gitignore already ignores it).
pyc_pin="skills/shiploop/scripts/__pycache__"
cleanup_pyc_pin() { rm -rf "$pyc_pin"; }
trap cleanup_pyc_pin EXIT
mkdir -p "$pyc_pin"
printf 'x' >"$pyc_pin/pin.pyc"
set +e
out_pyc="$(bash scripts/sync-plugin-views.sh --check shiploop 2>&1)"
rc_pyc=$?
set -e
cleanup_pyc_pin
trap - EXIT
[[ "$rc_pyc" -eq 0 ]] || fail "leaf-only __pycache__ should not fail --check: $out_pyc"

# Check mode must pass after regenerating
bash scripts/sync-plugin-views.sh --check || fail "plugin views out of sync or still symlinked"

# No symlinks under any plugins/*/skills or plugins/*/agents
if find plugins -type l 2>/dev/null | grep -q .; then
  fail "symlinks under plugins/ (Claude git-subdir cannot follow them): $(find plugins -type l | tr '\n' ' ')"
fi

# skill-interop SKILL.md present in plugin view
[[ -f plugins/skill-interop/skills/skill-interop/SKILL.md ]] || fail "missing materialised SKILL.md"
[[ -f plugins/skill-interop/agents/skill-interop.md ]] || fail "missing materialised agent card"
[[ -f plugins/skill-interop/.claude-plugin/plugin.json ]] || fail "missing plugin.json"

# plugin.json is derived from SKILL.md SoT (version/description/license)
node scripts/skill-frontmatter-to-plugin-json.js skill-interop --check \
  || fail "skill-interop plugin.json not derived from frontmatter"
node scripts/skill-frontmatter-to-plugin-json.js c-plan --check \
  || fail "c-plan plugin.json not derived from frontmatter"

# Default enumeration is skills/ — every skill leaf must have a plugin view after sync
[[ -f LICENSE ]] || fail "source root LICENSE missing"
for d in skills/*/; do
  n="$(basename "$d")"
  [[ -f "skills/$n/SKILL.md" ]] || continue
  [[ -f "plugins/$n/.claude-plugin/plugin.json" ]] || fail "missing plugin view for skills/$n"
  [[ -f "plugins/$n/.codex-plugin/plugin.json" ]] || fail "missing Codex manifest for skills/$n"
  [[ -f "plugins/$n/LICENSE" ]] || fail "missing package-root LICENSE for skills/$n"
  cmp -s LICENSE "plugins/$n/LICENSE" \
    || fail "package-root LICENSE drift for skills/$n"
  [[ -s "plugins/$n/README.md" ]] || fail "missing package-root README for skills/$n"
done

# --check fails on orphan plugins/<leaf> with no skills/<leaf>
orphan="plugins/_zz-orphan-sync-test_"
mkdir -p "$orphan/.claude-plugin"
printf '%s\n' '{"name":"_zz-orphan-sync-test_","version":"0.0.0","description":"orphan"}' \
  >"$orphan/.claude-plugin/plugin.json"
set +e
out_orphan="$(bash scripts/sync-plugin-views.sh --check 2>&1)"
rc_orphan=$?
set -e
rm -rf "$orphan"
[[ "$rc_orphan" -ne 0 ]] || fail "orphan plugin view should fail --check: $out_orphan"
printf '%s\n' "$out_orphan" | grep -qi 'orphan' || fail "orphan message missing: $out_orphan"
# suite still clean after cleanup
bash scripts/sync-plugin-views.sh --check || fail "check failed after orphan cleanup"

# --check fails when plugin.json drifts from SKILL.md frontmatter
pj="plugins/c-plan/.claude-plugin/plugin.json"
cp "$pj" "$pj.bak-sync-test"
python3 - <<'PY'
import json
p="plugins/c-plan/.claude-plugin/plugin.json"
d=json.load(open(p))
d["version"]="9.9.9-drift"
json.dump(d, open(p,"w"), indent=2)
open(p,"a").write("\n")
PY
set +e
out_drift="$(bash scripts/sync-plugin-views.sh --check 2>&1)"
rc_drift=$?
set -e
mv "$pj.bak-sync-test" "$pj"
[[ "$rc_drift" -ne 0 ]] || fail "drifted plugin.json should fail --check: $out_drift"
bash scripts/sync-plugin-views.sh --check || fail "check failed after drift restore"

# Package-root distribution artifacts are generated as part of the same leaf
# contract. A changed license must fail closed rather than silently publishing
# a package whose subdirectory no longer carries the source license.
license_path="plugins/c-plan/LICENSE"
cp "$license_path" "$license_path.bak-sync-test"
printf 'license drift fixture\n' >"$license_path"
set +e
out_license_drift="$(bash scripts/sync-plugin-views.sh --check c-plan 2>&1)"
rc_license_drift=$?
set -e
mv "$license_path.bak-sync-test" "$license_path"
[[ "$rc_license_drift" -ne 0 ]] || fail "drifted package LICENSE should fail --check: $out_license_drift"
printf '%s\n' "$out_license_drift" | grep -Fq 'LICENSE' \
  || fail "package LICENSE drift message missing: $out_license_drift"
bash scripts/sync-plugin-views.sh --check || fail "check failed after license drift restore"

readme_path="plugins/c-plan/README.md"
cp "$readme_path" "$readme_path.bak-sync-test"
printf '# stale package README\n' >"$readme_path"
set +e
out_readme_drift="$(bash scripts/sync-plugin-views.sh --check c-plan 2>&1)"
rc_readme_drift=$?
set -e
mv "$readme_path.bak-sync-test" "$readme_path"
[[ "$rc_readme_drift" -ne 0 ]] || fail "drifted package README should fail --check: $out_readme_drift"
printf '%s\n' "$out_readme_drift" | grep -Fq 'README' \
  || fail "package README drift message missing: $out_readme_drift"
bash scripts/sync-plugin-views.sh --check || fail "check failed after README drift restore"

# base checks ok; continue to SA8 sample-leaf cases

pass_sync() { printf '  ok %s\n' "$*"; }

# --- Internal symlink deref + escape refuse (SA8 sample leaf) ---
sample="_zz-sync-symlink-sample_"
cleanup_sample() {
  rm -rf "skills/$sample" "plugins/$sample"
}
trap 'cleanup_sample' EXIT

cleanup_sample
mkdir -p "skills/$sample/nested"
printf -- '---\nname: %s\ndescription: sample\nversion: 0.0.1\nlicense: MIT\nplatforms:\n  - macos\nmetadata:\n  skill_craft:\n    kind: prompt-only\n---\n\n# sample\n' "$sample" >"skills/$sample/SKILL.md"
printf 'target-body\n' >"skills/$sample/nested/real.txt"
ln -s "nested/real.txt" "skills/$sample/alias.txt"

# Internal link: sync succeeds and dereferences
bash scripts/sync-plugin-views.sh "$sample" || fail "internal symlink sync failed"
[[ -f "plugins/$sample/skills/$sample/alias.txt" ]] || fail "alias missing in view"
[[ ! -L "plugins/$sample/skills/$sample/alias.txt" ]] || fail "alias still symlink in view"
[[ "$(cat "plugins/$sample/skills/$sample/alias.txt")" == "target-body" ]] || fail "alias content"
[[ -f "plugins/$sample/.codex-plugin/plugin.json" ]] || fail "sample Codex manifest missing"
[[ -s "plugins/$sample/README.md" ]] || fail "sample package README missing"
cmp -s LICENSE "plugins/$sample/LICENSE" || fail "sample package LICENSE mismatch"
# residual no symlinks under this plugin view
if find "plugins/$sample" -type l 2>/dev/null | grep -q .; then
  fail "residual symlink in plugin view after internal deref"
fi
pass_sync "internal symlink dereferenced"

# .DS_Store below the skill root is noise in the source and in the view: it
# never fails --check and a sync never copies it.
printf 'finder' >"skills/$sample/nested/.DS_Store"
printf 'finder' >"plugins/$sample/skills/$sample/nested/.DS_Store"
bash scripts/sync-plugin-views.sh --check "$sample" >/dev/null \
  || fail "nested .DS_Store must not fail a leaf --check"
bash scripts/sync-plugin-views.sh "$sample" >/dev/null || fail "leaf sync with nested .DS_Store"
[[ -z "$(find "plugins/$sample" -name .DS_Store)" ]] || fail "leaf sync copied .DS_Store into the view"
rm -f "skills/$sample/nested/.DS_Store"
pass_sync "nested .DS_Store ignored for a leaf"

# Escaping symlink: refuse, no partial plugin view materialization of the escape
cleanup_sample
mkdir -p "skills/$sample"
printf -- '---\nname: %s\ndescription: sample\nversion: 0.0.1\nlicense: MIT\nplatforms:\n  - macos\nmetadata:\n  skill_craft:\n    kind: prompt-only\n---\n\n# sample\n' "$sample" >"skills/$sample/SKILL.md"
ln -s "/etc/passwd" "skills/$sample/escape.txt"
# Capture pre-existing plugins path state
rm -rf "plugins/$sample"
set +e
out_esc="$(bash scripts/sync-plugin-views.sh "$sample" 2>&1)"
rc_esc=$?
set -e
[[ "$rc_esc" -ne 0 ]] || fail "escape symlink should fail sync: $out_esc"
printf '%s\n' "$out_esc" | grep -qi 'escape\|escapes' || fail "escape message missing: $out_esc"
# no partial write of the skill tree with the escape file as symlink
if [[ -e "plugins/$sample/skills/$sample/escape.txt" ]]; then
  fail "partial write left escape in plugin view"
fi
cleanup_sample
# Restore trap only cleanup
trap - EXIT
cleanup_sample


# --- B1 dest-symlink tripwire (must not follow/delete through symlinked dest entry) ---
sample_b1="_zz-sync-dest-symlink_"
cleanup_b1() { rm -rf "skills/$sample_b1" "plugins/$sample_b1" "$root/.tmp-b1-home"; }
trap 'cleanup_sample; cleanup_b1' EXIT
cleanup_b1
mkdir -p "skills/$sample_b1"
printf -- '---\nname: %s\ndescription: sample\nversion: 0.0.1\nlicense: MIT\nplatforms:\n  - macos\nmetadata:\n  skill_craft:\n    kind: prompt-only\n---\n\n# sample\n' "$sample_b1" >"skills/$sample_b1/SKILL.md"
printf 'safe-body\n' >"skills/$sample_b1/body.txt"
# Pre-create plugin view with a symlinked path pointing outside (home fixture)
mkdir -p "plugins/$sample_b1/skills/$sample_b1" "$root/.tmp-b1-home"
printf 'DO-NOT-DELETE\n' >"$root/.tmp-b1-home/protected.txt"
# place symlink as child of dest skill tree
ln -s "$root/.tmp-b1-home" "plugins/$sample_b1/skills/$sample_b1/outside-link"
# log rsync implementation
if command -v rsync >/dev/null 2>&1; then
  rsync --version 2>&1 | head -1 || true
fi
# Sync must succeed (overwrite tree via rm -rf dest then copy) OR fail closed — either way protected must remain
set +e
out_b1="$(bash scripts/sync-plugin-views.sh "$sample_b1" 2>&1)"
rc_b1=$?
set -e
[[ -f "$root/.tmp-b1-home/protected.txt" ]] || fail "B1 protected target deleted via symlink (rc=$rc_b1 out=$out_b1)"
[[ "$(cat "$root/.tmp-b1-home/protected.txt")" == "DO-NOT-DELETE" ]] || fail "B1 protected content changed"
# After successful sync, outside-link should not remain as a live escape into home
if [[ "$rc_b1" -eq 0 ]]; then
  if [[ -L "plugins/$sample_b1/skills/$sample_b1/outside-link" ]]; then
    fail "B1 residual outside-link symlink after sync"
  fi
fi
pass_sync "dest-symlink tripwire (protected intact; rsync logged)"
cleanup_b1

# --- Plugin bundles (bundles/<plugin>/bundle.json) ---
expect_fail() {
  local label="$1" needle="$2"
  shift 2
  local out rc
  set +e
  out="$("$@" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -ne 0 ]] || fail "$label should fail: $out"
  printf '%s\n' "$out" | grep -Fq -- "$needle" || fail "$label did not report '$needle': $out"
}
tree_sum() { (cd "$1" && find . -type f | LC_ALL=C sort | xargs shasum 2>/dev/null) || true; }

# Real tree: the backchain view carries exactly its declared members and
# never the upstream skill-interop redirect (skill-craft owns skill-interop).
[[ "$(ls plugins/backchain/skills | tr '\n' ' ')" == "backchain plan-dispatcher " ]] \
  || fail "plugins/backchain/skills is not exactly backchain + plan-dispatcher"
[[ "$(ls plugins/backchain/agents)" == "backchain.md" ]] || fail "plugins/backchain/agents is not exactly backchain.md"
[[ ! -e plugins/backchain/skills/skill-interop && ! -e plugins/backchain/agents/skill-interop.md ]] \
  || fail "skill-interop must not be vendored into the backchain view"
cmp -s LICENSE plugins/backchain/LICENSE || fail "bundle view LICENSE must be the source root LICENSE"

zb="zz-sync-bundle"
cleanup_bundle() {
  rm -rf "bundles/$zb" "plugins/$zb" "skills/$zb" "bundles/zz-sync-other" "$root/.tmp-held-bundle" \
    "$root/.tmp-bundle-json" "$root/.tmp-bundle-src" "$root/.tmp-held-view"
}
trap 'cleanup_bundle' EXIT
cleanup_bundle
python3 - "$zb" <<'PY'
import hashlib, json, sys
from pathlib import Path
name = sys.argv[1]
bundle = Path("bundles") / name
files = {
    f"skills/{name}/SKILL.md": f"---\nname: {name}\ndescription: Sync bundle primary.\nversion: 0.0.1\nlicense: MIT\nplatforms:\n  - macos\nmetadata:\n  skill_craft:\n    kind: prompt-only\n---\n\n# primary\n",
    "skills/zz-sync-member/SKILL.md": "---\nname: zz-sync-member\ndescription: Sync bundle member.\nlicense: MIT\nmetadata:\n  version: 0.0.2\n  skill_craft:\n    kind: prompt-only\n---\n\n# member\n",
    "skills/zz-sync-member/references/notes.md": "member notes\n",
    f"agents/{name}.md": "# agent card\n",
}
records = []
for relative, text in sorted(files.items()):
    target = bundle / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode()
    target.write_bytes(data)
    records.append({"path": relative, "mode": "100644", "sha256": hashlib.sha256(data).hexdigest(),
                    "git_blob": hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()})
(bundle / "bundle.json").write_text(json.dumps({"format": "skill-craft-plugin-bundle/v1", "name": name,
    "description": "Synthetic sync bundle.", "skills": [name, "zz-sync-member"], "agents": [name]}, indent=2) + "\n")
(bundle / "PROVENANCE.json").write_text(json.dumps({"format": "skill-craft-vendored-bundle-provenance/v1",
    "bundle": name, "upstream": {"repository": "https://example.invalid/zz.git", "commit": "a" * 40,
    "manifest": {"path": ".claude-plugin/plugin.json", "name": name, "version": "0.0.1",
                 "sha256": "b" * 64, "git_blob": "c" * 40}}, "files": records}, indent=2) + "\n")
with open(".gitattributes", "a") as stream:
    stream.write(f"plugins/{name}/** -text -whitespace\n")
PY

bash scripts/sync-plugin-views.sh >/dev/null || fail "synthetic bundle full sync"
bash scripts/sync-plugin-views.sh --check >/dev/null || fail "synthetic bundle full check"
[[ "$(ls "plugins/$zb/skills" | tr '\n' ' ')" == "$zb zz-sync-member " ]] || fail "bundle view members"
[[ -f "plugins/$zb/agents/$zb.md" && -f "plugins/$zb/.codex-plugin/plugin.json" && -f "plugins/$zb/.cursor-plugin/plugin.json" ]] \
  || fail "bundle view adapters or agent missing"
grep -q "\"name\": \"$zb\"" .grok-plugin/marketplace.json || fail "bundle missing from Grok index"
pass_sync "synthetic bundle materialized"

printf 'drift\n' >> "plugins/$zb/skills/zz-sync-member/SKILL.md"
expect_fail "bundle member body drift" "out of sync with bundles/$zb/skills/zz-sync-member" \
  bash scripts/sync-plugin-views.sh --check "$zb"
bash scripts/sync-plugin-views.sh "$zb" >/dev/null || fail "restore member drift"

mkdir -p "plugins/$zb/skills/stale-member"
printf 'stale\n' > "plugins/$zb/skills/stale-member/SKILL.md"
expect_fail "stale undeclared member" "not exactly the declared members" \
  bash scripts/sync-plugin-views.sh --check "$zb"
bash scripts/sync-plugin-views.sh "$zb" >/dev/null || fail "sync over stale member"
[[ ! -e "plugins/$zb/skills/stale-member" ]] || fail "sync must remove an undeclared member view"

rm -f "plugins/$zb/agents/$zb.md"
expect_fail "missing bundle agent" "agent card plugins/$zb/agents/$zb.md out of sync" \
  bash scripts/sync-plugin-views.sh --check "$zb"
bash scripts/sync-plugin-views.sh "$zb" >/dev/null || fail "restore bundle agent"

python3 - "$zb" <<'PY'
import json, sys
path = f"plugins/{sys.argv[1]}/.codex-plugin/plugin.json"
data = json.load(open(path))
data["interface"]["defaultPrompt"] = ["stale"]
open(path, "w").write(json.dumps(data, indent=2) + "\n")
PY
expect_fail "bundle manifest drift" "Codex plugin manifest" bash scripts/sync-plugin-views.sh --check "$zb"
bash scripts/sync-plugin-views.sh "$zb" >/dev/null || fail "restore bundle manifest"
bash scripts/sync-plugin-views.sh --check "$zb" >/dev/null || fail "bundle check after repairs"
# Local noise is not drift in the exact-set checks (matches the orphan rule)
# nor inside a member tree, in the view or in the vendored source; a sync
# never copies it into a member view.
printf 'finder' > "plugins/$zb/.DS_Store"
printf 'finder' > "plugins/$zb/skills/.DS_Store"
printf 'finder' > "bundles/$zb/.DS_Store"
printf 'finder' > "plugins/$zb/skills/zz-sync-member/.DS_Store"
printf 'finder' > "plugins/$zb/skills/zz-sync-member/references/.DS_Store"
printf 'finder' > "bundles/$zb/skills/zz-sync-member/references/.DS_Store"
bash scripts/sync-plugin-views.sh --check "$zb" >/dev/null || fail ".DS_Store must not fail the bundle check"
python3 scripts/sync-vendored-bundles.py --check --bundle "$zb" >/dev/null \
  || fail ".DS_Store must not fail vendored verification"
bash scripts/sync-plugin-views.sh "$zb" >/dev/null || fail "bundle sync with .DS_Store noise"
[[ -z "$(find "plugins/$zb/skills/zz-sync-member" -name .DS_Store)" ]] \
  || fail "bundle sync copied .DS_Store into a member view"
rm -f "plugins/$zb/.DS_Store" "plugins/$zb/skills/.DS_Store" "bundles/$zb/.DS_Store" \
  "bundles/$zb/skills/zz-sync-member/references/.DS_Store"
pass_sync "bundle drift detected and repaired"

# Every exact-set branch of a bundle --check fails closed, and a sync repairs it.
printf 'stray\n' > "plugins/$zb/notes.md"
expect_fail "stray top-level entry" "plugins/$zb top-level entries are not exactly" \
  bash scripts/sync-plugin-views.sh --check "$zb"
bash scripts/sync-plugin-views.sh "$zb" >/dev/null || fail "sync over a stray top-level entry"
[[ ! -e "plugins/$zb/notes.md" ]] || fail "sync must remove a stray top-level entry"

printf 'stale\n' > "plugins/$zb/agents/stale.md"
expect_fail "undeclared agent card" "plugins/$zb/agents is not exactly the declared agent cards" \
  bash scripts/sync-plugin-views.sh --check "$zb"
bash scripts/sync-plugin-views.sh "$zb" >/dev/null || fail "sync over an undeclared agent card"
[[ ! -e "plugins/$zb/agents/stale.md" ]] || fail "sync must remove an undeclared agent card"

printf 'license drift\n' > "plugins/$zb/LICENSE"
expect_fail "bundle LICENSE drift" "plugins/$zb/LICENSE differs from source root LICENSE" \
  bash scripts/sync-plugin-views.sh --check "$zb"
bash scripts/sync-plugin-views.sh "$zb" >/dev/null || fail "sync over bundle LICENSE drift"
cmp -s LICENSE "plugins/$zb/LICENSE" || fail "sync must restore the bundle LICENSE"

ln -s ../../LICENSE "plugins/$zb/skills/zz-sync-member/license-link"
expect_fail "symlink in a bundle view" "plugins/$zb contains symlinks" \
  bash scripts/sync-plugin-views.sh --check "$zb"
bash scripts/sync-plugin-views.sh "$zb" >/dev/null || fail "sync over a symlink in the bundle view"
[[ -z "$(find "plugins/$zb" -type l)" ]] || fail "sync must leave no symlink in the bundle view"

mv "plugins/$zb" "$root/.tmp-held-view"
expect_fail "missing bundle view" "missing plugins/$zb (bundles/$zb)" \
  bash scripts/sync-plugin-views.sh --check "$zb"
rm -rf "$root/.tmp-held-view"
bash scripts/sync-plugin-views.sh "$zb" >/dev/null || fail "sync must recreate a missing bundle view"

# A declaration that drops its agents leaves agents/ in the view: --check
# reports it and a sync removes it.
cp -R "bundles/$zb" "$root/.tmp-bundle-src"
python3 - "$zb" <<'PY2'
import json, sys
from pathlib import Path
name = sys.argv[1]
bundle = Path("bundles") / name
declaration = json.loads((bundle / "bundle.json").read_text())
declaration["agents"] = []
(bundle / "bundle.json").write_text(json.dumps(declaration, indent=2) + "\n")
(bundle / "agents" / f"{name}.md").unlink()
(bundle / "agents").rmdir()
provenance = json.loads((bundle / "PROVENANCE.json").read_text())
provenance["files"] = [entry for entry in provenance["files"] if not entry["path"].startswith("agents/")]
(bundle / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2) + "\n")
PY2
expect_fail "agents dropped (top level)" "plugins/$zb top-level entries are not exactly" \
  bash scripts/sync-plugin-views.sh --check "$zb"
expect_fail "agents dropped (cards)" "plugins/$zb/agents is not exactly the declared agent cards" \
  bash scripts/sync-plugin-views.sh --check "$zb"
bash scripts/sync-plugin-views.sh "$zb" >/dev/null || fail "sync after dropping agents"
[[ ! -e "plugins/$zb/agents" ]] || fail "sync must remove agents/ when none are declared"
bash scripts/sync-plugin-views.sh --check "$zb" >/dev/null || fail "check of a bundle without agents"
rm -rf "bundles/$zb"
mv "$root/.tmp-bundle-src" "bundles/$zb"
bash scripts/sync-plugin-views.sh "$zb" >/dev/null || fail "restore bundle agents"
[[ -f "plugins/$zb/agents/$zb.md" ]] || fail "restored bundle view lacks its agent card"
bash scripts/sync-plugin-views.sh --check "$zb" >/dev/null || fail "bundle check after exact-set repairs"
pass_sync "bundle exact-set branches fail closed and repair"

# Generator refusals: every declaration and member-card rule fails before any
# write (the view is unchanged). Each case mutates a copy-restored source.
mutate_bundle() {
  python3 - "$zb" "$1" <<'PY2'
import json, sys
from pathlib import Path
name, case = sys.argv[1], sys.argv[2]
bundle = Path("bundles") / name
member = bundle / "skills/zz-sync-member/SKILL.md"
declaration = json.loads((bundle / "bundle.json").read_text())
if case == "extra-key":
    declaration["extra"] = True
elif case == "no-primary":
    declaration["skills"] = ["zz-sync-member"]
elif case == "member-name":
    member.write_text(member.read_text().replace("name: zz-sync-member", "name: zz-other-name", 1))
elif case == "member-version":
    member.write_text(member.read_text().replace("  version: 0.0.2\n", "  version: latest\n", 1))
elif case == "member-license":
    member.write_text(member.read_text().replace("license: MIT", "license: Apache-2.0", 1))
elif case == "no-agent":
    (bundle / "agents" / f"{name}.md").unlink()
elif case == "no-provenance":
    (bundle / "PROVENANCE.json").unlink()
else:
    raise SystemExit(f"unknown mutation {case}")
(bundle / "bundle.json").write_text(json.dumps(declaration, indent=2) + "\n")
PY2
}
refuse_bundle_case() {
  local label="$1" needle="$2" mutation="$3"
  shift 3
  local before
  rm -rf "$root/.tmp-bundle-src"
  cp -R "bundles/$zb" "$root/.tmp-bundle-src"
  mutate_bundle "$mutation" || fail "$label fixture mutation"
  before="$(tree_sum "plugins/$zb")"
  expect_fail "$label" "$needle" "$@"
  [[ "$(tree_sum "plugins/$zb")" == "$before" ]] || fail "$label changed the bundle view"
  rm -rf "bundles/$zb"
  mv "$root/.tmp-bundle-src" "bundles/$zb"
}
# sync-vendored-bundles.py repeats the declaration rules, so call the
# generator directly to pin its own copy of them.
refuse_bundle_case "extra bundle.json key" "bundle.json keys must be exactly agents, description, format, name, skills" \
  extra-key node scripts/skill-frontmatter-to-plugin-json.js --bundle "$zb" --members
refuse_bundle_case "bundle without its primary" "bundles/$zb/bundle.json skills must include the primary member $zb" \
  no-primary node scripts/skill-frontmatter-to-plugin-json.js --bundle "$zb" --members
refuse_bundle_case "member card name" "skills/zz-sync-member/SKILL.md name must be zz-sync-member" member-name \
  bash scripts/sync-plugin-views.sh "$zb"
refuse_bundle_case "member version" "zz-sync-member/SKILL.md needs a semantic version" member-version \
  bash scripts/sync-plugin-views.sh "$zb"
refuse_bundle_case "member license" "zz-sync-member license Apache-2.0 differs from primary MIT" member-license \
  bash scripts/sync-plugin-views.sh "$zb"
refuse_bundle_case "missing declared agent" "bundles/$zb: missing declared agents/$zb.md" no-agent \
  bash scripts/sync-plugin-views.sh "$zb"
refuse_bundle_case "missing provenance" "bundles/$zb requires PROVENANCE.json" no-provenance \
  node scripts/skill-frontmatter-to-plugin-json.js --bundle "$zb" --check

# One skill identity belongs to one package: a member declared by two bundles
# is refused for the bundle and for a named leaf operation, before any write.
other_bundle="zz-sync-other"
mkdir -p "bundles/$other_bundle"
printf '%s\n' "{\"format\": \"skill-craft-plugin-bundle/v1\", \"name\": \"$other_bundle\", \"description\": \"Second bundle.\", \"skills\": [\"$other_bundle\", \"zz-sync-member\"], \"agents\": []}" \
  > "bundles/$other_bundle/bundle.json"
plugins_before="$(tree_sum plugins)"
expect_fail "member declared by two bundles" "bundle member zz-sync-member is declared by both $zb and $other_bundle" \
  bash scripts/sync-plugin-views.sh "$zb"
expect_fail "leaf sync with a doubly declared member" "is declared by both" \
  bash scripts/sync-plugin-views.sh c-plan
[[ "$(tree_sum plugins)" == "$plugins_before" ]] || fail "a doubly declared member changed plugins/"
rm -rf "bundles/$other_bundle"
bash scripts/sync-plugin-views.sh --check "$zb" >/dev/null || fail "bundle check after generator refusals"
pass_sync "generator bundle refusals fail before writes"

# Vendored bytes are verified before any write: a tampered source must not
# reach the view.
member_card="bundles/$zb/skills/zz-sync-member/SKILL.md"
cp "$member_card" "$member_card.bak-sync-test"
view_before="$(tree_sum "plugins/$zb")"
printf 'tampered\n' >> "$member_card"
expect_fail "tampered vendored source" "not a verified vendored bundle" bash scripts/sync-plugin-views.sh "$zb"
[[ "$(tree_sum "plugins/$zb")" == "$view_before" ]] || fail "tampered source changed the bundle view"
mv "$member_card.bak-sync-test" "$member_card"

# Name collisions fail closed before writes.
mkdir -p "skills/$zb"
printf -- '---\nname: %s\ndescription: collide\nversion: 0.0.1\nlicense: MIT\nplatforms:\n  - macos\nmetadata:\n  skill_craft:\n    kind: prompt-only\n---\n\n# c\n' "$zb" > "skills/$zb/SKILL.md"
expect_fail "bundle/leaf collision" "collides with source skill" bash scripts/sync-plugin-views.sh
# A named operation takes the leaf path (skills/$zb exists) and must still
# refuse before any write rather than overwrite the bundle view.
view_before="$(tree_sum "plugins/$zb")"
expect_fail "named bundle/leaf collision" "bundle $zb collides with source skill skills/$zb" \
  bash scripts/sync-plugin-views.sh "$zb"
expect_fail "named bundle/leaf collision check" "bundle $zb collides with source skill skills/$zb" \
  bash scripts/sync-plugin-views.sh --check "$zb"
[[ "$(tree_sum "plugins/$zb")" == "$view_before" ]] || fail "named collision changed the bundle view"
rm -rf "skills/$zb"
cp "bundles/$zb/bundle.json" "$root/.tmp-bundle-json"
python3 - "$zb" <<'PY'
import json, sys
path = f"bundles/{sys.argv[1]}/bundle.json"
data = json.load(open(path))
data["skills"].append("c-plan")
open(path, "w").write(json.dumps(data, indent=2) + "\n")
PY
expect_fail "member named like a leaf" "duplicates source skill skills/c-plan" bash scripts/sync-plugin-views.sh "$zb"
mv "$root/.tmp-bundle-json" "bundles/$zb/bundle.json"
pass_sync "bundle collisions refused"

# A bundle view without its declaration is an orphan.
mv "bundles/$zb" "$root/.tmp-held-bundle"
expect_fail "bundle view without bundle.json" "orphan plugins/$zb" bash scripts/sync-plugin-views.sh --check
mv "$root/.tmp-held-bundle" "bundles/$zb"

# An escaping symlink in a member is refused with no partial view.
rm -rf "plugins/$zb"
ln -s /etc/passwd "bundles/$zb/skills/zz-sync-member/escape.txt"
set +e
out_bundle_escape="$(bash scripts/sync-plugin-views.sh "$zb" 2>&1)"
rc_bundle_escape=$?
set -e
rm -f "bundles/$zb/skills/zz-sync-member/escape.txt"
[[ "$rc_bundle_escape" -ne 0 ]] || fail "escaping bundle symlink should fail: $out_bundle_escape"
[[ ! -e "plugins/$zb" ]] || fail "escaping bundle symlink left a partial view"
pass_sync "bundle escape symlink refused without partial write"

# Without bundles the README inventory is exactly the skills table.
cleanup_bundle
rm -rf bundles plugins/backchain
bash scripts/sync-plugin-views.sh >/dev/null || fail "sync without bundles"
python3 - <<'PY' || fail "inventory without bundles must render only the skills table"
import pathlib
last = sorted(p.parent.name for p in pathlib.Path("skills").glob("*/SKILL.md"))[-1]
text = open("README.md").read()
block = text.split("<!-- skill-craft:inventory:start -->")[1].split("<!-- skill-craft:inventory:end -->")[0]
lines = block.split("\n")
assert "plugin bundle" not in block and "| Plugin |" not in block, "bundle table present"
assert lines[-2] == "" and lines[-3].startswith(f"| [{last}]"), lines[-4:]
assert '"backchain"' not in open(".grok-plugin/marketplace.json").read()
PY
trap - EXIT

printf 'sync-plugin-views.test.sh: PASS (incl. internal deref + escape refuse + B1 + bundles)\n'
exit 0
