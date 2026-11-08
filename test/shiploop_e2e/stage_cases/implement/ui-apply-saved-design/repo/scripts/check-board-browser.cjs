"use strict";

const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const required = ["--light-page", "--dark-page", "--square-a", "--square-b", "--board-max", "--focus-color"];
if (process.argv.includes("--help")) {
  process.stdout.write(`Checks the local board at 390x844 and 1440x1000, in light and dark themes.\nPass selected AD anchors as values; no palette is baked into this runner.\nUsage: node scripts/check-board-browser.cjs ${required.map((name) => `${name} VALUE`).join(" ")} [--dark-focus-color VALUE] [--dark-class CLASS] [--summary-below --summary-max VALUE --summary-gap VALUE]\n`);
  process.exit(0);
}
const args = Object.fromEntries(process.argv.slice(2).reduce((pairs, value, index, values) => {
  if (value.startsWith("--") && values[index + 1] && !values[index + 1].startsWith("--")) {
    pairs.push([value, values[index + 1]]);
  }
  return pairs;
}, []));
const missing = required.filter((name) => !args[name]);
if (missing.length) {
  process.stderr.write(`Usage: node scripts/check-board-browser.cjs ${required.map((name) => `${name} VALUE`).join(" ")} [--summary-below]\nMissing: ${missing.join(", ")}\n`);
  process.exit(2);
}
if (process.argv.includes("--summary-below") && (!args["--summary-max"] || !args["--summary-gap"])) {
  process.stderr.write("--summary-below requires --summary-max and --summary-gap values from the selected AD.\n");
  process.exit(2);
}
if (!process.env.PLAYWRIGHT_NODE_PATH || !process.env.BROWSER_EXECUTABLE_PATH) {
  throw new Error("This check needs the host-provided PLAYWRIGHT_NODE_PATH and BROWSER_EXECUTABLE_PATH; do not install a browser.");
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
    if (!file.startsWith(root + path.sep) && file !== path.join(root, "index.html")) {
      response.writeHead(403).end();
      return;
    }
    fs.readFile(file, (error, contents) => {
      if (error) {
        response.writeHead(404).end();
        return;
      }
      response.writeHead(200, { "content-type": mime(file) }).end(contents);
    });
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve(server)));
}

function channels(value) {
  const match = String(value).match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
  return match ? match.slice(1, 4).map(Number) : null;
}

async function expectedChannels(page, value) {
  return page.evaluate((color) => {
    const sample = document.createElement("span");
    sample.style.color = color;
    document.body.append(sample);
    const parsed = getComputedStyle(sample).color;
    sample.remove();
    return parsed;
  }, value).then(channels);
}

async function actualBackgroundMatches(page, expected) {
  const expectedRgb = await expectedChannels(page, expected);
  if (!expectedRgb) return false;
  const actual = await page.evaluate(() => ["html", "body", "main"].map((selector) => {
    const element = document.querySelector(selector);
    return element ? getComputedStyle(element).backgroundColor : "";
  }));
  return actual.some((color) => JSON.stringify(channels(color)) === JSON.stringify(expectedRgb));
}

function dimensionPixels(value, rootPixels) {
  const match = String(value).match(/^\s*(\d+(?:\.\d+)?)(rem|px)\s*$/);
  if (!match) throw new Error(`--board-max must be a concrete px or rem value, received ${value}`);
  return Number(match[1]) * (match[2] === "rem" ? rootPixels : 1);
}

async function checkLayout(page, theme, expectedPage, expectedSquares) {
  if (!(await actualBackgroundMatches(page, expectedPage))) {
    throw new Error(`${theme}: no rendered page surface matches the selected ${theme} canvas ${expectedPage}`);
  }

  const squares = page.getByRole("button", { name: /^Square [a-h][1-8]$/ });
  if (await squares.count() !== 64) throw new Error(`${theme}: expected 64 named square buttons`);
  const first = page.getByRole("button", { name: "Square a1" });
  const next = page.getByRole("button", { name: "Square b1" });
  const observed = await Promise.all([first, next].map((button) => button.evaluate((element) => getComputedStyle(element).backgroundColor)));
  const expected = await Promise.all(expectedSquares.map((value) => expectedChannels(page, value)));
  if (expected.some((color) => !color) || !expected.some((color) => JSON.stringify(color) === JSON.stringify(channels(observed[0]))) || !expected.some((color) => JSON.stringify(color) === JSON.stringify(channels(observed[1])))) {
    throw new Error(`${theme}: the first two alternating board surfaces do not match the AD color anchors`);
  }

  const board = page.locator("#board");
  const dimensions = await board.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return { width: rect.width, height: rect.height, root: parseFloat(getComputedStyle(document.documentElement).fontSize) };
  });
  const maxWidth = dimensionPixels(args["--board-max"], dimensions.root);
  if (dimensions.width > maxWidth + 1 || Math.abs(dimensions.width - dimensions.height) > 1) {
    throw new Error(`${theme}: board is not square or exceeds the selected ${args["--board-max"]} maximum`);
  }
  if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)) {
    throw new Error(`${theme}: horizontal overflow`);
  }

  const boxes = await squares.evaluateAll((elements) => elements.map((element) => {
    const rect = element.getBoundingClientRect();
    return [rect.width, rect.height];
  }));
  if (boxes.some(([width, height]) => Math.abs(width - boxes[0][0]) > 1 || Math.abs(height - boxes[0][1]) > 1 || Math.abs(width - height) > 1)) {
    throw new Error(`${theme}: board cells are not equal squares`);
  }

  await first.focus();
  const focus = await first.evaluate((element) => {
    const style = getComputedStyle(element);
    return { outline: style.outlineStyle !== "none" && parseFloat(style.outlineWidth) >= 2, shadow: style.boxShadow !== "none", outlineColor: style.outlineColor, boxShadow: style.boxShadow };
  });
  const focusAnchor = theme === "dark" ? (args["--dark-focus-color"] || args["--focus-color"]) : args["--focus-color"];
  const focusRgb = await expectedChannels(page, focusAnchor);
  const focusObserved = [channels(focus.outlineColor), ...String(focus.boxShadow).match(/rgba?\([^)]*\)/g)?.map(channels) || []];
  if (!(focus.outline || focus.shadow) || !focusObserved.some((color) => JSON.stringify(color) === JSON.stringify(focusRgb))) {
    throw new Error(`${theme}: visible focus treatment does not use the selected focus color ${focusAnchor}`);
  }

}

async function checkBoardBehavior(page) {
  await page.getByRole("button", { name: "Square a1" }).click();
  if ((await page.getByRole("status").innerText()).trim() !== "Selected: a1") {
    throw new Error("selecting a square does not announce its coordinate");
  }
  await page.getByRole("button", { name: "Reset" }).click();
  if ((await page.getByRole("status").innerText()).trim() !== "Choose a square") {
    throw new Error("Reset does not restore Choose a square");
  }
}

async function checkSummary(page) {
  await page.getByRole("button", { name: "Square a1" }).click();
  if ((await page.getByRole("status").innerText()).trim() !== "Selected: a1") {
    throw new Error("selected-square summary does not announce the coordinate");
  }
  const geometry = await page.evaluate(() => {
    const boardRect = document.querySelector("#board").getBoundingClientRect();
    const statusRect = document.querySelector("#selection-status").getBoundingClientRect();
    const rootPixels = parseFloat(getComputedStyle(document.documentElement).fontSize);
    return { below: boardRect.bottom <= statusRect.top, width: statusRect.width,
      gap: statusRect.top - boardRect.bottom, rootPixels };
  });
  if (!geometry.below) throw new Error("selected-square summary is not below the board");
  const summaryMax = dimensionPixels(args["--summary-max"], geometry.rootPixels);
  const summaryGap = dimensionPixels(args["--summary-gap"], geometry.rootPixels);
  if (geometry.width > summaryMax + 1) throw new Error("summary exceeds its selected maximum " + args["--summary-max"]);
  if (Math.abs(geometry.gap - summaryGap) > 2) throw new Error("summary gap does not match " + args["--summary-gap"]);
  await page.getByRole("button", { name: "Reset" }).click();
  if ((await page.getByRole("status").innerText()).trim() !== "Choose a square") {
    throw new Error("Reset does not restore the summary prompt");
  }
}

async function main() {
  const server = await startServer();
  let browser;
  try {
    browser = await chromium.launch({ headless: true, executablePath: process.env.BROWSER_EXECUTABLE_PATH });
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, colorScheme: "light" });
    const page = await context.newPage();
    const address = server.address();
    await page.goto(`http://127.0.0.1:${address.port}/`);
    const failures = [];
    async function report(id, check) {
      try {
        await check();
        process.stdout.write(id + ": PASS\n");
      } catch (error) {
        process.stderr.write(id + ": FAIL — " + error.message + "\n");
        failures.push(id);
      }
    }
    for (const viewport of [{ width: 390, height: 844 }, { width: 1440, height: 1000 }]) {
      await page.setViewportSize(viewport);
      for (const theme of ["light", "dark"]) {
        await page.emulateMedia({ colorScheme: theme });
        await page.reload();
        if (theme === "dark" && args["--dark-class"]) {
          await page.evaluate((className) => document.documentElement.classList.add(className), args["--dark-class"]);
        }
        const expectedPage = args[theme === "light" ? "--light-page" : "--dark-page"];
        await report("TC-LAYOUT " + viewport.width + "x" + viewport.height + " " + theme,
          () => checkLayout(page, theme, expectedPage, [args["--square-a"], args["--square-b"]]));
        await report("TC-BOARD " + viewport.width + "x" + viewport.height + " " + theme,
          () => checkBoardBehavior(page));
        if (process.argv.includes("--summary-below")) {
          await report("TC-SUMMARY " + viewport.width + "x" + viewport.height + " " + theme,
            () => checkSummary(page));
        }
      }
    }
    if (failures.length) throw new Error(failures.length + " rendered check(s) failed: " + failures.join(", "));
    await context.close();
  } finally {
    if (browser) await browser.close();
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
