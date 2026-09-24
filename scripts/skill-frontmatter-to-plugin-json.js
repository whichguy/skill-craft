#!/usr/bin/env node
"use strict";

/**
 * Derive plugin manifests and marketplace indexes (Claude, Codex, Cursor, Grok)
 * from skills/<leaf>/SKILL.md
 * frontmatter and from plugin bundles (bundles/<plugin>/bundle.json).
 *
 * A bundle packages several member skills as one plugin. Its primary member
 * (the skill named like the bundle) supplies version, license, author and
 * category; bundle.json supplies the description and the member list.
 *
 * Usage:
 *   node scripts/skill-frontmatter-to-plugin-json.js <leaf>
 *   node scripts/skill-frontmatter-to-plugin-json.js <leaf> --write
 *   node scripts/skill-frontmatter-to-plugin-json.js <leaf> --check
 *   node scripts/skill-frontmatter-to-plugin-json.js --bundle <plugin> --write|--check
 *   node scripts/skill-frontmatter-to-plugin-json.js --bundle <plugin> --members
 *   node scripts/skill-frontmatter-to-plugin-json.js --marketplaces --write
 *   node scripts/skill-frontmatter-to-plugin-json.js --marketplaces --check
 *
 * --members validates every bundle and prints "skill <name>" / "agent <name>"
 * lines (primary member first) for scripts/sync-plugin-views.sh.
 *
 * Exit 0 on success / check match; exit 1 on error or --check mismatch.
 */
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const MAX_DESC = 1024;
const SEMVER_RE = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;
const REPOSITORY = "https://github.com/whichguy/skill-craft";
const BUNDLE_FORMAT = "skill-craft-plugin-bundle/v1";
const BUNDLE_KEYS = ["agents", "description", "format", "name", "skills"];
const NAME_RE = /^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/;
const MARKETPLACE_DESCRIPTION =
  "Portable multi-host agent skills for Grok, Claude, Cursor, and Codex.";

function fail(msg) {
  console.error(`skill-frontmatter-to-plugin-json: ${msg}`);
  process.exit(1);
}

function parseFrontmatter(text) {
  if (!text.startsWith("---\n")) {
    fail("SKILL.md must start with --- frontmatter");
  }
  const close = text.indexOf("\n---\n", 3);
  if (close < 0) {
    fail("frontmatter close --- not found");
  }
  return text.slice(4, close);
}

function scalar(fm, key) {
  const m = fm.match(new RegExp(`^${key}:\\s*(.+?)\\s*$`, "m"));
  return m ? m[1].trim() : null;
}

function flattenDescription(fm) {
  const folded = fm.match(/^description:\s*>-?\s*\n((?:[ \t]+.*\n?)*)/m);
  const literal = fm.match(/^description:\s*\|\s*\n((?:[ \t]+.*\n?)*)/m);
  const plain = fm.match(/^description:\s*(.+)$/m);
  let raw = "";
  if (folded || literal) {
    raw = (folded || literal)[1]
      .split("\n")
      .map((l) => l.replace(/^[ \t]+/, "").trimEnd())
      .filter((l) => l.length > 0)
      .join(" ");
  } else if (plain && !/^[|>]/.test(plain[1])) {
    raw = plain[1].trim();
  }
  raw = raw.replace(/\s+/g, " ").trim();
  if (!raw) {
    fail("description empty");
  }
  if (raw.length <= MAX_DESC) {
    return raw;
  }
  // Word-boundary truncate; never mid-word mid-sentence without ellipsis.
  let cut = raw.slice(0, MAX_DESC - 1);
  const sp = cut.lastIndexOf(" ");
  if (sp > MAX_DESC * 0.6) {
    cut = cut.slice(0, sp);
  }
  return cut.replace(/[.,;:]+$/, "") + "…";
}

function kindFromFm(fm) {
  const m = fm.match(/^\s+kind:\s*(\S+)\s*$/m);
  return m ? m[1] : null;
}

function metadataScalar(fm, key) {
  const m = fm.match(new RegExp(`^\\s+${key}:\\s*(.+?)\\s*$`, "m"));
  return m ? m[1].trim().replace(/^['"]|['"]$/g, "") : null;
}

// Read a direct child of the top-level metadata: block (for example
// metadata.version), ignoring deeper nested keys with the same name.
function metadataChildScalar(fm, key) {
  const lines = fm.split("\n");
  const start = lines.findIndex((line) => /^metadata:\s*$/.test(line));
  if (start < 0) return null;
  let indent = null;
  for (const line of lines.slice(start + 1)) {
    if (!line.trim()) continue;
    const lead = line.match(/^[ \t]*/)[0].length;
    if (lead === 0) break;
    if (indent === null) indent = lead;
    if (lead !== indent) continue;
    const m = line.match(new RegExp(`^[ \\t]+${key}:\\s*(.+?)\\s*$`));
    if (m) return m[1].replace(/^['"]|['"]$/g, "");
  }
  return null;
}

function memberVersion(fm) {
  return scalar(fm, "version") || metadataChildScalar(fm, "version");
}

function displayNameFromLeaf(leaf) {
  const known = {
    "c-plan": "C Plan",
    devloop: "DevLoop",
    shiploop: "ShipLoop",
  };
  if (known[leaf]) return known[leaf];
  return leaf
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function titleCase(value) {
  return value
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function shortDescriptionFromText(description) {
  if (description.length <= 120) return description;
  const cut = description.slice(0, 119);
  const boundary = cut.lastIndexOf(" ");
  return (boundary > 60 ? cut.slice(0, boundary) : cut).replace(/[.,;:]+$/, "") + "…";
}

function shortDescriptionFromFm(fm, description) {
  const declared = metadataScalar(fm, "short-description");
  if (declared) return declared;
  return shortDescriptionFromText(description);
}

function platformsFromFm(fm) {
  const match = fm.match(/^platforms:\s*\n((?:[ \t]+-\s+\S+.*\n?)*)/m);
  if (!match) return [];
  return match[1]
    .split("\n")
    .map((line) => line.match(/^\s+-\s+(.+?)\s*$/))
    .filter(Boolean)
    .map((parts) => parts[1]);
}

function buildPlugin(leaf, fm) {
  const name = scalar(fm, "name") || leaf;
  if (name !== leaf) {
    fail(`frontmatter name ${name} != leaf ${leaf}`);
  }
  const version = scalar(fm, "version");
  if (!version) {
    fail("missing version");
  }
  if (!SEMVER_RE.test(version)) {
    fail(`version must be strict semver: ${version}`);
  }
  const license = scalar(fm, "license") || "MIT";
  const description = flattenDescription(fm);
  const authorLine = scalar(fm, "author");
  const authorName = authorLine
    ? authorLine.replace(/\s*\/.*$/, "").trim() || "whichguy"
    : "whichguy";
  const kind = kindFromFm(fm);
  const keywords = ["skill-craft", leaf, "portable-skills"];
  if (kind) {
    keywords.push(kind);
  }
  // de-dupe preserve order
  const seen = new Set();
  const kw = [];
  for (const k of keywords) {
    if (!seen.has(k)) {
      seen.add(k);
      kw.push(k);
    }
  }
  return {
    name: leaf,
    version,
    description,
    author: {
      name: authorName,
      url: "https://github.com/whichguy",
    },
    homepage: REPOSITORY,
    repository: REPOSITORY,
    license,
    keywords: kw,
  };
}

function buildCursorPlugin(leaf, fm) {
  return cursorFromPlugin(buildPlugin(leaf, fm));
}

function cursorFromPlugin(plugin) {
  return {
    name: plugin.name,
    version: plugin.version,
    description: plugin.description,
    // Cursor documents name/email for author metadata. Keep its manifest to
    // that schema rather than inheriting Claude's author URL extension.
    author: {
      name: plugin.author.name,
    },
    homepage: plugin.homepage,
    repository: plugin.repository,
    license: plugin.license,
    keywords: plugin.keywords,
    // Cursor otherwise discovers this by convention. Pinning the component
    // path makes the package contract explicit without creating a second body.
    skills: "skills",
  };
}

function buildCodexPlugin(leaf, fm) {
  const plugin = buildPlugin(leaf, fm);
  const kind = kindFromFm(fm) || "portable";
  return {
    ...plugin,
    skills: "./skills/",
    interface: {
      displayName: displayNameFromLeaf(leaf),
      shortDescription: shortDescriptionFromFm(fm, plugin.description),
      longDescription: plugin.description,
      developerName: plugin.author.name,
      category: titleCase(categoryFromFm(fm)),
      capabilities: kind === "prompt-only" ? ["Read"] : ["Read", "Write"],
      defaultPrompt: [`Use $${leaf}:${leaf} for this task.`],
    },
  };
}

function categoryFromFm(fm) {
  // skill-craft's Hermes metadata has an optional category. Grok catalog
  // entries use one for consistent browsing, so general skills use its
  // documented example category while a declared source category wins.
  const m = fm.match(/^\s+category:\s*(\S+)\s*$/m);
  return m ? m[1] : "productivity";
}

function listLeaves() {
  const skillsDir = path.join(root, "skills");
  return fs
    .readdirSync(skillsDir, { withFileTypes: true })
    .filter(
      (entry) =>
        entry.isDirectory() &&
        fs.existsSync(path.join(skillsDir, entry.name, "SKILL.md"))
    )
    .map((entry) => entry.name)
    .sort();
}

function readSkillFrontmatter(leaf) {
  const skillPath = path.join(root, "skills", leaf, "SKILL.md");
  if (!fs.existsSync(skillPath)) {
    fail(`missing ${skillPath}`);
  }
  return parseFrontmatter(fs.readFileSync(skillPath, "utf8"));
}

function listBundleNames() {
  const bundlesDir = path.join(root, "bundles");
  if (!fs.existsSync(bundlesDir)) return [];
  return fs
    .readdirSync(bundlesDir, { withFileTypes: true })
    .filter(
      (entry) =>
        entry.isDirectory() &&
        fs.existsSync(path.join(bundlesDir, entry.name, "bundle.json"))
    )
    .map((entry) => entry.name)
    .sort();
}

function requireNameList(value, label, required) {
  if (!Array.isArray(value) || (required && value.length === 0)) {
    fail(`${label} must be a ${required ? "non-empty " : ""}list of names`);
  }
  if (!value.every((item) => typeof item === "string" && NAME_RE.test(item))) {
    fail(`${label} entries must be normalized names`);
  }
  if (new Set(value).size !== value.length) {
    fail(`${label} entries must be unique`);
  }
  return value;
}

function readBundleJson(name) {
  const label = `bundles/${name}/bundle.json`;
  let data;
  try {
    data = JSON.parse(fs.readFileSync(path.join(root, "bundles", name, "bundle.json"), "utf8"));
  } catch (e) {
    fail(`${label} is unreadable or invalid JSON: ${e.message}`);
  }
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    fail(`${label} must be a JSON object`);
  }
  if (JSON.stringify(Object.keys(data).sort()) !== JSON.stringify(BUNDLE_KEYS)) {
    fail(`${label} keys must be exactly ${BUNDLE_KEYS.join(", ")}`);
  }
  if (data.format !== BUNDLE_FORMAT) fail(`${label} format must be ${BUNDLE_FORMAT}`);
  if (data.name !== name || !NAME_RE.test(name)) fail(`${label} name must equal its directory`);
  if (typeof data.description !== "string" || !data.description.trim()) {
    fail(`${label} description must be a non-empty string`);
  }
  if (data.description.length > MAX_DESC) {
    fail(`${label} description exceeds ${MAX_DESC} characters`);
  }
  requireNameList(data.skills, `${label} skills`, true);
  requireNameList(data.agents, `${label} agents`, false);
  if (!data.skills.includes(name)) {
    fail(`${label} skills must include the primary member ${name}`);
  }
  return data;
}

// Validate every bundle declaration against the leaves and each other: a
// bundle may not share a name with a skills/<leaf>, and a member may belong
// to one package only. Leaf operations run this too, so a named leaf sync or
// check cannot overwrite (or pass) a colliding bundle view.
function declareBundles(leaves) {
  const leafSet = new Set(leaves);
  const owner = new Map();
  return listBundleNames().map((name) => {
    const data = readBundleJson(name);
    if (leafSet.has(name)) {
      fail(`bundle ${name} collides with source skill skills/${name}`);
    }
    for (const member of data.skills) {
      if (member !== name && leafSet.has(member)) {
        fail(`bundle ${name} member ${member} duplicates source skill skills/${member}`);
      }
      if (owner.has(member)) {
        fail(`bundle member ${member} is declared by both ${owner.get(member)} and ${name}`);
      }
      owner.set(member, name);
    }
    return {
      name,
      description: data.description,
      // Primary member first, then the declared order.
      skills: [name, ...data.skills.filter((member) => member !== name)],
      agents: data.agents,
    };
  });
}

// Load and validate every bundle (declarations, then member cards). Any
// violation fails before a caller writes a plugin view or catalog.
function loadBundles(leaves) {
  const bundles = declareBundles(leaves);
  for (const bundle of bundles) {
    const fms = {};
    for (const member of bundle.skills) {
      const cardPath = path.join(root, "bundles", bundle.name, "skills", member, "SKILL.md");
      if (!fs.existsSync(cardPath)) {
        fail(`bundles/${bundle.name}: missing declared skills/${member}/SKILL.md`);
      }
      const fm = parseFrontmatter(fs.readFileSync(cardPath, "utf8"));
      if (scalar(fm, "name") !== member) {
        fail(`bundles/${bundle.name}/skills/${member}/SKILL.md name must be ${member}`);
      }
      const version = memberVersion(fm);
      if (!version || !SEMVER_RE.test(version)) {
        fail(`bundles/${bundle.name}/skills/${member}/SKILL.md needs a semantic version or metadata.version`);
      }
      fms[member] = fm;
    }
    for (const agent of bundle.agents) {
      if (!fs.existsSync(path.join(root, "bundles", bundle.name, "agents", `${agent}.md`))) {
        fail(`bundles/${bundle.name}: missing declared agents/${agent}.md`);
      }
    }
    bundle.fms = fms;
    bundle.primary = buildPlugin(bundle.name, fms[bundle.name]);
    for (const member of bundle.skills) {
      const license = scalar(fms[member], "license") || "MIT";
      if (license !== bundle.primary.license) {
        fail(`bundles/${bundle.name}/skills/${member} license ${license} differs from primary ${bundle.primary.license}`);
      }
    }
  }
  return bundles;
}

function findBundle(name) {
  const bundle = loadBundles(listLeaves()).find((entry) => entry.name === name);
  if (!bundle) fail(`no bundles/${name}/bundle.json`);
  return bundle;
}

function buildBundlePlugin(bundle) {
  const keywords = [...bundle.primary.keywords];
  for (const member of bundle.skills) {
    if (!keywords.includes(member)) keywords.push(member);
  }
  return { ...bundle.primary, description: bundle.description, keywords };
}

function buildBundleCodexPlugin(bundle) {
  const plugin = buildBundlePlugin(bundle);
  const promptOnly = bundle.skills.every(
    (member) => kindFromFm(bundle.fms[member]) === "prompt-only"
  );
  return {
    ...plugin,
    skills: "./skills/",
    interface: {
      displayName: displayNameFromLeaf(bundle.name),
      shortDescription: shortDescriptionFromText(plugin.description),
      longDescription: plugin.description,
      developerName: plugin.author.name,
      category: titleCase(categoryFromFm(bundle.fms[bundle.name])),
      capabilities: promptOnly ? ["Read"] : ["Read", "Write"],
      defaultPrompt: bundle.skills
        .slice(0, 3)
        .map((member) => `Use $${bundle.name}:${member} for this task.`),
    },
  };
}

function readBundleProvenance(name) {
  const provenancePath = path.join(root, "bundles", name, "PROVENANCE.json");
  if (!fs.existsSync(provenancePath)) {
    fail(`bundles/${name} requires PROVENANCE.json (import it with scripts/sync-vendored-bundles.py)`);
  }
  try {
    const upstream = JSON.parse(fs.readFileSync(provenancePath, "utf8")).upstream;
    return { commit: upstream.commit, version: upstream.manifest.version };
  } catch (e) {
    fail(`bundles/${name}/PROVENANCE.json is invalid: ${e.message}`);
  }
}

function buildBundleReadme(bundle) {
  const plugin = buildBundlePlugin(bundle);
  const provenance = readBundleProvenance(bundle.name);
  const platforms = platformsFromFm(bundle.fms[bundle.name]);
  const platformText =
    platforms.length > 0 ? platforms.join(", ") : "the platforms it declares";
  const rows = bundle.skills.map((member) => {
    const fm = bundle.fms[member];
    return `| \`${member}\` | ${memberVersion(fm)} | ${kindFromFm(fm) || "portable"} | \`$${bundle.name}:${member}\` | \`/${bundle.name}:${member}\` | [SKILL.md](skills/${member}/SKILL.md) |`;
  });
  const agents =
    bundle.agents.length > 0
      ? bundle.agents.map((agent) => `[agents/${agent}.md](agents/${agent}.md)`).join(", ")
      : "none";
  return [
    `# ${displayNameFromLeaf(bundle.name)}`,
    "",
    plugin.description,
    "",
    "## Skills",
    "",
    `This plugin packages ${bundle.skills.length} skills. Agent cards: ${agents}.`,
    "",
    "| Skill | Version | Kind | Codex | Claude | Card |",
    "|-------|---------|------|-------|--------|------|",
    ...rows,
    "",
    "## Install",
    "",
    `Install the \`${bundle.name}\` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skills. Keep one track per host: use either this plugin or a skill-directory install of the same skills, not both. Skill Craft's \`install.sh\` never installs these skills.`,
    "",
    "## Use",
    "",
    `Use the installed plugin skills by their qualified names: in Codex, ask for \`$${bundle.name}:<skill>\`; in Claude, invoke \`/${bundle.name}:<skill>\`; in other hosts, select the installed plugin skill. Read the skill's SKILL.md before execution; it defines the workflow and any task-specific limits.`,
    "",
    "## Runtime and prerequisites",
    "",
    `Each skill declares its own kind and requirements; the primary skill targets ${platformText}. When a card invokes a bundled helper, resolve it from that loaded skill directory (for example, \`skills/<skill>/scripts/...\`), never from the consumer project's current directory.`,
    "",
    "## Package scope",
    "",
    "This package contains only the skills and agent cards listed above. Files that a card mentions outside its own skill directory, such as repository-level harnesses, installers or make targets, are not part of this package.",
    "",
    "## Provenance",
    "",
    `The skills and agent cards are a verbatim, hash-verified copy of upstream commit \`${provenance.commit}\` (upstream package version ${provenance.version}). Skill Craft records every file's sha256 in [bundles/${bundle.name}/PROVENANCE.json](${REPOSITORY}/blob/main/bundles/${bundle.name}/PROVENANCE.json).`,
    "",
    "## Support",
    "",
    `[Skill Craft source and issue tracker](${REPOSITORY})`,
    "",
  ].join("\n");
}

function byName(a, b) {
  return a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
}

function buildCursorMarketplace(leaves, bundles = []) {
  return {
    name: "skill-craft",
    owner: {
      name: "whichguy",
    },
    metadata: {
      description: MARKETPLACE_DESCRIPTION,
    },
    plugins: [
      ...leaves.map((leaf) => {
        const plugin = buildPlugin(leaf, readSkillFrontmatter(leaf));
        return {
          name: leaf,
          source: `./plugins/${leaf}`,
          description: plugin.description,
        };
      }),
      ...bundles.map((bundle) => ({
        name: bundle.name,
        source: `./plugins/${bundle.name}`,
        description: bundle.description,
      })),
    ].sort(byName),
  };
}

function buildGrokMarketplace(leaves, bundles = []) {
  return {
    name: "skill-craft",
    description: MARKETPLACE_DESCRIPTION,
    owner: {
      name: "whichguy",
    },
    plugins: [
      ...leaves.map((leaf) => {
        const fm = readSkillFrontmatter(leaf);
        const plugin = buildPlugin(leaf, fm);
        return {
          name: leaf,
          version: plugin.version,
          description: plugin.description,
          category: categoryFromFm(fm),
          source: {
            type: "local",
            path: `./plugins/${leaf}`,
          },
        };
      }),
      ...bundles.map((bundle) => ({
        name: bundle.name,
        version: bundle.primary.version,
        description: bundle.description,
        category: categoryFromFm(bundle.fms[bundle.name]),
        source: {
          type: "local",
          path: `./plugins/${bundle.name}`,
        },
      })),
    ].sort(byName),
  };
}

// Claude and Codex catalogs keep the historical marketplace name so installed
// plugin IDs (for example shiploop@skill-craft-market) survive the move from
// the former skill-craft-market repository into this one.
const CLAUDE_CODEX_MARKETPLACE = "skill-craft-market";
const EXTERNAL_PLUGINS = path.join(root, "catalog", "external-plugins.json");

function loadExternalPlugins(localNames) {
  if (!fs.existsSync(EXTERNAL_PLUGINS)) return [];
  let data;
  try {
    data = JSON.parse(fs.readFileSync(EXTERNAL_PLUGINS, "utf8"));
  } catch (e) {
    fail(`catalog/external-plugins.json is invalid: ${e.message}`);
  }
  const plugins = Array.isArray(data.plugins) ? data.plugins : fail("catalog/external-plugins.json needs a plugins array");
  for (const plugin of plugins) {
    const label = `catalog/external-plugins.json ${plugin && plugin.name}`;
    if (!plugin || !NAME_RE.test(plugin.name || "")) fail(`${label}: invalid name`);
    if (localNames.has(plugin.name)) fail(`${label}: also published from this repository`);
    if ("hooks" in plugin) fail(`${label}: must not declare hooks`);
    if (!SEMVER_RE.test(plugin.version || "")) fail(`${label}: needs a semantic version`);
    const source = plugin.source || {};
    if (typeof source !== "object" || !/^[0-9a-f]{40}$/.test(source.sha || "")) {
      fail(`${label}: an external source needs a full 40-character sha pin`);
    }
  }
  return plugins;
}

function catalogEntries(leaves, bundles, source) {
  const entry = (name, plugin, category) => ({
    name,
    description: plugin.description,
    version: plugin.version,
    author: plugin.author,
    source: source(name),
    policy: { installation: "AVAILABLE", authentication: "ON_INSTALL" },
    category,
  });
  return [
    ...leaves.map((leaf) => entry(leaf, buildPlugin(leaf, readSkillFrontmatter(leaf)), "Productivity")),
    ...bundles.map((bundle) => entry(bundle.name, buildBundlePlugin(bundle), "Productivity")),
  ];
}

function buildClaudeMarketplace(leaves, bundles = []) {
  const local = catalogEntries(leaves, bundles, (name) => `./plugins/${name}`);
  return {
    name: CLAUDE_CODEX_MARKETPLACE,
    owner: { name: "whichguy", url: "https://github.com/whichguy" },
    description: MARKETPLACE_DESCRIPTION,
    interface: { displayName: "Skill Craft" },
    plugins: [...local, ...loadExternalPlugins(new Set(local.map((p) => p.name)))].sort(byName),
  };
}

function buildCodexMarketplace(leaves, bundles = []) {
  const local = catalogEntries(leaves, bundles, (name) => ({ source: "local", path: `./plugins/${name}` }));
  return {
    name: CLAUDE_CODEX_MARKETPLACE,
    interface: { displayName: "Skill Craft" },
    plugins: [...local, ...loadExternalPlugins(new Set(local.map((p) => p.name)))].sort(byName),
  };
}

function jsonText(value) {
  return JSON.stringify(value, null, 2) + "\n";
}

function writeGeneratedJson(outPath, value) {
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, jsonText(value));
}

function checkGeneratedJson(outPath, value, label) {
  if (!fs.existsSync(outPath)) {
    fail(`missing ${outPath}`);
  }
  const existing = fs.readFileSync(outPath, "utf8");
  try {
    JSON.parse(existing);
  } catch (e) {
    fail(`invalid JSON ${outPath}: ${e.message}`);
  }
  if (existing !== jsonText(value)) {
    fail(`${label} out of sync with SKILL.md derivation`);
  }
}

function checkClaudePlugin(outPath, plugin, leaf) {
  if (!fs.existsSync(outPath)) {
    fail(`missing ${outPath}`);
  }
  const existing = fs.readFileSync(outPath, "utf8");
  let parsed;
  try {
    parsed = JSON.parse(existing);
  } catch (e) {
    fail(`invalid JSON ${outPath}: ${e.message}`);
  }
  // Preserve the Claude check's compatibility contract: validate its
  // load-bearing frontmatter-derived fields while allowing Claude additions.
  const keys = ["name", "version", "description", "license"];
  for (const k of keys) {
    if (parsed[k] !== plugin[k]) {
      fail(
        `${leaf} plugin.json ${k} mismatch\n  want: ${JSON.stringify(plugin[k])}\n  got:  ${JSON.stringify(parsed[k])}`
      );
    }
  }
  if (!parsed.author || parsed.author.name !== plugin.author.name) {
    fail(`${leaf} plugin.json author.name mismatch`);
  }
}

function packageReadmePath(leaf) {
  return path.join(root, "plugins", leaf, "README.md");
}

function buildPackageReadme(leaf, fm) {
  const plugin = buildPlugin(leaf, fm);
  const kind = kindFromFm(fm) || "portable";
  const platforms = platformsFromFm(fm);
  const authoredGuide = path.join(root, "skills", leaf, "README.md");
  const guide = fs.existsSync(authoredGuide)
    ? `This package preserves its authored guide at [skills/${leaf}/README.md](skills/${leaf}/README.md).`
    : `The packaged [skill instructions](skills/${leaf}/SKILL.md) are the authoritative guide.`;
  const platformText = platforms.length > 0 ? platforms.join(", ") : "the platforms declared by the skill";
  return [
    `# ${displayNameFromLeaf(leaf)}`,
    "",
    plugin.description,
    "",
    "## Install",
    "",
    `Install the \`${leaf}\` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.`,
    "",
    "## Use",
    "",
    `Use the installed plugin skill: in Codex, ask for \`$${leaf}:${leaf}\`; in Claude, invoke \`/${leaf}:${leaf}\`; in other hosts, select the installed plugin skill. Read [SKILL.md](skills/${leaf}/SKILL.md) before execution; it defines the workflow and any task-specific limits.`,
    "",
    "## Runtime and prerequisites",
    "",
    `This is a \`${kind}\` skill for ${platformText}. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, \`skills/${leaf}/scripts/...\`), never from the consumer project's current directory.`,
    "",
    "## Documentation",
    "",
    guide,
    "",
    "## Support",
    "",
    `[Skill Craft source and issue tracker](${REPOSITORY})`,
    "",
  ].join("\n");
}

function writeGeneratedText(outPath, value) {
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, value);
}

function checkGeneratedText(outPath, value, label) {
  if (!fs.existsSync(outPath)) {
    fail(`missing ${outPath}`);
  }
  if (fs.readFileSync(outPath, "utf8") !== value) {
    fail(`${label} out of sync with SKILL.md derivation`);
  }
}

function readmeInventory(leaves, bundles = []) {
  const outPath = path.join(root, "README.md");
  const current = fs.readFileSync(outPath, "utf8");
  const start = "<!-- skill-craft:inventory:start -->";
  const end = "<!-- skill-craft:inventory:end -->";
  if (current.split(start).length !== 2 || current.split(end).length !== 2 ||
      current.indexOf(end) < current.indexOf(start)) {
    fail("README inventory requires exactly one ordered start/end marker pair");
  }
  const cell = (text) => text.replace(/\|/g, "\\|").replace(/[\r\n]+/g, " ");
  const summary = (text) => {
    if (text.length <= 180) return cell(text);
    const prefix = text.slice(0, 179);
    return cell(prefix.slice(0, prefix.lastIndexOf(" ")) + "…");
  };
  const rows = leaves.map((leaf) => {
    const plugin = buildPlugin(leaf, readSkillFrontmatter(leaf));
    return `| [${leaf}](skills/${leaf}/SKILL.md) | ${cell(plugin.version)} | ${summary(plugin.description)} |`;
  });
  // A checkout without bundles renders exactly the historical skills table.
  const bundleBlock =
    bundles.length === 0
      ? []
      : [
          "",
          `**${bundles.length} plugin bundle${bundles.length === 1 ? "" : "s"}.** Marketplace-only: \`install.sh\` never installs bundle members. Generated from \`bundles/<plugin>/bundle.json\` and member frontmatter by \`scripts/sync-plugin-views.sh\`.`,
          "",
          "| Plugin | Version | Skills | Purpose |",
          "|--------|---------|--------|---------|",
          ...bundles.map(
            (bundle) =>
              `| [${bundle.name}](bundles/${bundle.name}/bundle.json) | ${cell(bundle.primary.version)} | ${cell(bundle.skills.join(", "))} | ${summary(bundle.description)} |`
          ),
        ];
  const inventory = [
    start,
    "",
    `**${leaves.length} skills.** Generated from skill frontmatter by \`scripts/sync-plugin-views.sh\`.`,
    "",
    "| Skill | Version | Purpose |",
    "|-------|---------|---------|",
    ...rows,
    ...bundleBlock,
    "",
    end,
  ].join("\n");
  const wanted = current.slice(0, current.indexOf(start)) + inventory +
    current.slice(current.indexOf(end) + end.length);
  return { outPath, current, wanted };
}

function runMarketplaces(doWrite, doCheck) {
  const leaves = listLeaves();
  if (leaves.length === 0) {
    fail("no source skills; refusing empty distribution");
  }
  const bundles = loadBundles(leaves);
  const inventory = doWrite || doCheck ? readmeInventory(leaves, bundles) : null;
  const targets = [
    {
      outPath: path.join(root, ".cursor-plugin", "marketplace.json"),
      value: buildCursorMarketplace(leaves, bundles),
      label: "Cursor marketplace index",
    },
    {
      outPath: path.join(root, ".grok-plugin", "marketplace.json"),
      value: buildGrokMarketplace(leaves, bundles),
      label: "Grok marketplace index",
    },
    {
      outPath: path.join(root, ".claude-plugin", "marketplace.json"),
      value: buildClaudeMarketplace(leaves, bundles),
      label: "Claude marketplace index",
    },
    {
      outPath: path.join(root, ".agents", "plugins", "marketplace.json"),
      value: buildCodexMarketplace(leaves, bundles),
      label: "Codex marketplace index",
    },
  ];

  if (doCheck) {
    for (const target of targets) {
      checkGeneratedJson(target.outPath, target.value, target.label);
    }
    if (inventory.current !== inventory.wanted) {
      fail("README inventory out of sync with SKILL.md derivation");
    }
    process.stdout.write(
      `skill-frontmatter-to-plugin-json: CHECK OK marketplaces (${leaves.length} skills, ${bundles.length} bundle${bundles.length === 1 ? "" : "s"})\n`
    );
    return;
  }

  if (doWrite) {
    for (const target of targets) {
      writeGeneratedJson(target.outPath, target.value);
      process.stdout.write(
        `skill-frontmatter-to-plugin-json: wrote ${path.relative(root, target.outPath)}\n`
      );
    }
    fs.writeFileSync(inventory.outPath, inventory.wanted);
    process.stdout.write("skill-frontmatter-to-plugin-json: updated README inventory\n");
    return;
  }

  process.stdout.write(
    jsonText({
      cursor: targets[0].value,
      grok: targets[1].value,
      claude: targets[2].value,
      codex: targets[3].value,
    })
  );
}

function parseArgs(args) {
  const options = { write: false, check: false, marketplaces: false, members: false, bundle: null, leaves: [] };
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "--write") options.write = true;
    else if (arg === "--check") options.check = true;
    else if (arg === "--marketplaces") options.marketplaces = true;
    else if (arg === "--members") options.members = true;
    else if (arg === "--bundle") {
      if (index + 1 >= args.length || args[index + 1].startsWith("--")) {
        fail("--bundle requires a plugin name");
      }
      options.bundle = args[index + 1];
      index += 1;
    } else if (arg.startsWith("--")) fail(`unknown option ${arg}`);
    else options.leaves.push(arg);
  }
  if (options.write && options.check) {
    fail("--write and --check are mutually exclusive");
  }
  return options;
}

function writeOrCheckPackage(name, generated, doWrite, doCheck) {
  const base = path.join(root, "plugins", name);
  const claudePath = path.join(base, ".claude-plugin", "plugin.json");
  const cursorPath = path.join(base, ".cursor-plugin", "plugin.json");
  const codexPath = path.join(base, ".codex-plugin", "plugin.json");
  const readmePath = packageReadmePath(name);

  if (doCheck) {
    checkClaudePlugin(claudePath, generated.plugin, name);
    checkGeneratedJson(cursorPath, generated.cursor, `${name} Cursor plugin manifest`);
    checkGeneratedJson(codexPath, generated.codex, `${name} Codex plugin manifest`);
    checkGeneratedText(readmePath, generated.readme, `${name} package README`);
    process.stdout.write(`skill-frontmatter-to-plugin-json: CHECK OK ${name}\n`);
    return;
  }

  if (doWrite) {
    writeGeneratedJson(claudePath, generated.plugin);
    writeGeneratedJson(cursorPath, generated.cursor);
    writeGeneratedJson(codexPath, generated.codex);
    writeGeneratedText(readmePath, generated.readme);
    process.stdout.write(
      `skill-frontmatter-to-plugin-json: wrote plugins/${name} host manifests and README.md\n`
    );
    return;
  }

  process.stdout.write(jsonText(generated.plugin));
}

function main() {
  const args = process.argv.slice(2);
  if (args.length === 0 || args.includes("-h") || args.includes("--help")) {
    console.log(
      "Usage: skill-frontmatter-to-plugin-json.js <leaf> [--write|--check]\n" +
        "       skill-frontmatter-to-plugin-json.js --bundle <plugin> [--write|--check|--members]\n" +
        "       skill-frontmatter-to-plugin-json.js --marketplaces [--write|--check]"
    );
    process.exit(args.length === 0 ? 1 : 0);
  }
  const options = parseArgs(args);

  if (options.marketplaces) {
    if (options.leaves.length > 0 || options.bundle !== null) {
      fail("--marketplaces does not take a leaf or bundle");
    }
    runMarketplaces(options.write, options.check);
    return;
  }

  if (options.bundle !== null) {
    if (options.leaves.length > 0) {
      fail("--bundle does not take a leaf");
    }
    const bundle = findBundle(options.bundle);
    if (options.members) {
      const lines = [
        ...bundle.skills.map((member) => `skill ${member}`),
        ...bundle.agents.map((agent) => `agent ${agent}`),
      ];
      process.stdout.write(lines.join("\n") + "\n");
      return;
    }
    writeOrCheckPackage(
      bundle.name,
      {
        plugin: buildBundlePlugin(bundle),
        cursor: cursorFromPlugin(buildBundlePlugin(bundle)),
        codex: buildBundleCodexPlugin(bundle),
        readme: buildBundleReadme(bundle),
      },
      options.write,
      options.check
    );
    return;
  }

  if (options.members) {
    fail("--members requires --bundle");
  }
  if (options.leaves.length !== 1) {
    fail("missing leaf");
  }
  const leaf = options.leaves[0];
  declareBundles(listLeaves());
  const fm = readSkillFrontmatter(leaf);
  writeOrCheckPackage(
    leaf,
    {
      plugin: buildPlugin(leaf, fm),
      cursor: buildCursorPlugin(leaf, fm),
      codex: buildCodexPlugin(leaf, fm),
      readme: buildPackageReadme(leaf, fm),
    },
    options.write,
    options.check
  );
}

main();
