#!/usr/bin/env bash
# Cursor and Grok marketplace metadata is generated from skill frontmatter.
# Exercise drift failures in an isolated checkout so this test never mutates
# the caller's materialized plugin views.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/skill-craft-native-marketplace.XXXXXX")"
repo="$tmp/repo"

cleanup() {
  rm -rf "$tmp"
}
trap cleanup EXIT

fail() {
  printf 'native-marketplace-adapters.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

expect_failure() {
  local label="$1"
  local needle="$2"
  shift 2
  local out rc
  set +e
  out="$("$@" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -ne 0 ]] || fail "$label should fail: $out"
  printf '%s\n' "$out" | grep -Fq "$needle" \
    || fail "$label did not report '$needle': $out"
}

mkdir -p "$repo"
# Preserve source files and generated views while excluding the active git
# checkout plus ignored caches/worktrees that do not belong in a fixture.
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
  -cf - .) | (cd "$repo" && tar -xf -)
cd "$repo"

[[ -x scripts/sync-plugin-views.sh ]] || fail "sync script is not executable"
node --check scripts/skill-frontmatter-to-plugin-json.js \
  || fail "generator syntax check"
bash scripts/sync-plugin-views.sh --check || fail "baseline adapter check"

# The adapters expose every actual source skill and nothing inferred from
# empty/stale directories.
node - <<'NODE' || exit 1
const fs = require("fs");
const leaves = fs
  .readdirSync("skills", { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && fs.existsSync(`skills/${entry.name}/SKILL.md`))
  .map((entry) => entry.name)
  .sort();
if (leaves.length === 0) {
  throw new Error("expected at least one source skill");
}
const cursor = JSON.parse(fs.readFileSync(".cursor-plugin/marketplace.json", "utf8"));
const grok = JSON.parse(fs.readFileSync(".grok-plugin/marketplace.json", "utf8"));
for (const [host, catalog] of [["Cursor", cursor], ["Grok", grok]]) {
  const names = catalog.plugins.map((plugin) => plugin.name);
  if (JSON.stringify(names) !== JSON.stringify(leaves)) {
    throw new Error(`${host} catalog leaf set is not exact`);
  }
}
for (const plugin of cursor.plugins) {
  if (plugin.source !== `./plugins/${plugin.name}` || !plugin.description) {
    throw new Error(`Cursor entry invalid for ${plugin.name}`);
  }
}
for (const plugin of grok.plugins) {
  if (plugin.source?.type !== "local" || plugin.source?.path !== `./plugins/${plugin.name}` || !plugin.version || !plugin.category) {
    throw new Error(`Grok entry invalid for ${plugin.name}`);
  }
}
NODE

# A leaf check only owns that leaf. It must not reject unrelated root-index
# drift, while the full check must catch the stale generated index.
node - <<'NODE'
const fs = require("fs");
const path = ".cursor-plugin/marketplace.json";
const catalog = JSON.parse(fs.readFileSync(path, "utf8"));
catalog.metadata.description = "stale test value";
fs.writeFileSync(path, JSON.stringify(catalog, null, 2) + "\n");
NODE
bash scripts/sync-plugin-views.sh --check c-plan \
  || fail "leaf-only check should not inspect root marketplace indexes"
expect_failure "stale Cursor index" "Cursor marketplace index" \
  bash scripts/sync-plugin-views.sh --check
bash scripts/sync-plugin-views.sh || fail "restore stale Cursor index"

# A missing per-plugin Cursor manifest is caught by the owning leaf check.
rm -f plugins/c-plan/.cursor-plugin/plugin.json
expect_failure "missing Cursor manifest" "missing" \
  bash scripts/sync-plugin-views.sh --check c-plan
bash scripts/sync-plugin-views.sh c-plan || fail "restore missing Cursor manifest"
bash scripts/sync-plugin-views.sh --check c-plan \
  || fail "restored Cursor manifest"

# Exact generated index content rejects entries that are not backed by a skill.
node - <<'NODE'
const fs = require("fs");
const path = ".grok-plugin/marketplace.json";
const catalog = JSON.parse(fs.readFileSync(path, "utf8"));
catalog.plugins.push({
  name: "_zz-extra",
  version: "0.0.0",
  description: "extra",
  category: "productivity",
  source: { type: "local", path: "./plugins/_zz-extra" },
});
fs.writeFileSync(path, JSON.stringify(catalog, null, 2) + "\n");
NODE
expect_failure "extra Grok index entry" "Grok marketplace index" \
  bash scripts/sync-plugin-views.sh --check
bash scripts/sync-plugin-views.sh || fail "restore extra Grok index entry"

# Adding a real source leaf must update all discovery surfaces, preserve prose
# outside the inventory, and remove the entry again when the leaf is retired.
printf '\n<!-- outside-inventory-sentinel -->\n' >> README.md
mkdir -p skills/catalog-fixture
cat > skills/catalog-fixture/SKILL.md <<'SKILL'
---
name: catalog-fixture
version: 1.2.3
description: Test | automatic catalog inventory.
license: MIT
---
Fixture only.
SKILL
bash scripts/sync-plugin-views.sh || fail "new source leaf sync"
node - <<'NODE'
const fs = require("fs");
const readme = fs.readFileSync("README.md", "utf8");
if (!readme.includes("[catalog-fixture](skills/catalog-fixture/SKILL.md) | 1.2.3 | Test \\| automatic")) {
  throw new Error("new skill/version/escaped description missing from README inventory");
}
if (!readme.includes("<!-- outside-inventory-sentinel -->")) throw new Error("outside prose lost");
for (const host of ["cursor", "grok"]) {
  const catalog = JSON.parse(fs.readFileSync(`.${host}-plugin/marketplace.json`, "utf8"));
  if (catalog.plugins.filter(p => p.name === "catalog-fixture").length !== 1) {
    throw new Error(`${host} new source leaf missing or duplicated`);
  }
}
NODE

cp README.md "$tmp/readme-before-drift"
python3 - <<'PY'
from pathlib import Path
p = Path("README.md")
text = p.read_text()
row = next(line for line in text.splitlines(True) if line.startswith("| [catalog-fixture]"))
p.write_text(text.replace(row, row + row))
PY
bash scripts/sync-plugin-views.sh --check c-plan || fail "leaf check must ignore root inventory"
expect_failure "duplicate README row" "README inventory out of sync" \
  node scripts/skill-frontmatter-to-plugin-json.js --marketplaces --check
bash scripts/sync-plugin-views.sh || fail "restore generated inventory"
cmp -s README.md "$tmp/readme-before-drift" || fail "inventory repair changed unrelated prose"

python3 - <<'PY'
from pathlib import Path
p = Path("README.md")
p.write_text(p.read_text().replace("<!-- skill-craft:inventory:end -->", ""))
PY
expect_failure "missing inventory marker" "exactly one ordered" \
  node scripts/skill-frontmatter-to-plugin-json.js --marketplaces --write
cp "$tmp/readme-before-drift" README.md
printf '\n<!-- skill-craft:inventory:start -->\n' >> README.md
expect_failure "duplicate inventory marker" "exactly one ordered" \
  node scripts/skill-frontmatter-to-plugin-json.js --marketplaces --write
cp "$tmp/readme-before-drift" README.md
rm -rf skills/catalog-fixture plugins/catalog-fixture
bash scripts/sync-plugin-views.sh || fail "removed source leaf sync"
grep -q 'catalog-fixture' README.md && fail "removed leaf remains in README inventory"

# An empty/incomplete checkout must not turn stale catalogs into a green check
# or overwrite a previously good inventory/catalog with an empty release.
cp README.md "$tmp/readme-before-empty"
cp .cursor-plugin/marketplace.json "$tmp/cursor-before-empty"
cp .grok-plugin/marketplace.json "$tmp/grok-before-empty"
mv skills "$tmp/held-skills"
mkdir skills
expect_failure "empty full check" "no source skills" bash scripts/sync-plugin-views.sh --check
expect_failure "empty full sync" "no source skills" bash scripts/sync-plugin-views.sh
expect_failure "empty direct generation" "no source skills" \
  node scripts/skill-frontmatter-to-plugin-json.js --marketplaces --write
cmp -s README.md "$tmp/readme-before-empty" || fail "empty source changed README"
cmp -s .cursor-plugin/marketplace.json "$tmp/cursor-before-empty" || fail "empty source changed Cursor index"
cmp -s .grok-plugin/marketplace.json "$tmp/grok-before-empty" || fail "empty source changed Grok index"
rmdir skills
mv "$tmp/held-skills" skills

# Empty stale directories are ignored, but a package with contents and no
# source SKILL.md is still an orphan.
mkdir -p skills/_zz-empty plugins/_zz-empty
bash scripts/sync-plugin-views.sh --check \
  || fail "empty stale directories should not fail full check"
mkdir -p plugins/_zz-orphan/.cursor-plugin
printf '%s\n' '{"name":"_zz-orphan","version":"0.0.0"}' \
  >plugins/_zz-orphan/.cursor-plugin/plugin.json
expect_failure "packaged orphan" "orphan" \
  bash scripts/sync-plugin-views.sh --check

printf 'native-marketplace-adapters.test.sh: PASS (generated Cursor/Grok adapter drift checks)\n'
