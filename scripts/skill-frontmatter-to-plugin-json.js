#!/usr/bin/env node
"use strict";

/**
 * Derive the one skill-craft plugin package (Claude, Codex, Cursor manifests,
 * hooks, README) and the marketplace indexes (Claude, Codex, Cursor, Grok) from
 * every skills/<leaf>/SKILL.md plus catalog/skill-craft-plugin.json.
 *
 * Every skill ships in a single plugin named skill-craft, so hosts namespace
 * them as skill-craft:<leaf> (Claude /skill-craft:shiploop, Codex
 * $skill-craft:shiploop).
 *
 * Usage:
 *   node scripts/skill-frontmatter-to-plugin-json.js --package [--write|--check]
 *   node scripts/skill-frontmatter-to-plugin-json.js --marketplaces [--write|--check]
 *
 * Exit 0 on success / check match; exit 1 on error or --check mismatch.
 */
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const MAX_DESC = 1024;
const SEMVER_RE = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;
const REPOSITORY = "https://github.com/whichguy/skill-craft";
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

// The plugin that carries every skill. Its name is the marketplace name, so
// every host namespaces the skills as skill-craft:<leaf>. Its version is
// release output: only scripts/release.py writes catalog/skill-craft-plugin.json.
const PLUGIN_NAME = "skill-craft";
const BUNDLE_SOURCE = path.join(root, "catalog", "skill-craft-plugin.json");

function readBundle() {
  let data;
  try {
    data = JSON.parse(fs.readFileSync(BUNDLE_SOURCE, "utf8"));
  } catch (e) {
    fail(`catalog/skill-craft-plugin.json is missing or invalid: ${e.message}`);
  }
  if (!data || typeof data !== "object" || Object.keys(data).sort().join() !== "description,name,version") {
    fail("catalog/skill-craft-plugin.json must hold exactly name, version and description");
  }
  if (data.name !== PLUGIN_NAME) fail(`catalog/skill-craft-plugin.json name must be ${PLUGIN_NAME}`);
  if (!SEMVER_RE.test(data.version || "")) fail("catalog/skill-craft-plugin.json version must be strict semver");
  if (typeof data.description !== "string" || !data.description.trim() || data.description.length > MAX_DESC) {
    fail("catalog/skill-craft-plugin.json description must be non-empty and at most 1024 characters");
  }
  return data;
}

function buildBundlePlugin(leaves) {
  const bundle = readBundle();
  // Validates every card (name == leaf, strict semver) before packaging it.
  for (const leaf of leaves) buildPlugin(leaf, readSkillFrontmatter(leaf));
  return {
    name: PLUGIN_NAME,
    version: bundle.version,
    description: bundle.description,
    author: {
      name: "whichguy",
      url: "https://github.com/whichguy",
    },
    homepage: REPOSITORY,
    repository: REPOSITORY,
    license: "MIT",
    keywords: [PLUGIN_NAME, "portable-skills", ...leaves],
  };
}

function buildCursorPlugin(leaves, hookFiles = {}) {
  const cursor = cursorFromPlugin(buildBundlePlugin(leaves));
  if (hookFiles[HOOK_FILES.cursor]) cursor.hooks = `./${HOOK_FILES.cursor}`;
  return cursor;
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

function buildCodexPlugin(leaves, hookFiles = {}) {
  const plugin = buildBundlePlugin(leaves);
  const promptOnly = leaves.every((leaf) => kindFromFm(readSkillFrontmatter(leaf)) === "prompt-only");
  const featured = ["shiploop", "improve", "ask-agent"].filter((leaf) => leaves.includes(leaf));
  return {
    ...plugin,
    skills: "./skills/",
    ...(hookFiles[HOOK_FILES.codex] ? { hooks: `./${HOOK_FILES.codex}` } : {}),
    interface: {
      displayName: "Skill Craft",
      shortDescription: shortDescriptionFromText(plugin.description),
      longDescription: plugin.description,
      developerName: plugin.author.name,
      category: "Productivity",
      capabilities: promptOnly ? ["Read"] : ["Read", "Write"],
      defaultPrompt: (featured.length ? featured : leaves.slice(0, 1))
        .map((leaf) => `Use $${PLUGIN_NAME}:${leaf} for this task.`),
    },
  };
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

// Host hooks: an optional skills/<leaf>/host-hooks.json declares host-neutral
// hooks; each host gets its own generated file, in its own format and plugin
// root variable, and may only run an executable in the skill's own scripts/.
const HOOK_HOSTS = ["claude", "codex", "cursor", "grok"];
// after-shell: after a shell command. turn-end: when the host is about to end
// the agent's turn (Claude-format Stop; Cursor stop).
const HOOK_EVENTS = new Set(["after-shell", "turn-end"]);
// Cursor stops re-prompting after loop_limit follow-ups (default 5); a turn-end
// hook owns its own loop limits, so the host limit is only a backstop.
const CURSOR_TURN_END_LOOP_LIMIT = 50;
const HOOK_ID_RE = /^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/;
const HOOK_SCRIPT_RE = /^scripts\/[A-Za-z0-9._-]+$/;
const HOOK_FILES = {
  claude: "hooks/hooks.json", // Claude's default path; Grok loads Claude plugin hooks.
  codex: "hooks/codex.json",
  cursor: "hooks/cursor.json",
};

function readHostHooks(leaf) {
  const declPath = path.join(root, "skills", leaf, "host-hooks.json");
  if (!fs.existsSync(declPath)) return null;
  let decl;
  try {
    decl = JSON.parse(fs.readFileSync(declPath, "utf8"));
  } catch (e) {
    fail(`invalid JSON ${declPath}: ${e.message}`);
  }
  const label = `skills/${leaf}/host-hooks.json`;
  if (!decl || typeof decl !== "object" || Array.isArray(decl) ||
      Object.keys(decl).join() !== "hooks" || !Array.isArray(decl.hooks) || decl.hooks.length === 0) {
    fail(`${label}: must be {"hooks": [ ... ]} with at least one hook`);
  }
  const ids = new Set();
  for (const hook of decl.hooks) {
    const keys = Object.keys(hook || {}).sort().join();
    if (keys !== "event,hosts,id,script,timeout") {
      fail(`${label}: each hook has exactly id, event, script, timeout and hosts`);
    }
    if (!HOOK_ID_RE.test(hook.id) || ids.has(hook.id)) fail(`${label}: invalid or duplicate id ${hook.id}`);
    ids.add(hook.id);
    if (!HOOK_EVENTS.has(hook.event)) fail(`${label}: ${hook.id}: unsupported event ${hook.event}`);
    if (!HOOK_SCRIPT_RE.test(hook.script)) fail(`${label}: ${hook.id}: script must be scripts/<file>`);
    const script = path.join(root, "skills", leaf, hook.script);
    let stat;
    try {
      stat = fs.lstatSync(script);
    } catch (e) {
      fail(`${label}: ${hook.id}: missing script ${hook.script}`);
    }
    if (!stat.isFile() || (stat.mode & 0o111) === 0) {
      fail(`${label}: ${hook.id}: script ${hook.script} must be an executable regular file`);
    }
    if (!Number.isInteger(hook.timeout) || hook.timeout < 1 || hook.timeout > 60) {
      fail(`${label}: ${hook.id}: timeout must be an integer from 1 to 60`);
    }
    if (!Array.isArray(hook.hosts) || hook.hosts.length === 0 ||
        new Set(hook.hosts).size !== hook.hosts.length || !hook.hosts.every((h) => HOOK_HOSTS.includes(h))) {
      fail(`${label}: ${hook.id}: hosts must be distinct values from ${HOOK_HOSTS.join(", ")}`);
    }
  }
  return decl;
}

// Merge every skill's declared hooks into the plugin's one file per host.
function buildHostHooks(leaves) {
  const all = [];
  for (const leaf of leaves) {
    const decl = readHostHooks(leaf);
    if (decl) all.push(...decl.hooks.map((hook) => ({ ...hook, leaf })));
  }
  if (all.length === 0) return {};
  const files = {};
  const decl = { hooks: all };
  // Unquoted: Grok does not strip quotes and would read the quoted path as a file
  // name relative to the hooks folder. Plugin roots contain no spaces.
  const command = (variable, hook) => `${variable}/skills/${hook.leaf}/${hook.script}`;
  const entry = (variable, hook) => ({ type: "command", command: command(variable, hook), timeout: hook.timeout });
  const claudeShaped = (variable, hooks) => {
    const shell = hooks.filter((hook) => hook.event === "after-shell");
    const turnEnd = hooks.filter((hook) => hook.event === "turn-end");
    const events = {};
    if (shell.length) events.PostToolUse = [{ matcher: "Bash", hooks: shell.map((hook) => entry(variable, hook)) }];
    if (turnEnd.length) events.Stop = [{ hooks: turnEnd.map((hook) => entry(variable, hook)) }];
    return { hooks: events };
  };
  const forHost = (...hosts) => decl.hooks.filter((hook) => hosts.some((h) => hook.hosts.includes(h)));
  const claude = forHost("claude", "grok");
  if (claude.length) files[HOOK_FILES.claude] = claudeShaped("${CLAUDE_PLUGIN_ROOT}", claude);
  const codex = forHost("codex");
  if (codex.length) files[HOOK_FILES.codex] = claudeShaped("$PLUGIN_ROOT", codex);
  const cursor = forHost("cursor");
  if (cursor.length) {
    const events = {};
    const shell = cursor.filter((hook) => hook.event === "after-shell");
    const turnEnd = cursor.filter((hook) => hook.event === "turn-end");
    if (shell.length) {
      events.afterShellExecution = shell.map((hook) => ({
        command: command("${CURSOR_PLUGIN_ROOT}", hook), timeout: hook.timeout,
      }));
    }
    if (turnEnd.length) {
      events.stop = turnEnd.map((hook) => ({
        command: command("${CURSOR_PLUGIN_ROOT}", hook), timeout: hook.timeout,
        loop_limit: CURSOR_TURN_END_LOOP_LIMIT,
      }));
    }
    files[HOOK_FILES.cursor] = { version: 1, hooks: events };
  }
  return files;
}

function byName(a, b) {
  return a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
}

function buildCursorMarketplace(leaves) {
  const plugin = buildBundlePlugin(leaves);
  return {
    name: MARKETPLACE,
    owner: {
      name: "whichguy",
    },
    metadata: {
      description: MARKETPLACE_DESCRIPTION,
    },
    plugins: [{ name: PLUGIN_NAME, source: `./plugins/${PLUGIN_NAME}`, description: plugin.description }],
  };
}

function buildGrokMarketplace(leaves) {
  const plugin = buildBundlePlugin(leaves);
  return {
    name: MARKETPLACE,
    description: MARKETPLACE_DESCRIPTION,
    owner: {
      name: "whichguy",
    },
    plugins: [{
      name: PLUGIN_NAME,
      version: plugin.version,
      description: plugin.description,
      category: "productivity",
      source: {
        type: "local",
        path: `./plugins/${PLUGIN_NAME}`,
      },
    }],
  };
}

// One marketplace name on every host; install IDs are skill-craft@whichguy.
const MARKETPLACE = "whichguy";
const EXTERNAL_PLUGINS = path.join(root, "catalog", "external-plugins.json");
const EXTERNAL_KEYS = new Set(["name", "description", "version", "author", "source", "policy", "category"]);
const GITHUB_REPO_RE = /^https:\/\/github\.com\/([A-Za-z0-9-]+)\/([A-Za-z0-9._-]+?)(?:\.git)?$/;

function loadExternalPlugins(localNames) {
  if (!fs.existsSync(EXTERNAL_PLUGINS)) return [];
  let data;
  try {
    data = JSON.parse(fs.readFileSync(EXTERNAL_PLUGINS, "utf8"));
  } catch (e) {
    fail(`catalog/external-plugins.json is invalid: ${e.message}`);
  }
  const plugins = Array.isArray(data.plugins) ? data.plugins : fail("catalog/external-plugins.json needs a plugins array");
  const seen = new Set();
  const nonEmpty = (value) => typeof value === "string" && value.trim() !== "";
  for (const plugin of plugins) {
    const label = `catalog/external-plugins.json ${plugin && plugin.name}`;
    if (!plugin || typeof plugin !== "object" || !NAME_RE.test(plugin.name || "")) fail(`${label}: invalid name`);
    if (localNames.has(plugin.name)) fail(`${label}: also published from this repository`);
    if (seen.has(plugin.name.toLowerCase())) fail(`${label}: listed more than once`);
    seen.add(plugin.name.toLowerCase());
    // Entries are copied verbatim into both catalogs, so only known catalog
    // fields may appear (no hooks, mcpServers or other components).
    for (const key of Object.keys(plugin)) {
      if (!EXTERNAL_KEYS.has(key)) fail(`${label}: unexpected key ${key}`);
    }
    if (!SEMVER_RE.test(plugin.version || "")) fail(`${label}: needs a semantic version`);
    if (!nonEmpty(plugin.description)) fail(`${label}: needs a description`);
    if (!nonEmpty(plugin.category)) fail(`${label}: needs a category`);
    const policy = plugin.policy || {};
    if (policy.installation !== "AVAILABLE" || policy.authentication !== "ON_INSTALL" || Object.keys(policy).length !== 2) {
      fail(`${label}: policy must be {installation: AVAILABLE, authentication: ON_INSTALL}`);
    }
    const source = plugin.source;
    if (!source || typeof source !== "object" || !["url", "git-subdir"].includes(source.source)) {
      fail(`${label}: source.source must be url or git-subdir`);
    }
    const repo = GITHUB_REPO_RE.exec(typeof source.url === "string" ? source.url : "");
    if (!repo) fail(`${label}: source.url must be https://github.com/<owner>/<repo>`);
    if (`${repo[1]}/${repo[2]}`.toLowerCase() === "whichguy/skill-craft") {
      fail(`${label}: source.url points at this repository`);
    }
    if (source.source === "git-subdir") {
      const sub = source.path;
      if (!nonEmpty(sub) || sub.startsWith("/") || sub.includes("\\") ||
          sub.split("/").some((part) => part === "" || part === "." || part === "..")) {
        fail(`${label}: git-subdir needs a relative path inside the repository`);
      }
    } else if ("path" in source) {
      fail(`${label}: a url source takes no path`);
    }
    if ("ref" in source && !nonEmpty(source.ref)) fail(`${label}: source.ref must be a non-empty string`);
    if (!/^[0-9a-f]{40}$/.test(source.sha || "")) {
      fail(`${label}: an external source needs a full 40-character sha pin`);
    }
  }
  return plugins;
}

function catalogEntry(leaves, source) {
  const plugin = buildBundlePlugin(leaves);
  return {
    name: PLUGIN_NAME,
    description: plugin.description,
    version: plugin.version,
    author: plugin.author,
    source,
    policy: { installation: "AVAILABLE", authentication: "ON_INSTALL" },
    category: "Productivity",
  };
}

// External plugins may not reuse the plugin name or any bundled skill name.
function reservedNames(leaves) {
  return new Set([PLUGIN_NAME, ...leaves]);
}

function buildClaudeMarketplace(leaves) {
  const local = catalogEntry(leaves, `./plugins/${PLUGIN_NAME}`);
  return {
    name: MARKETPLACE,
    owner: { name: "whichguy", url: "https://github.com/whichguy" },
    description: MARKETPLACE_DESCRIPTION,
    interface: { displayName: "Skill Craft" },
    plugins: [local, ...loadExternalPlugins(reservedNames(leaves))].sort(byName),
  };
}

function buildCodexMarketplace(leaves) {
  const local = catalogEntry(leaves, { source: "local", path: `./plugins/${PLUGIN_NAME}` });
  return {
    name: MARKETPLACE,
    interface: { displayName: "Skill Craft" },
    plugins: [local, ...loadExternalPlugins(reservedNames(leaves))].sort(byName),
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

function checkClaudePlugin(outPath, plugin, name) {
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
        `${name} plugin.json ${k} mismatch\n  want: ${JSON.stringify(plugin[k])}\n  got:  ${JSON.stringify(parsed[k])}`
      );
    }
  }
  if (!parsed.author || parsed.author.name !== plugin.author.name) {
    fail(`${name} plugin.json author.name mismatch`);
  }
}

function buildPackageReadme(leaves) {
  const plugin = buildBundlePlugin(leaves);
  const cell = (text) => text.replace(/\|/g, "\\|").replace(/[\r\n]+/g, " ");
  const rows = leaves.map((leaf) => {
    const fm = readSkillFrontmatter(leaf);
    const card = buildPlugin(leaf, fm);
    return `| [${leaf}](skills/${leaf}/SKILL.md) | \`/${PLUGIN_NAME}:${leaf}\` | ${cell(card.version)} | ${cell(shortDescriptionFromFm(fm, card.description))} |`;
  });
  return [
    "# Skill Craft",
    "",
    plugin.description,
    "",
    "## Install",
    "",
    `Add the \`${MARKETPLACE}\` marketplace, install \`${PLUGIN_NAME}@${MARKETPLACE}\`, then start a fresh host session so it loads the packaged skills.`,
    "",
    "## Use",
    "",
    `Every skill is namespaced by this plugin: in Claude, invoke \`/${PLUGIN_NAME}:<skill>\` (for example \`/${PLUGIN_NAME}:shiploop\`); in Codex, ask for \`$${PLUGIN_NAME}:<skill>\`; in other hosts, select the installed plugin skill. Read each skill's SKILL.md before execution; it defines the workflow and any task-specific limits. When a skill invokes a bundled helper, resolve it from the loaded skill directory (for example, \`skills/<skill>/scripts/...\`), never from the consumer project's current directory.`,
    "",
    "## Skills",
    "",
    "| Skill | Claude command | Version | Purpose |",
    "|-------|----------------|---------|---------|",
    ...rows,
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

function readmeInventory(leaves) {
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
  const inventory = [
    start,
    "",
    `**${leaves.length} skills.** Generated from skill frontmatter by \`scripts/sync-plugin-views.sh\`.`,
    "",
    "| Skill | Version | Purpose |",
    "|-------|---------|---------|",
    ...rows,
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
  const inventory = doWrite || doCheck ? readmeInventory(leaves) : null;
  const targets = [
    {
      outPath: path.join(root, ".cursor-plugin", "marketplace.json"),
      value: buildCursorMarketplace(leaves),
      label: "Cursor marketplace index",
    },
    {
      outPath: path.join(root, ".grok-plugin", "marketplace.json"),
      value: buildGrokMarketplace(leaves),
      label: "Grok marketplace index",
    },
    {
      outPath: path.join(root, ".claude-plugin", "marketplace.json"),
      value: buildClaudeMarketplace(leaves),
      label: "Claude marketplace index",
    },
    {
      outPath: path.join(root, ".agents", "plugins", "marketplace.json"),
      value: buildCodexMarketplace(leaves),
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
      `skill-frontmatter-to-plugin-json: CHECK OK marketplaces (${leaves.length} skills)\n`
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
  const options = { write: false, check: false, marketplaces: false, package: false };
  for (const arg of args) {
    if (arg === "--write") options.write = true;
    else if (arg === "--check") options.check = true;
    else if (arg === "--marketplaces") options.marketplaces = true;
    else if (arg === "--package") options.package = true;
    else fail(`unknown argument ${arg}`);
  }
  if (options.write && options.check) {
    fail("--write and --check are mutually exclusive");
  }
  if (options.marketplaces === options.package) {
    fail("choose exactly one of --package or --marketplaces");
  }
  return options;
}

function writeOrCheckPackage(generated, doWrite, doCheck) {
  const name = PLUGIN_NAME;
  const base = path.join(root, "plugins", name);
  const claudePath = path.join(base, ".claude-plugin", "plugin.json");
  const cursorPath = path.join(base, ".cursor-plugin", "plugin.json");
  const codexPath = path.join(base, ".codex-plugin", "plugin.json");
  const readmePath = path.join(base, "README.md");

  const hookPaths = Object.keys(generated.hooks || {});
  if (doCheck) {
    checkClaudePlugin(claudePath, generated.plugin, name);
    checkGeneratedJson(cursorPath, generated.cursor, `${name} Cursor plugin manifest`);
    checkGeneratedJson(codexPath, generated.codex, `${name} Codex plugin manifest`);
    checkGeneratedText(readmePath, generated.readme, `${name} package README`);
    for (const rel of hookPaths) {
      checkGeneratedJson(path.join(base, rel), generated.hooks[rel], `${name} ${rel}`);
    }
    const hookDir = path.join(base, "hooks");
    const present = fs.existsSync(hookDir) ? fs.readdirSync(hookDir).map((f) => `hooks/${f}`).sort() : [];
    if (present.join() !== [...hookPaths].sort().join()) {
      fail(`${name} hooks/ holds ${present.join(", ") || "nothing"}; host-hooks.json generates ${hookPaths.join(", ") || "nothing"}`);
    }
    process.stdout.write(`skill-frontmatter-to-plugin-json: CHECK OK ${name}\n`);
    return;
  }

  if (doWrite) {
    writeGeneratedJson(claudePath, generated.plugin);
    writeGeneratedJson(cursorPath, generated.cursor);
    writeGeneratedJson(codexPath, generated.codex);
    writeGeneratedText(readmePath, generated.readme);
    const hookDir = path.join(base, "hooks");
    fs.rmSync(hookDir, { recursive: true, force: true });
    for (const rel of hookPaths) writeGeneratedJson(path.join(base, rel), generated.hooks[rel]);
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
      "Usage: skill-frontmatter-to-plugin-json.js --package [--write|--check]\n" +
        "       skill-frontmatter-to-plugin-json.js --marketplaces [--write|--check]"
    );
    process.exit(args.length === 0 ? 1 : 0);
  }
  const options = parseArgs(args);

  if (options.marketplaces) {
    runMarketplaces(options.write, options.check);
    return;
  }

  const leaves = listLeaves();
  if (leaves.length === 0) {
    fail("no source skills; refusing empty distribution");
  }
  const hooks = buildHostHooks(leaves);
  writeOrCheckPackage(
    {
      plugin: buildBundlePlugin(leaves),
      cursor: buildCursorPlugin(leaves, hooks),
      codex: buildCodexPlugin(leaves, hooks),
      readme: buildPackageReadme(leaves),
      hooks,
    },
    options.write,
    options.check
  );
}

main();
