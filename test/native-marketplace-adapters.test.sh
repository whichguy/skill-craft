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
  printf '%s\n' "$out" | grep -Fq -- "$needle" \
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
# Committed plugins/ is release output and may lag the source; regenerate the
# copy so the checks below test the generator, not release freshness.
bash scripts/sync-plugin-views.sh >/dev/null || fail "baseline adapter sync"
bash scripts/sync-plugin-views.sh --check || fail "baseline adapter check"

# Generator command line: each misuse fails with its own message and writes
# nothing; an unknown option is refused rather than silently dropped.
gen="scripts/skill-frontmatter-to-plugin-json.js"
generated_digest() {
  (find plugins .cursor-plugin .grok-plugin README.md -type f | LC_ALL=C sort | xargs shasum) 2>/dev/null
}
generated_digest > "$tmp/generated-before-cli"
expect_failure "unknown option on a leaf" "unknown option --bogus" node "$gen" c-plan --check --bogus
expect_failure "--marketplaces with a leaf" "--marketplaces does not take a leaf" \
  node "$gen" --marketplaces c-plan --check
expect_failure "--write with --check" "mutually exclusive" node "$gen" c-plan --write --check
expect_failure "two leaves" "missing leaf" node "$gen" c-plan skill-interop --check
node "$gen" c-plan --check >/dev/null || fail "leaf --check must still pass"
node "$gen" --marketplaces --check >/dev/null || fail "--marketplaces --check must still pass"
generated_digest | cmp -s - "$tmp/generated-before-cli" || fail "generator command-line refusals changed generated files"

# The adapters expose every actual source skill, and nothing inferred from empty/stale directories.
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
const published = leaves;
const cursor = JSON.parse(fs.readFileSync(".cursor-plugin/marketplace.json", "utf8"));
const grok = JSON.parse(fs.readFileSync(".grok-plugin/marketplace.json", "utf8"));
for (const [host, catalog] of [["Cursor", cursor], ["Grok", grok]]) {
  const names = catalog.plugins.map((plugin) => plugin.name);
  if (JSON.stringify(names) !== JSON.stringify(published)) {
    throw new Error(`${host} catalog set is not exactly the leaves`);
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
for (const leaf of leaves) {
  const root = `plugins/${leaf}`;
  const claude = JSON.parse(fs.readFileSync(`${root}/.claude-plugin/plugin.json`, "utf8"));
  const codex = JSON.parse(fs.readFileSync(`${root}/.codex-plugin/plugin.json`, "utf8"));
  for (const key of ["name", "version", "description", "author", "repository", "license"]) {
    if (JSON.stringify(codex[key]) !== JSON.stringify(claude[key])) {
      throw new Error(`Codex identity drift for ${leaf}: ${key}`);
    }
  }
  if (codex.skills !== "./skills/") {
    throw new Error(`Codex skill path invalid for ${leaf}`);
  }
  if ("hooks" in codex || "mcpServers" in codex || "apps" in codex) {
    throw new Error(`Codex manifest must not invent components for ${leaf}`);
  }
  const requiredInterface = [
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
  ];
  for (const key of requiredInterface) {
    if (typeof codex.interface?.[key] !== "string" || !codex.interface[key].trim()) {
      throw new Error(`Codex interface ${key} missing for ${leaf}`);
    }
  }
  if (!Array.isArray(codex.interface?.capabilities) || codex.interface.capabilities.length === 0 ||
      !Array.isArray(codex.interface?.defaultPrompt) || codex.interface.defaultPrompt.length === 0) {
    throw new Error(`Codex interface actions missing for ${leaf}`);
  }
  const expectedCodexPrompt = `Use $${leaf}:${leaf} for this task.`;
  if (JSON.stringify(codex.interface.defaultPrompt) !== JSON.stringify([expectedCodexPrompt])) {
    throw new Error(`Codex default prompt must use the qualified plugin skill for ${leaf}`);
  }
  if (!fs.existsSync(`${root}/LICENSE`) || fs.readFileSync(`${root}/LICENSE`, "utf8") !== fs.readFileSync("LICENSE", "utf8")) {
    throw new Error(`package root LICENSE missing or drifted for ${leaf}`);
  }
  if (!fs.existsSync(`${root}/README.md`) || !fs.readFileSync(`${root}/README.md`, "utf8").trim()) {
    throw new Error(`package root README missing for ${leaf}`);
  }
  const readme = fs.readFileSync(`${root}/README.md`, "utf8");
  if (!readme.includes(`\`$${leaf}:${leaf}\``) || !readme.includes(`\`/${leaf}:${leaf}\``)) {
    throw new Error(`package README must document qualified host invocations for ${leaf}`);
  }
  if (readme.includes(`\`$${leaf}\``)) {
    throw new Error(`package README must not claim bare Codex invocation for ${leaf}`);
  }
  const cards = [];
  const visit = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = `${dir}/${entry.name}`;
      if (entry.isDirectory()) visit(full);
      else if (entry.isFile() && entry.name === "SKILL.md") cards.push(full);
    }
  };
  visit(`${root}/skills`);
  if (JSON.stringify(cards.sort()) !== JSON.stringify([`${root}/skills/${leaf}/SKILL.md`])) {
    throw new Error(`unexpected public skill cards for ${leaf}: ${cards.join(", ")}`);
  }
}
NODE

# Claude and Codex catalogs keep the historical marketplace name, list every
# local package, and carry each catalog/external-plugins.json entry verbatim.
node - <<'NODE' || exit 1
const fs = require("fs");
const { isDeepStrictEqual } = require("util");
const leaves = fs
  .readdirSync("skills", { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && fs.existsSync(`skills/${entry.name}/SKILL.md`))
  .map((entry) => entry.name);
const published = leaves.sort();
const external = JSON.parse(fs.readFileSync("catalog/external-plugins.json", "utf8")).plugins;
const externalNames = new Set(external.map((plugin) => plugin.name));
const claude = JSON.parse(fs.readFileSync(".claude-plugin/marketplace.json", "utf8"));
const codex = JSON.parse(fs.readFileSync(".agents/plugins/marketplace.json", "utf8"));
const localSource = {
  Claude: (name) => `./plugins/${name}`,
  Codex: (name) => ({ source: "local", path: `./plugins/${name}` }),
};
for (const [host, catalog] of [["Claude", claude], ["Codex", codex]]) {
  if (catalog.name !== "skill-craft-market") {
    throw new Error(`${host} catalog must keep the skill-craft-market name`);
  }
  const local = catalog.plugins.filter((plugin) => !externalNames.has(plugin.name));
  if (JSON.stringify(local.map((plugin) => plugin.name).sort()) !== JSON.stringify(published)) {
    throw new Error(`${host} local entries are not exactly the leaves`);
  }
  for (const plugin of local) {
    if (!isDeepStrictEqual(plugin.source, localSource[host](plugin.name))) {
      throw new Error(`${host} local source invalid for ${plugin.name}`);
    }
  }
  for (const want of external) {
    const got = catalog.plugins.filter((plugin) => plugin.name === want.name);
    if (got.length !== 1 || !isDeepStrictEqual(got[0].source, want.source)) {
      throw new Error(`${host} catalog must carry external ${want.name} once with its pinned source`);
    }
  }
}
NODE

# Each invalid external entry is refused before any catalog is compared.
external="catalog/external-plugins.json"
cp "$external" "$tmp/external-before"
expect_external_failure() {
  local label="$1" needle="$2" edit="$3"
  EDIT="$edit" node - <<'NODE'
const fs = require("fs");
const path = "catalog/external-plugins.json";
const data = JSON.parse(fs.readFileSync(path, "utf8"));
const plugins = data.plugins;
new Function("plugins", process.env.EDIT)(plugins);
fs.writeFileSync(path, JSON.stringify(data, null, 2) + "\n");
NODE
  expect_failure "$label" "$needle" node "$gen" --marketplaces --check
  cp "$tmp/external-before" "$external"
}
expect_external_failure "external local-name collision" "also published from this repository" \
  'plugins[0].name = "c-plan";'
expect_external_failure "external short sha" "full 40-character sha pin" \
  'plugins[0].source.sha = plugins[0].source.sha.slice(0, 12);'
expect_external_failure "external two-part version" "needs a semantic version" \
  'plugins[0].version = "1.0";'
expect_external_failure "duplicate external entry" "listed more than once" \
  'plugins.push(JSON.parse(JSON.stringify(plugins.find((p) => p.name === "lennox-s40") || plugins[0])));'
expect_external_failure "external local source" "source.source must be url or git-subdir" \
  'plugins[0].source = { source: "local", path: "./plugins/x" };'
expect_external_failure "external non-GitHub URL" "source.url must be https://github.com/<owner>/<repo>" \
  'plugins[0].source.url = "https://gitlab.com/whichguy/x.git";'
expect_external_failure "external escaping path" "relative path inside the repository" \
  'Object.assign(plugins[0].source, { source: "git-subdir", path: "../x" });'
expect_external_failure "external extra component" "unexpected key mcpServers" \
  'plugins[0].mcpServers = { x: { command: "x" } };'
cmp -s "$external" "$tmp/external-before" || fail "external catalog not restored"
node "$gen" --marketplaces --check >/dev/null || fail "restored external catalog must pass"

# A hand edit to a generated Claude/Codex catalog is drift.
node - <<'NODE'
const fs = require("fs");
const path = ".agents/plugins/marketplace.json";
const catalog = JSON.parse(fs.readFileSync(path, "utf8"));
catalog.name = "hand-edited";
fs.writeFileSync(path, JSON.stringify(catalog, null, 2) + "\n");
NODE
expect_failure "hand-edited Codex catalog" "Codex marketplace index" \
  node "$gen" --marketplaces --check
bash scripts/sync-plugin-views.sh || fail "restore hand-edited Codex catalog"

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

# Codex is a generated peer adapter, not a hand-maintained special case.
rm -f plugins/c-plan/.codex-plugin/plugin.json
expect_failure "missing Codex manifest" "missing" \
  bash scripts/sync-plugin-views.sh --check c-plan
bash scripts/sync-plugin-views.sh c-plan || fail "restore missing Codex manifest"
bash scripts/sync-plugin-views.sh --check c-plan \
  || fail "restored Codex manifest"

codex_manifest="plugins/c-plan/.codex-plugin/plugin.json"
cp "$codex_manifest" "$codex_manifest.bak-native-test"
node - <<'NODE'
const fs = require("fs");
const path = "plugins/c-plan/.codex-plugin/plugin.json";
const manifest = JSON.parse(fs.readFileSync(path, "utf8"));
manifest.interface.defaultPrompt = ["stale fixture"];
fs.writeFileSync(path, JSON.stringify(manifest, null, 2) + "\n");
NODE
expect_failure "drifted Codex manifest" "Codex plugin manifest" \
  bash scripts/sync-plugin-views.sh --check c-plan
mv "$codex_manifest.bak-native-test" "$codex_manifest"
bash scripts/sync-plugin-views.sh --check c-plan \
  || fail "restored Codex manifest after drift"

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
plugins_digest() { (find plugins -type f | LC_ALL=C sort | xargs shasum) 2>/dev/null; }
cp README.md "$tmp/readme-before-empty"
cp .cursor-plugin/marketplace.json "$tmp/cursor-before-empty"
cp .grok-plugin/marketplace.json "$tmp/grok-before-empty"
plugins_digest > "$tmp/plugins-before-empty"
mv skills "$tmp/held-skills"
mkdir skills
expect_failure "empty full check" "no source skills" bash scripts/sync-plugin-views.sh --check
expect_failure "empty full sync" "no source skills" bash scripts/sync-plugin-views.sh
expect_failure "empty direct generation" "no source skills" \
  node scripts/skill-frontmatter-to-plugin-json.js --marketplaces --write
cmp -s README.md "$tmp/readme-before-empty" || fail "empty source changed README"
cmp -s .cursor-plugin/marketplace.json "$tmp/cursor-before-empty" || fail "empty source changed Cursor index"
cmp -s .grok-plugin/marketplace.json "$tmp/grok-before-empty" || fail "empty source changed Grok index"
plugins_digest | cmp -s - "$tmp/plugins-before-empty" || fail "empty source changed plugins/"
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

printf 'native-marketplace-adapters.test.sh: PASS (generated host catalog and adapter drift checks)\n'
