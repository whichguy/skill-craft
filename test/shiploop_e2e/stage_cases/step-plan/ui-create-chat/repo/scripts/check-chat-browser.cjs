"use strict";

const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const required = ["--light-page", "--dark-page", "--panel", "--dark-panel", "--accent", "--focus-color", "--content-max"];
if (process.argv.includes("--help")) {
  process.stdout.write(`Checks the local chat at 390x844 and 1440x1000 in light and dark themes.
Pass anchors from the selected AD; no palette is baked into this runner.
Usage: node scripts/check-chat-browser.cjs ${required.map((key) => `${key} VALUE`).join(" ")} [--dark-class CLASS]
`);
  process.exit(0);
}
const args = Object.fromEntries(process.argv.slice(2).reduce((pairs, value, index, values) => {
  if (value.startsWith("--") && values[index + 1] && !values[index + 1].startsWith("--")) pairs.push([value, values[index + 1]]);
  return pairs;
}, []));
const missing = required.filter((key) => !args[key]);
if (missing.length) throw new Error(`Missing selected AD anchors: ${missing.join(", ")}`);
if (!process.env.PLAYWRIGHT_NODE_PATH || !process.env.BROWSER_EXECUTABLE_PATH) {
  throw new Error("This check needs host-provided PLAYWRIGHT_NODE_PATH and BROWSER_EXECUTABLE_PATH; do not install a browser.");
}
const { chromium } = require(process.env.PLAYWRIGHT_NODE_PATH);

function mime(file) {
  return file.endsWith(".html") ? "text/html" : file.endsWith(".css") ? "text/css" : "text/javascript";
}
function startServer() {
  const server = http.createServer((request, response) => {
    const urlPath = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
    const relative = urlPath === "/" ? "index.html" : urlPath.replace(/^\/+/, "");
    const file = path.resolve(root, relative);
    if (!file.startsWith(root + path.sep) && file !== path.join(root, "index.html")) return response.writeHead(403).end();
    fs.readFile(file, (error, bytes) => {
      if (error) return response.writeHead(404).end();
      response.writeHead(200, { "content-type": mime(file) }).end(bytes);
    });
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve(server)));
}
function channels(value) {
  const match = String(value).match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
  return match ? match.slice(1, 4).map(Number) : null;
}
async function color(page, value) {
  return page.evaluate((input) => {
    const sample = document.createElement("span");
    sample.style.color = input;
    document.body.append(sample);
    const parsed = getComputedStyle(sample).color;
    sample.remove();
    return parsed;
  }, value).then(channels);
}
async function matches(page, selector, expected) {
  const rgb = await color(page, expected);
  const actual = await page.locator(selector).evaluateAll((elements) => elements.map((element) => getComputedStyle(element).backgroundColor));
  return Boolean(rgb) && actual.some((value) => JSON.stringify(channels(value)) === JSON.stringify(rgb));
}
function maxPixels(value, rootPixels) {
  const match = String(value).match(/^\s*(\d+(?:\.\d+)?)(rem|px)\s*$/);
  if (!match) throw new Error(`--content-max must be a concrete rem or px value: ${value}`);
  return Number(match[1]) * (match[2] === "rem" ? rootPixels : 1);
}

async function main() {
  const server = await startServer();
  let browser;
  try {
    browser = await chromium.launch({ headless: true, executablePath: process.env.BROWSER_EXECUTABLE_PATH });
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, colorScheme: "light" });
    const page = await context.newPage();
    const address = server.address();
    const failures = [];
    for (const viewport of [{ width: 390, height: 844 }, { width: 1440, height: 1000 }]) {
      await page.setViewportSize(viewport);
      for (const theme of ["light", "dark"]) {
        await page.emulateMedia({ colorScheme: theme });
        await page.reload();
        if (theme === "dark" && args["--dark-class"]) {
          await page.evaluate((name) => document.documentElement.classList.add(name), args["--dark-class"]);
        }
        const pageAnchor = args[theme === "light" ? "--light-page" : "--dark-page"];
        const label = `TC-CHAT-LAYOUT ${viewport.width}x${viewport.height} ${theme}`;
        try {
          if (!(await matches(page, "html, body, main", pageAnchor))) throw new Error(`page surface does not match ${pageAnchor}`);
          const panelAnchor = theme === "dark" ? args["--dark-panel"] : args["--panel"];
          if (!(await matches(page, "#chat-panel", panelAnchor))) throw new Error("chat panel surface does not match its AD anchor");
          for (const selector of ["#conversation-list", "#active-conversation", "#message-list", "#chat-form", "#message-input", "#send-message"]) {
            if (await page.locator(selector).count() !== 1 || !(await page.locator(selector).isVisible())) throw new Error(`${selector} is missing or not visible`);
          }
          const layout = await page.locator("#chat-layout").evaluate((element) => {
            const rect = element.getBoundingClientRect();
            return { width: rect.width, root: parseFloat(getComputedStyle(document.documentElement).fontSize) };
          });
          if (layout.width > maxPixels(args["--content-max"], layout.root) + 1) throw new Error("chat layout exceeds the AD maximum width");
          if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)) throw new Error("page has horizontal overflow");
          const send = page.locator("#send-message");
          await send.focus();
          const focused = await send.evaluate((element) => {
            const style = getComputedStyle(element);
            return {
              visible: (style.outlineStyle !== "none" && parseFloat(style.outlineWidth) >= 2) || style.boxShadow !== "none",
              colors: [style.outlineColor, ...String(style.boxShadow).match(/rgba?\([^)]*\)/g) || []],
            };
          });
          const focus = await color(page, args["--focus-color"]);
          const focusColors = focused.colors.map(channels);
          if (!focused.visible || !focusColors.some((value) => JSON.stringify(value) === JSON.stringify(focus))) {
            throw new Error("keyboard focus does not use the selected focus anchor");
          }
          const selectedAccent = await color(page, args["--accent"]);
          const active = await page.locator("#conversation-list [aria-current='page']").evaluate((element) => getComputedStyle(element).borderLeftColor);
          if (JSON.stringify(channels(active)) !== JSON.stringify(selectedAccent)) throw new Error("selected conversation marker does not use the AD accent");
          process.stdout.write(label + ": PASS\n");
        } catch (error) {
          process.stderr.write(label + ": FAIL — " + error.message + "\n");
          failures.push(label);
        }
      }
    }
    await context.close();
    if (failures.length) throw new Error(`${failures.length} rendered chat check(s) failed`);
  } finally {
    if (browser) await browser.close();
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
}
main().catch((error) => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
