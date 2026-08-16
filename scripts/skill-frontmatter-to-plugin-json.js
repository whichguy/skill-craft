#!/usr/bin/env node
"use strict";

/**
 * Derive Claude plugin.json fields from skills/<leaf>/SKILL.md frontmatter.
 *
 * Usage:
 *   node scripts/skill-frontmatter-to-plugin-json.js <leaf>
 *   node scripts/skill-frontmatter-to-plugin-json.js <leaf> --write
 *   node scripts/skill-frontmatter-to-plugin-json.js <leaf> --check
 *
 * Exit 0 on success / check match; exit 1 on error or --check mismatch.
 */
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const MAX_DESC = 1024;

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

// User-facing dest name may differ from the source leaf. Plugin id stays the leaf.
const DEST_NAME_ALIASES = { "devloop-run": "devloop" };

function buildPlugin(leaf, fm) {
  const name = scalar(fm, "name") || leaf;
  const allowed = name === leaf || DEST_NAME_ALIASES[leaf] === name;
  if (!allowed) {
    fail(`frontmatter name ${name} != leaf ${leaf}`);
  }
  const version = scalar(fm, "version");
  if (!version) {
    fail("missing version");
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
    homepage: "https://github.com/whichguy/skill-craft",
    repository: "https://github.com/whichguy/skill-craft",
    license,
    keywords: kw,
  };
}

function main() {
  const args = process.argv.slice(2);
  if (args.length === 0 || args.includes("-h") || args.includes("--help")) {
    console.log(
      "Usage: skill-frontmatter-to-plugin-json.js <leaf> [--write|--check]"
    );
    process.exit(args.length === 0 ? 1 : 0);
  }
  const leaf = args.find((a) => !a.startsWith("--"));
  if (!leaf) {
    fail("missing leaf");
  }
  const doWrite = args.includes("--write");
  const doCheck = args.includes("--check");

  const skillPath = path.join(root, "skills", leaf, "SKILL.md");
  if (!fs.existsSync(skillPath)) {
    fail(`missing ${skillPath}`);
  }
  const fm = parseFrontmatter(fs.readFileSync(skillPath, "utf8"));
  const plugin = buildPlugin(leaf, fm);
  const json = JSON.stringify(plugin, null, 2) + "\n";
  const outPath = path.join(
    root,
    "plugins",
    leaf,
    ".claude-plugin",
    "plugin.json"
  );

  if (doCheck) {
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
    // Compare load-bearing fields derived from SoT
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
    process.stdout.write(`skill-frontmatter-to-plugin-json: CHECK OK ${leaf}\n`);
    return;
  }

  if (doWrite) {
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, json);
    process.stdout.write(
      `skill-frontmatter-to-plugin-json: wrote plugins/${leaf}/.claude-plugin/plugin.json\n`
    );
    return;
  }

  process.stdout.write(json);
}

main();
