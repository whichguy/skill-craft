"use strict";
const fs = require("fs");

const raw = fs.readFileSync(0, "utf8");
const items = JSON.parse(raw);
if (!Array.isArray(items) || items.length > 20) {
  process.stderr.write("ERR_BATCH_CAP_20\n");
  process.exit(2);
}
for (const item of items) {
  const note = String(item.note || "").replace(/\r?\n/g, " ");
  process.stdout.write(`${item.id}\t${item.name || ""}\t${note}\n`);
}
