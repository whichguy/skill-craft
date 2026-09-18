#!/usr/bin/env node
"use strict";

/**
 * Derive plugin manifests and marketplace indexes from skills/<leaf>/SKILL.md
 * frontmatter.
 *
 * Usage:
 *   node scripts/skill-frontmatter-to-plugin-json.js <leaf>
 *   node scripts/skill-frontmatter-to-plugin-json.js <leaf> --write
 *   node scripts/skill-frontmatter-to-plugin-json.js <leaf> --check
 *   node scripts/skill-frontmatter-to-plugin-json.js --marketplaces --write
 *   node scripts/skill-frontmatter-to-plugin-json.js --marketplaces --check
 *
 * Exit 0 on success / check match; exit 1 on error or --check mismatch.
 */
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const MAX_DESC = 1024;
const SEMVER_RE = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;
const REPOSITORY = "https://github.com/whichguy/skill-craft";
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

function shortDescriptionFromFm(fm, description) {
  const declared = metadataScalar(fm, "short-description");
  if (declared) return declared;
  if (description.length <= 120) return description;
  const cut = description.slice(0, 119);
  const boundary = cut.lastIndexOf(" ");
  return (boundary > 60 ? cut.slice(0, boundary) : cut).replace(/[.,;:]+$/, "") + "…";
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
  const plugin = buildPlugin(leaf, fm);
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

function buildCursorMarketplace(leaves) {
  return {
    name: "skill-craft",
    owner: {
      name: "whichguy",
    },
    metadata: {
      description: MARKETPLACE_DESCRIPTION,
    },
    plugins: leaves.map((leaf) => {
      const plugin = buildPlugin(leaf, readSkillFrontmatter(leaf));
      return {
        name: leaf,
        source: `./plugins/${leaf}`,
        description: plugin.description,
      };
    }),
  };
}

function buildGrokMarketplace(leaves) {
  return {
    name: "skill-craft",
    description: MARKETPLACE_DESCRIPTION,
    owner: {
      name: "whichguy",
    },
    plugins: leaves.map((leaf) => {
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
    })
  );
}

function main() {
  const args = process.argv.slice(2);
  if (args.length === 0 || args.includes("-h") || args.includes("--help")) {
    console.log(
      "Usage: skill-frontmatter-to-plugin-json.js <leaf> [--write|--check]\n" +
        "       skill-frontmatter-to-plugin-json.js --marketplaces [--write|--check]"
    );
    process.exit(args.length === 0 ? 1 : 0);
  }
  const doWrite = args.includes("--write");
  const doCheck = args.includes("--check");
  const marketplaces = args.includes("--marketplaces");
  if (doWrite && doCheck) {
    fail("--write and --check are mutually exclusive");
  }
  const leaves = args.filter((a) => !a.startsWith("--"));

  if (marketplaces) {
    if (leaves.length > 0) {
      fail("--marketplaces does not take a leaf");
    }
    runMarketplaces(doWrite, doCheck);
    return;
  }

  if (leaves.length !== 1) {
    fail("missing leaf");
  }
  const leaf = leaves[0];

  const fm = readSkillFrontmatter(leaf);
  const plugin = buildPlugin(leaf, fm);
  const claudePath = path.join(
    root,
    "plugins",
    leaf,
    ".claude-plugin",
    "plugin.json"
  );
  const cursorPath = path.join(
    root,
    "plugins",
    leaf,
    ".cursor-plugin",
    "plugin.json"
  );
  const codexPath = path.join(
    root,
    "plugins",
    leaf,
    ".codex-plugin",
    "plugin.json"
  );
  const cursorPlugin = buildCursorPlugin(leaf, fm);
  const codexPlugin = buildCodexPlugin(leaf, fm);
  const readmePath = packageReadmePath(leaf);
  const packageReadme = buildPackageReadme(leaf, fm);

  if (doCheck) {
    checkClaudePlugin(claudePath, plugin, leaf);
    checkGeneratedJson(
      cursorPath,
      cursorPlugin,
      `${leaf} Cursor plugin manifest`
    );
    checkGeneratedJson(codexPath, codexPlugin, `${leaf} Codex plugin manifest`);
    checkGeneratedText(readmePath, packageReadme, `${leaf} package README`);
    process.stdout.write(`skill-frontmatter-to-plugin-json: CHECK OK ${leaf}\n`);
    return;
  }

  if (doWrite) {
    writeGeneratedJson(claudePath, plugin);
    writeGeneratedJson(cursorPath, cursorPlugin);
    writeGeneratedJson(codexPath, codexPlugin);
    writeGeneratedText(readmePath, packageReadme);
    process.stdout.write(
      `skill-frontmatter-to-plugin-json: wrote plugins/${leaf} host manifests and README.md\n`
    );
    return;
  }

  process.stdout.write(jsonText(plugin));
}

main();
