#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

const skillPath = path.join(__dirname, "..", "skills", "skill-interop", "SKILL.md");
const text = fs.readFileSync(skillPath, "utf8");

function fail(msg) {
  console.error(`skill-interop-frontmatter.test.js: FAIL ${msg}`);
  process.exit(1);
}

if (!text.startsWith("---\n")) {
  fail("SKILL.md must start with --- frontmatter");
}

const close = text.indexOf("\n---\n", 3);
if (close < 0) {
  fail("frontmatter close --- not found");
}

const fm = text.slice(4, close);
const body = text.slice(close + 5);

if (!body.trim()) {
  fail("skill body after frontmatter is empty");
}

if (text.length > 100000) {
  fail(`skill content ${text.length} exceeds 100000 chars`);
}

function requireLine(re, label) {
  if (!re.test(fm)) {
    fail(`frontmatter missing ${label}`);
  }
}

requireLine(/^name:\s*skill-interop\s*$/m, "name: skill-interop");
requireLine(/^description:\s/m, "description");
requireLine(/^version:\s*\S+/m, "version");
requireLine(/^author:\s*\S+/m, "author");
requireLine(/^license:\s*\S+/m, "license");
requireLine(/^platforms:\s*$/m, "platforms");
requireLine(/^metadata:\s*$/m, "metadata");
requireLine(/^\s+hermes:\s*$/m, "metadata.hermes");
requireLine(/^\s+category:\s*software-development\s*$/m, "hermes.category software-development");
requireLine(/^\s+tags:\s*$/m, "hermes.tags");

// Description ≤ 1024 chars (folded block under description: >-)
const descMatch = fm.match(/^description:\s*>-?\s*\n((?:[ \t]+.*\n)*)/m);
if (!descMatch) {
  fail("description block not parseable");
}
const desc = descMatch[1]
  .split("\n")
  .map((l) => l.replace(/^[ \t]+/, "").trimEnd())
  .filter((l) => l.length > 0)
  .join(" ");
if (desc.length === 0) {
  fail("description empty");
}
if (desc.length > 1024) {
  fail(`description length ${desc.length} > 1024`);
}
if (!/^Use when\b/i.test(desc)) {
  fail("description should start with 'Use when' (Hermes peer trigger style)");
}

console.log(
  `skill-interop-frontmatter.test.js: PASS hermes peer frontmatter (desc ${desc.length} chars, total ${text.length})`
);
