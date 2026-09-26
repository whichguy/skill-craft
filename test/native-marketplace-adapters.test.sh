#!/usr/bin/env bash
# Cursor and Grok marketplace metadata is generated from skill frontmatter.
# Exercise drift failures in an isolated checkout so this test never mutates
# the caller's materialized plugin views.
#
# Every skill ships in the one plugins/skill-craft bundle: the generator's
# CLI takes --package or --marketplaces (no per-leaf argument), and the
# marketplace catalogs list exactly one local plugin entry ("skill-craft")
# rather than one entry per skill.
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

PLUGIN="skill-craft"
MARKETPLACE="whichguy"

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
  (find plugins .cursor-plugin .grok-plugin .claude-plugin .agents README.md -type f | LC_ALL=C sort | xargs shasum) 2>/dev/null
}
generated_digest > "$tmp/generated-before-cli"
expect_failure "unknown option" "unknown argument --bogus" node "$gen" --package --check --bogus
expect_failure "both --package and --marketplaces" "choose exactly one of --package or --marketplaces" \
  node "$gen" --package --marketplaces --check
expect_failure "neither --package nor --marketplaces" "choose exactly one of --package or --marketplaces" \
  node "$gen" --check
expect_failure "--write with --check" "mutually exclusive" node "$gen" --package --write --check
node "$gen" --package --check >/dev/null || fail "--package --check must still pass"
node "$gen" --marketplaces --check >/dev/null || fail "--marketplaces --check must still pass"
generated_digest | cmp -s - "$tmp/generated-before-cli" || fail "generator command-line refusals changed generated files"

# The bundle carries every actual source skill, and nothing inferred from
# empty/stale directories; the Cursor and Grok catalogs each list exactly one
# local plugin entry (the bundle), not one per skill.
node - <<NODE || exit 1
const fs = require("fs");
const plugin = "$PLUGIN";
const leaves = fs
  .readdirSync("skills", { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && fs.existsSync(\`skills/\${entry.name}/SKILL.md\`))
  .map((entry) => entry.name)
  .sort();
if (leaves.length === 0) {
  throw new Error("expected at least one source skill");
}
const cursor = JSON.parse(fs.readFileSync(".cursor-plugin/marketplace.json", "utf8"));
const grok = JSON.parse(fs.readFileSync(".grok-plugin/marketplace.json", "utf8"));
for (const [host, catalog] of [["Cursor", cursor], ["Grok", grok]]) {
  const names = catalog.plugins.map((p) => p.name);
  if (JSON.stringify(names) !== JSON.stringify([plugin])) {
    throw new Error(\`\${host} catalog must list exactly the one bundle plugin, got \${names}\`);
  }
}
const cursorPlugin = cursor.plugins[0];
if (cursorPlugin.source !== \`./plugins/\${plugin}\` || !cursorPlugin.description) {
  throw new Error("Cursor entry invalid");
}
const grokPlugin = grok.plugins[0];
if (grokPlugin.source?.type !== "local" || grokPlugin.source?.path !== \`./plugins/\${plugin}\` ||
    !grokPlugin.version || !grokPlugin.category) {
  throw new Error("Grok entry invalid");
}

const base = \`plugins/\${plugin}\`;
const claude = JSON.parse(fs.readFileSync(\`\${base}/.claude-plugin/plugin.json\`, "utf8"));
const codex = JSON.parse(fs.readFileSync(\`\${base}/.codex-plugin/plugin.json\`, "utf8"));
for (const key of ["name", "version", "description", "author", "repository", "license"]) {
  if (JSON.stringify(codex[key]) !== JSON.stringify(claude[key])) {
    throw new Error(\`Codex identity drift: \${key}\`);
  }
}
if (codex.skills !== "./skills/") {
  throw new Error("Codex skill path invalid");
}
if ("mcpServers" in codex || "apps" in codex) {
  throw new Error("Codex manifest must not invent components");
}
// Hooks come only from skills/<leaf>/host-hooks.json, merged into one file.
const declaresHooks = leaves.some((leaf) => fs.existsSync(\`skills/\${leaf}/host-hooks.json\`));
if (("hooks" in codex) !== declaresHooks || (declaresHooks && codex.hooks !== "./hooks/codex.json")) {
  throw new Error("Codex hooks must match the merged skills/<leaf>/host-hooks.json declarations");
}
const requiredInterface = ["displayName", "shortDescription", "longDescription", "developerName", "category"];
for (const key of requiredInterface) {
  if (typeof codex.interface?.[key] !== "string" || !codex.interface[key].trim()) {
    throw new Error(\`Codex interface \${key} missing\`);
  }
}
if (!Array.isArray(codex.interface?.capabilities) || codex.interface.capabilities.length === 0 ||
    !Array.isArray(codex.interface?.defaultPrompt) || codex.interface.defaultPrompt.length === 0) {
  throw new Error("Codex interface actions missing");
}
const featured = ["shiploop", "improve", "ask-agent"].filter((leaf) => leaves.includes(leaf));
const expectedCodexPrompt = (featured.length ? featured : leaves.slice(0, 1))
  .map((leaf) => \`Use $\${plugin}:\${leaf} for this task.\`);
if (JSON.stringify(codex.interface.defaultPrompt) !== JSON.stringify(expectedCodexPrompt)) {
  throw new Error("Codex default prompt must use the qualified bundle-namespaced skills");
}
if (!fs.existsSync(\`\${base}/LICENSE\`) || fs.readFileSync(\`\${base}/LICENSE\`, "utf8") !== fs.readFileSync("LICENSE", "utf8")) {
  throw new Error("package root LICENSE missing or drifted");
}
if (!fs.existsSync(\`\${base}/README.md\`) || !fs.readFileSync(\`\${base}/README.md\`, "utf8").trim()) {
  throw new Error("package root README missing");
}
const readme = fs.readFileSync(\`\${base}/README.md\`, "utf8");
if (!readme.includes(\`\\\`$\${plugin}:<skill>\\\`\`) || !readme.includes(\`\\\`/\${plugin}:<skill>\\\`\`)) {
  throw new Error("package README must document the qualified host invocation pattern");
}
for (const leaf of leaves) {
  if (!readme.includes(\`\\\`/\${plugin}:\${leaf}\\\`\`)) {
    throw new Error(\`package README must list the qualified Claude command for \${leaf}\`);
  }
}
const cards = [];
const visit = (dir) => {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = \`\${dir}/\${entry.name}\`;
    if (entry.isDirectory()) visit(full);
    else if (entry.isFile() && entry.name === "SKILL.md") cards.push(full);
  }
};
visit(\`\${base}/skills\`);
const expectedCards = leaves.map((leaf) => \`\${base}/skills/\${leaf}/SKILL.md\`).sort();
if (JSON.stringify(cards.sort()) !== JSON.stringify(expectedCards)) {
  throw new Error(\`unexpected public skill cards in the bundle: \${cards.join(", ")}\`);
}
NODE

# Claude and Codex catalogs use the "whichguy" marketplace name, list the one
# local bundle plugin, and carry each catalog/external-plugins.json entry
# verbatim.
node - <<NODE || exit 1
const fs = require("fs");
const { isDeepStrictEqual } = require("util");
const plugin = "$PLUGIN";
const marketplace = "$MARKETPLACE";
const external = JSON.parse(fs.readFileSync("catalog/external-plugins.json", "utf8")).plugins;
const externalNames = new Set(external.map((p) => p.name));
const claude = JSON.parse(fs.readFileSync(".claude-plugin/marketplace.json", "utf8"));
const codex = JSON.parse(fs.readFileSync(".agents/plugins/marketplace.json", "utf8"));
const localSource = {
  Claude: () => \`./plugins/\${plugin}\`,
  Codex: () => ({ source: "local", path: \`./plugins/\${plugin}\` }),
};
for (const [host, catalog] of [["Claude", claude], ["Codex", codex]]) {
  if (catalog.name !== marketplace) {
    throw new Error(\`\${host} catalog must use the \${marketplace} marketplace name\`);
  }
  const local = catalog.plugins.filter((p) => !externalNames.has(p.name));
  if (local.length !== 1 || local[0].name !== plugin) {
    throw new Error(\`\${host} local entries must be exactly the one bundle plugin\`);
  }
  if (!isDeepStrictEqual(local[0].source, localSource[host]())) {
    throw new Error(\`\${host} local source invalid for \${plugin}\`);
  }
  for (const want of external) {
    const got = catalog.plugins.filter((p) => p.name === want.name);
    if (got.length !== 1 || !isDeepStrictEqual(got[0].source, want.source)) {
      throw new Error(\`\${host} catalog must carry external \${want.name} once with its pinned source\`);
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

# The package check (plugins/skill-craft's own manifests) does not reach into
# the root marketplace indexes, while the marketplaces check does.
node - <<'NODE'
const fs = require("fs");
const path = ".cursor-plugin/marketplace.json";
const catalog = JSON.parse(fs.readFileSync(path, "utf8"));
catalog.metadata.description = "stale test value";
fs.writeFileSync(path, JSON.stringify(catalog, null, 2) + "\n");
NODE
node "$gen" --package --check >/dev/null \
  || fail "package check should not inspect root marketplace indexes"
expect_failure "stale Cursor index" "Cursor marketplace index" \
  node "$gen" --marketplaces --check
bash scripts/sync-plugin-views.sh || fail "restore stale Cursor index"

# A missing bundle Cursor manifest is caught by the package check.
rm -f "plugins/$PLUGIN/.cursor-plugin/plugin.json"
expect_failure "missing Cursor manifest" "missing" \
  node "$gen" --package --check
node "$gen" --package --write >/dev/null || fail "restore missing Cursor manifest"
node "$gen" --package --check >/dev/null || fail "restored Cursor manifest"

# Codex is a generated peer adapter, not a hand-maintained special case.
rm -f "plugins/$PLUGIN/.codex-plugin/plugin.json"
expect_failure "missing Codex manifest" "missing" \
  node "$gen" --package --check
node "$gen" --package --write >/dev/null || fail "restore missing Codex manifest"
node "$gen" --package --check >/dev/null || fail "restored Codex manifest"

codex_manifest="plugins/$PLUGIN/.codex-plugin/plugin.json"
cp "$codex_manifest" "$codex_manifest.bak-native-test"
node - <<NODE
const fs = require("fs");
const path = "$codex_manifest";
const manifest = JSON.parse(fs.readFileSync(path, "utf8"));
manifest.interface.defaultPrompt = ["stale fixture"];
fs.writeFileSync(path, JSON.stringify(manifest, null, 2) + "\n");
NODE
expect_failure "drifted Codex manifest" "Codex plugin manifest" \
  node "$gen" --package --check
mv "$codex_manifest.bak-native-test" "$codex_manifest"
node "$gen" --package --check >/dev/null || fail "restored Codex manifest after drift"

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

# Adding a real source leaf materializes it inside the one bundle and updates
# the README inventory, but does not grow the marketplace catalogs (every
# host still lists exactly the one "skill-craft" plugin entry); prose outside
# the inventory is preserved, and removing the leaf again cleans it up.
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
node - <<NODE
const fs = require("fs");
const plugin = "$PLUGIN";
const readme = fs.readFileSync("README.md", "utf8");
if (!readme.includes("[catalog-fixture](skills/catalog-fixture/SKILL.md) | 1.2.3 | Test \\\\| automatic")) {
  throw new Error("new skill/version/escaped description missing from README inventory");
}
if (!readme.includes("<!-- outside-inventory-sentinel -->")) throw new Error("outside prose lost");
for (const host of ["cursor", "grok"]) {
  const catalog = JSON.parse(fs.readFileSync(\`.\${host}-plugin/marketplace.json\`, "utf8"));
  const names = catalog.plugins.map((p) => p.name);
  if (JSON.stringify(names) !== JSON.stringify([plugin])) {
    throw new Error(\`\${host} catalog must still list only the one bundle plugin after a new leaf, got \${names}\`);
  }
}
if (!fs.existsSync(\`plugins/\${plugin}/skills/catalog-fixture/SKILL.md\`)) {
  throw new Error("new leaf missing from the materialized bundle");
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
node "$gen" --package --check >/dev/null || fail "package check must ignore root inventory"
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
rm -rf skills/catalog-fixture
bash scripts/sync-plugin-views.sh || fail "removed source leaf sync"
grep -q 'catalog-fixture' README.md && fail "removed leaf remains in README inventory"
[[ ! -e "plugins/$PLUGIN/skills/catalog-fixture" ]] || fail "removed leaf remains in the materialized bundle"

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

# A stray plugins/<name> directory other than the one true bundle is always
# rejected by a full check, packaged or not: this repo publishes exactly one
# plugin (plugins/skill-craft), so any other entry is a leftover, not noise.
mkdir -p "skills/_zz-empty"
mkdir -p "plugins/_zz-orphan/.cursor-plugin"
printf '%s\n' '{"name":"_zz-orphan","version":"0.0.0"}' \
  >"plugins/_zz-orphan/.cursor-plugin/plugin.json"
expect_failure "stray plugins/<name> directory" "is not generated" \
  bash scripts/sync-plugin-views.sh --check
bash scripts/sync-plugin-views.sh || fail "restore stray plugins directory"
[[ ! -e "plugins/_zz-orphan" ]] || fail "full sync should have removed the stray plugins directory"
rm -rf "skills/_zz-empty"

printf 'native-marketplace-adapters.test.sh: PASS (generated host catalog and adapter drift checks)\n'
