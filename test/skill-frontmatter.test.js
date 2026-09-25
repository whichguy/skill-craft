#!/usr/bin/env node
"use strict";

/**
 * Frontmatter contract for every skills/<leaf>/SKILL.md (P1).
 * skill-interop keeps stricter frontmatter extras.
 */
const fs = require("fs");
const path = require("path");

const skillsDir = path.join(__dirname, "..", "skills");
const KINDS = new Set(["prompt-only", "script-backed", "mixed"]);
const SEMVER_RE = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;

function fail(msg) {
  console.error(`skill-frontmatter.test.js: FAIL ${msg}`);
  process.exit(1);
}

function parseFrontmatter(text, leaf) {
  if (!text.startsWith("---\n")) {
    fail(`${leaf}: SKILL.md must start with --- frontmatter`);
  }
  const close = text.indexOf("\n---\n", 3);
  if (close < 0) {
    fail(`${leaf}: frontmatter close --- not found`);
  }
  const fm = text.slice(4, close);
  const body = text.slice(close + 5);
  if (!body.trim()) {
    fail(`${leaf}: skill body after frontmatter is empty`);
  }
  if (text.length > 100000) {
    fail(`${leaf}: skill content ${text.length} exceeds 100000 chars`);
  }
  return { fm, body };
}

function requireLine(fm, leaf, re, label) {
  if (!re.test(fm)) {
    fail(`${leaf}: frontmatter missing ${label}`);
  }
}

function descriptionNonEmpty(fm, leaf) {
  // description: plain | block | folded
  if (/^description:\s*\S+/m.test(fm)) {
    return;
  }
  const block = fm.match(/^description:\s*[|>]-?\s*\n((?:[ \t]+.*\n?)*)/m);
  if (!block) {
    fail(`${leaf}: description block not parseable`);
  }
  const desc = block[1]
    .split("\n")
    .map((l) => l.replace(/^[ \t]+/, "").trimEnd())
    .filter((l) => l.length > 0)
    .join(" ");
  if (desc.length === 0) {
    fail(`${leaf}: description empty`);
  }
}

const leaves = fs
  .readdirSync(skillsDir)
  .filter((name) => {
    const p = path.join(skillsDir, name);
    return fs.statSync(p).isDirectory() && fs.existsSync(path.join(p, "SKILL.md"));
  })
  .sort();

if (leaves.length === 0) {
  fail("no skills/*/SKILL.md found");
}

for (const leaf of leaves) {
  const skillPath = path.join(skillsDir, leaf, "SKILL.md");
  const text = fs.readFileSync(skillPath, "utf8");
  const { fm } = parseFrontmatter(text, leaf);

  requireLine(fm, leaf, new RegExp(`^name:\\s*${leaf}\\s*$`, "m"), `name: ${leaf}`);
  requireLine(fm, leaf, /^description:\s/m, "description");
  descriptionNonEmpty(fm, leaf);
  const versionMatch = fm.match(/^version:\s*(\S+)\s*$/m);
  if (!versionMatch || !SEMVER_RE.test(versionMatch[1])) {
    fail(`${leaf}: version must be strict semver`);
  }
  requireLine(fm, leaf, /^license:\s*\S+/m, "license");
  requireLine(fm, leaf, /^platforms:\s*$/m, "platforms");
  requireLine(fm, leaf, /^\s+-\s+(linux|macos)\s*$/m, "platforms entry linux|macos");
  requireLine(fm, leaf, /^metadata:\s*$/m, "metadata");
  requireLine(fm, leaf, /^\s+skill_craft:\s*$/m, "metadata.skill_craft");
  requireLine(fm, leaf, /^\s+kind:\s*(prompt-only|script-backed|mixed)\s*$/m, "metadata.skill_craft.kind");

  const kindMatch = fm.match(/^\s+kind:\s*(\S+)\s*$/m);
  if (!kindMatch || !KINDS.has(kindMatch[1])) {
    fail(`${leaf}: kind must be one of ${[...KINDS].join("|")}`);
  }
}

// skill-interop frontmatter extras
{
  const leaf = "skill-interop";
  if (!leaves.includes(leaf)) {
    fail("skill-interop missing");
  }
  const text = fs.readFileSync(path.join(skillsDir, leaf, "SKILL.md"), "utf8");
  const { fm } = parseFrontmatter(text, leaf);
  requireLine(fm, leaf, /^author:\s*\S+/m, "author");
  requireLine(fm, leaf, /^\s+kind:\s*script-backed\s*$/m, "kind script-backed");

  const descMatch = fm.match(/^description:\s*>-?\s*\n((?:[ \t]+.*\n)*)/m);
  if (!descMatch) {
    fail(`${leaf}: description block not parseable for Use-when check`);
  }
  const desc = descMatch[1]
    .split("\n")
    .map((l) => l.replace(/^[ \t]+/, "").trimEnd())
    .filter((l) => l.length > 0)
    .join(" ");
  if (desc.length === 0) {
    fail(`${leaf}: description empty`);
  }
  if (desc.length > 1024) {
    fail(`${leaf}: description length ${desc.length} > 1024`);
  }
  if (!/^Use when\b/i.test(desc)) {
    fail(`${leaf}: description should start with 'Use when'`);
  }
}

console.log(
  `skill-frontmatter.test.js: PASS ${leaves.length} skills (name/version/license/platforms/kind; skill-interop extras)`
);
