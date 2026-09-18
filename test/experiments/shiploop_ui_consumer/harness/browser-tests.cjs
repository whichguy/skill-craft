#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { CSP, ServiceDouble, createStaticServer } = require("./service-double.cjs");

const TIMEOUT = Number(process.env.BROWSER_TEST_TIMEOUT_MS || 5000);

function usage() {
  return [
    "Usage: node browser-tests.cjs --product <static-product-dir> [--mode baseline|full] [--case P2[,P7]] [--baseline-report <P1-report.json>] [--output <dir>] [--headed]",
    "",
    "Environment overrides:",
    "  PLAYWRIGHT_NODE_PATH or PLAYWRIGHT_MODULE_PATH  Playwright module directory",
    "  BROWSER_EXECUTABLE_PATH                           Chromium/Chrome executable (optional)",
    "  BROWSER_HEADLESS=false                            run headed unless --headed is absent",
    "  BROWSER_TEST_TIMEOUT_MS                           per-condition timeout (default 5000)",
  ].join("\n");
}

function parseArgs(argv) {
  const options = {
    mode: "full",
    product: null,
    output: null,
    cases: null,
    baselineReport: null,
    headed: process.env.BROWSER_HEADLESS === "false",
  };
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === "--help" || value === "-h") {
      process.stdout.write(`${usage()}\n`);
      process.exit(0);
    }
    if (value === "--mode") options.mode = argv[++index];
    else if (value === "--case") options.cases = String(argv[++index] || "").split(",").filter(Boolean);
    else if (value === "--product") options.product = argv[++index];
    else if (value === "--output") options.output = argv[++index];
    else if (value === "--baseline-report") options.baselineReport = argv[++index];
    else if (value === "--headed") options.headed = true;
    else throw new Error(`Unknown argument: ${value}`);
  }
  if (!options.product) throw new Error("--product is required\n\n" + usage());
  if (!new Set(["baseline", "full"]).has(options.mode)) {
    throw new Error(`--mode must be baseline or full, got ${options.mode}`);
  }
  if (options.cases && options.cases.length === 0) throw new Error("--case requires at least one case id");
  options.product = path.resolve(options.product);
  if (!fs.existsSync(path.join(options.product, "index.html"))) {
    throw new Error(`Static product does not contain index.html: ${options.product}`);
  }
  options.output = path.resolve(options.output || path.join(__dirname, "artifacts", `run-${new Date().toISOString().replace(/[:.]/g, "-")}`));
  if (options.baselineReport) options.baselineReport = path.resolve(options.baselineReport);
  return options;
}

function loadPlaywright() {
  const candidates = [
    process.env.PLAYWRIGHT_NODE_PATH,
    process.env.PLAYWRIGHT_MODULE_PATH,
    "playwright",
  ].filter(Boolean);
  let lastError;
  for (const candidate of candidates) {
    try {
      return { api: require(candidate), modulePath: candidate };
    } catch (error) {
      lastError = error;
    }
  }
  throw new Error(`Could not load Playwright. Set PLAYWRIGHT_NODE_PATH (or PLAYWRIGHT_MODULE_PATH), or make require('playwright') resolvable: ${lastError?.message || "unknown error"}`);
}

function createFreshOutputDirectory(output) {
  fs.mkdirSync(path.dirname(output), { recursive: true });
  try {
    fs.mkdirSync(output);
  } catch (error) {
    if (error.code === "EEXIST") throw new Error(`--output must name a new directory so prior evidence is preserved: ${output}`);
    throw error;
  }
}

function sha256Files(root, include) {
  const digest = crypto.createHash("sha256");
  const files = [];
  function add(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const file = path.join(directory, entry.name);
      const relative = path.relative(root, file);
      if (entry.isDirectory() && include(relative, entry)) add(file);
      else if (entry.isFile() && include(relative, entry)) {
        digest.update(`${relative}\0`);
        digest.update(fs.readFileSync(file));
        digest.update("\0");
        files.push(relative);
      }
    }
  }
  add(root);
  return { sha256: digest.digest("hex"), files };
}

function hashServedProduct(root) {
  const servedExtensions = new Set([".css", ".gif", ".html", ".ico", ".jpeg", ".jpg", ".js", ".json", ".mjs", ".png", ".svg", ".webp", ".woff", ".woff2"]);
  return sha256Files(root, (relative, entry) => {
    if (entry.isDirectory()) return !relative.split(path.sep).some((part) => part === ".git" || part === ".until-loop" || part === "artifacts");
    return servedExtensions.has(path.extname(relative).toLowerCase());
  });
}

function hashHarnessSource() {
  const sourceFiles = new Set(["browser-tests.cjs", "service-double.cjs", "README.md"]);
  return sha256Files(__dirname, (relative, entry) => entry.isFile() && sourceFiles.has(relative));
}

function detailPath(account = "alpha", noteId = "a1") {
  return `/api/accounts/${encodeURIComponent(account)}/notes/${encodeURIComponent(noteId)}`;
}

function operationPath(account, noteId, operationId) {
  return `${detailPath(account, noteId)}/operations/${encodeURIComponent(operationId)}`;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function requestCount(service, method, pathname) {
  return service.findRequests((entry) => entry.method === method && entry.pathname === pathname).length;
}

function normalize(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

async function installSyntheticVisibility(context) {
  await context.addInitScript(() => {
    let controlledState = null;
    let owner = Document.prototype;
    let descriptor = Object.getOwnPropertyDescriptor(owner, "visibilityState");
    while (!descriptor && owner) {
      owner = Object.getPrototypeOf(owner);
      descriptor = owner && Object.getOwnPropertyDescriptor(owner, "visibilityState");
    }
    const nativeGetter = descriptor && typeof descriptor.get === "function" ? descriptor.get : null;
    try {
      Object.defineProperty(document, "visibilityState", {
        configurable: true,
        get() {
          return controlledState || (nativeGetter ? nativeGetter.call(document) : "visible");
        },
      });
      window.__shiploopFixtureSetVisibility = (next) => {
        if (next !== "visible" && next !== "hidden") throw new Error(`Unsupported visibility state: ${next}`);
        controlledState = next;
        document.dispatchEvent(new Event("visibilitychange"));
        return document.visibilityState;
      };
      window.__shiploopFixtureVisibilityShim = "installed";
    } catch (error) {
      window.__shiploopFixtureVisibilityShim = `unavailable: ${error.message}`;
    }
  });
}

async function createScenario(browser, product, { reducedMotion = "no-preference", touch = false, clock = false } = {}) {
  const service = new ServiceDouble();
  const server = await createStaticServer({ productDir: product, service });
  const context = await browser.newContext({
    viewport: touch ? { width: 390, height: 844 } : { width: 1280, height: 900 },
    isMobile: touch,
    hasTouch: touch,
    reducedMotion,
  });
  await installSyntheticVisibility(context);
  if (clock) await context.clock.install({ time: new Date("2026-09-18T00:00:00.000Z") });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  return {
    context,
    page,
    pageErrors,
    server,
    service,
    clock,
    async close() {
      await context.close();
      await server.close();
    },
  };
}

async function gotoList(scenario) {
  const response = await scenario.page.goto(`${scenario.server.baseURL}/`, { waitUntil: "domcontentloaded" });
  assert.equal(response.status(), 200, "static product must load successfully");
  assert.equal(response.headers()["content-security-policy"], CSP, "fixture server must enforce the restrictive same-origin CSP");
  await scenario.page.locator("#account").waitFor({ state: "visible", timeout: TIMEOUT });
  await scenario.page.locator("button[data-note-id='a1']").waitFor({ state: "visible", timeout: TIMEOUT });
}

async function waitForRevision(page, revision, note) {
  await page.waitForFunction(({ revision: expectedRevision, note: expectedNote }) => {
    const revisionNode = document.querySelector("#revision");
    const confirmed = document.querySelector("#confirmed-note");
    return revisionNode?.textContent?.trim() === String(expectedRevision)
      && (!expectedNote || confirmed?.textContent?.includes(expectedNote));
  }, { revision, note }, { timeout: TIMEOUT });
}

async function waitForText(page, selector, text) {
  await page.waitForFunction(({ selector: target, text: expected }) => {
    const node = document.querySelector(target);
    return node && node.textContent.toLowerCase().includes(expected.toLowerCase());
  }, { selector, text }, { timeout: TIMEOUT });
}

async function waitForEnabled(page, selector) {
  await page.waitForFunction((target) => {
    const node = document.querySelector(target);
    return !!node && !node.hidden && !node.disabled;
  }, selector, { timeout: TIMEOUT });
}

async function openDetail(scenario, account = "alpha", noteId = "a1") {
  const { page } = scenario;
  await gotoList(scenario);
  if (await page.locator("#account").inputValue() !== account) {
    await page.locator("#account").selectOption(account);
    await page.locator(`button[data-note-id='${noteId}']`).waitFor({ state: "visible", timeout: TIMEOUT });
  }
  await page.locator(`button[data-note-id='${noteId}']`).click();
  await page.locator("#detail").waitFor({ state: "visible", timeout: TIMEOUT });
  await waitForRevision(page, 10);
}

async function capture(page, caseDirectory, label) {
  const file = path.join(caseDirectory, `${label}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function detailState(page) {
  return page.evaluate(() => {
    const input = document.querySelector("#note-input");
    const scroll = document.querySelector(".detail-scroll");
    return {
      activeId: document.activeElement?.id || null,
      value: input?.value || "",
      selectionStart: input?.selectionStart ?? null,
      selectionEnd: input?.selectionEnd ?? null,
      scrollTop: scroll?.scrollTop ?? null,
    };
  });
}

async function observeStablePresentation(page) {
  return page.evaluate(() => {
    const text = (selector) => (document.querySelector(selector)?.textContent || "").replace(/\s+/g, " ").trim();
    const style = (selector) => getComputedStyle(document.querySelector(selector));
    const root = style(":root");
    return {
      stable: {
        labels: {
          account: text("label[for='account'] > span"),
          back: text("#back"),
          edit: text("#edit"),
          save: text("#save"),
          cancel: text("#cancel"),
        },
        tokens: {
          navy: root.getPropertyValue("--navy").trim().toLowerCase(),
          amber: root.getPropertyValue("--amber").trim().toLowerCase(),
          paper: root.getPropertyValue("--paper").trim().toLowerCase(),
          mist: root.getPropertyValue("--mist").trim().toLowerCase(),
        },
        typography: {
          bodyFontFamily: style("body").fontFamily,
          headingFontFamily: style("h1").fontFamily,
          noteTitleFontFamily: style("#note-title").fontFamily,
          headingColor: style("h1").color,
        },
      },
      initialFocus: document.activeElement?.id || document.activeElement?.tagName || null,
    };
  });
}

function assertAcceptedStablePresentation(observation) {
  assert.deepEqual(observation.stable.labels, {
    account: "Account",
    back: "Back to notes",
    edit: "Edit note",
    save: "Save changes",
    cancel: "Cancel",
  }, "accepted baseline labels remain stable");
  assert.deepEqual(observation.stable.tokens, {
    navy: "#15324f",
    amber: "#c08722",
    paper: "#ffffff",
    mist: "#eef3f7",
  }, "accepted navy/amber/paper/mist tokens remain stable");
  assert.match(observation.stable.typography.headingFontFamily, /Georgia/i, "accepted serif heading type remains stable");
  assert.match(observation.stable.typography.noteTitleFontFamily, /Georgia/i, "accepted serif detail title type remains stable");
  assert.match(observation.stable.typography.bodyFontFamily, /apple-system|BlinkMacSystemFont|Segoe UI/i, "accepted system body type remains stable");
}

function loadBaselineP1(reportPath) {
  if (!reportPath) return null;
  const report = JSON.parse(fs.readFileSync(reportPath, "utf8"));
  const p1 = report.cases?.find((item) => item.id === "P1" && item.status === "passed");
  if (!p1?.evidence?.observations?.presentation?.stable) {
    throw new Error(`--baseline-report does not contain a passed P1 stable presentation observation: ${reportPath}`);
  }
  return {
    path: reportPath,
    productSha256: report.productSha256,
    presentation: p1.evidence.observations.presentation,
  };
}

async function dispatchUpdate(page, account, noteId) {
  await page.evaluate(({ account: updatedAccount, noteId: updatedNoteId }) => {
    window.dispatchEvent(new CustomEvent("fieldnotes:update", { detail: { account: updatedAccount, noteId: updatedNoteId } }));
  }, { account, noteId });
}

async function assertNoPageErrors(scenario) {
  assert.deepEqual(scenario.pageErrors, [], `page emitted errors: ${scenario.pageErrors.join(" | ")}`);
}

async function setSyntheticVisibility(page, state) {
  const result = await page.evaluate((next) => {
    if (typeof window.__shiploopFixtureSetVisibility !== "function") return { installed: false, state: document.visibilityState };
    return { installed: true, state: window.__shiploopFixtureSetVisibility(next) };
  }, state);
  assert.equal(result.installed, true, "test fixture could not install synthetic visibility fallback");
  assert.equal(result.state, state, "synthetic visibility state must be observable by the product");
}

async function attachStatusObserver(page) {
  await page.evaluate(() => {
    const nodes = [...document.querySelectorAll("[role='status']")];
    window.__shiploopFixtureStatusNames = nodes.map((node, index) => node.id || `status-${index}`);
    function normalizeNode(node) { return (node.textContent || "").replace(/\s+/g, " ").trim(); }
    function capture(kind, label) {
      window.__shiploopFixtureStatusEvents.push({
        kind,
        label: label || null,
        at: performance.now(),
        values: nodes.map(normalizeNode),
      });
    }
    window.__shiploopFixtureStatusEvents = [];
    capture("snapshot", "initial");
    const observer = new MutationObserver(() => {
      capture("mutation");
    });
    for (const node of nodes) observer.observe(node, { childList: true, characterData: true, subtree: true });
    window.__shiploopFixtureStatusObserver = observer;
    window.__shiploopFixtureMarkStatus = (label) => capture("mark", label);
  });
}

async function markStatus(page, label) {
  await page.evaluate((mark) => window.__shiploopFixtureMarkStatus?.(mark), label);
}

async function readStatusHistory(page) {
  return page.evaluate(() => {
    window.__shiploopFixtureStatusObserver?.disconnect();
    return {
      names: window.__shiploopFixtureStatusNames || [],
      events: window.__shiploopFixtureStatusEvents || [],
    };
  });
}

async function visibleStatusTexts(page) {
  return (await page.locator("[role='status']").allTextContents()).map(normalize).filter(Boolean);
}

const EXPLICIT_ERROR = /(?:\berror\b|\bfailed\b|could(?:n't| not)|\bunable\b|\bcannot\b|try again|\bretry\b)/i;

async function waitForExplicitFetchError(page) {
  await page.waitForFunction((source) => {
    const pattern = new RegExp(source, "i");
    return [...document.querySelectorAll("[role='status']")].some((node) => pattern.test(node.textContent || ""));
  }, EXPLICIT_ERROR.source, { timeout: TIMEOUT });
  return visibleStatusTexts(page);
}

function statusValuesBetween(history, statusId, startLabel, endLabel) {
  const statusIndex = history.names.indexOf(statusId);
  assert.ok(statusIndex >= 0, `${statusId} remains part of the live status contract`);
  const start = history.events.findIndex((event) => event.kind === "mark" && event.label === startLabel);
  const end = history.events.findIndex((event) => event.kind === "mark" && event.label === endLabel);
  assert.ok(start >= 0 && end > start, `status history contains ${startLabel} through ${endLabel}`);
  return history.events.slice(start + 1, end)
    .filter((event) => event.kind === "mutation")
    .map((event) => event.values[statusIndex] || "")
    .filter(Boolean);
}

async function testP1({ browser, product, caseDirectory, baselineP1 }) {
  const scenario = await createScenario(browser, product);
  const screenshots = [];
  try {
    const { page, service } = scenario;
    await gotoList(scenario);
    const presentation = await observeStablePresentation(page);
    assertAcceptedStablePresentation(presentation);
    if (baselineP1) {
      assert.deepEqual(presentation.stable, baselineP1.presentation.stable, "feature run preserves accepted baseline labels, visual tokens, and typography");
    }
    screenshots.push(await capture(page, caseDirectory, "before"));
    assert.equal(await page.locator("#detail").isHidden(), true, "list opens before detail");

    await page.locator("button[data-note-id='a1']").click();
    await page.locator("#detail").waitFor({ state: "visible", timeout: TIMEOUT });
    await waitForRevision(page, 10);
    assert.match(normalize(await page.locator("#note-title").textContent()), /alpha/i, "selected title remains visible");
    assert.equal(normalize(await page.locator("#revision").textContent()), "10", "initial revision is shown");

    await page.locator("#edit").click();
    await page.locator("#note-input").fill("P1 saved field observation");
    await page.locator("#save").click();
    const savedRequest = await service.waitForRequest((entry) => entry.method === "POST" && entry.pathname === detailPath());
    assert.equal(savedRequest.body.note, "P1 saved field observation", "save sends the edited text");
    assert.equal(savedRequest.body.baseRevision, 10, "save sends the displayed base revision");
    assert.equal(typeof savedRequest.body.operationId, "string", "save carries an operation identity");
    assert.ok(savedRequest.body.operationId.length > 0, "operation identity is nonempty");
    await waitForText(page, "#save-status", "saved");
    await waitForRevision(page, 11, "P1 saved field observation");

    await page.locator("#edit").click();
    await page.locator("#note-input").fill("P1 cancelled draft");
    await page.locator("#cancel").click();
    assert.equal(await page.locator("#note-input").inputValue(), "P1 saved field observation", "cancel restores confirmed text");
    assert.equal(await page.locator("#edit").evaluate((node) => document.activeElement === node), true, "cancel restores intentional edit focus");

    await page.locator("#back").click();
    await page.locator("#notes-view").waitFor({ state: "visible", timeout: TIMEOUT });
    const backFocus = await page.evaluate(() => document.activeElement?.dataset?.noteId || document.activeElement?.id || document.activeElement?.tagName || null);
    assert.equal(backFocus, "a1", "Back restores focus to the first note");
    const second = page.locator("button[data-note-id='a2']");
    await second.focus();
    await page.keyboard.press("Enter");
    await page.locator("#detail").waitFor({ state: "visible", timeout: TIMEOUT });
    await waitForRevision(page, 10);
    assert.match(normalize(await page.locator("#note-title").textContent()), /ridge/i, "keyboard opens the focused list item");
    await page.locator("#back").click();

    let touchObservation = null;
    const touch = await createScenario(browser, product, { touch: true });
    try {
      await gotoList(touch);
      const noteButton = touch.page.locator("button[data-note-id='a1']");
      const box = await noteButton.boundingBox();
      assert.ok(box && box.height >= 44, "touch-emulated list control has a 44px target");
      await noteButton.click();
      await touch.page.locator("#detail").waitFor({ state: "visible", timeout: TIMEOUT });
      const backBox = await touch.page.locator("#back").boundingBox();
      assert.ok(backBox && backBox.height >= 44, "touch-emulated Back control has a 44px target");
      await touch.page.locator("#back").click();
      await touch.page.locator("#notes-view").waitFor({ state: "visible", timeout: TIMEOUT });
      touchObservation = { listTargetHeight: box.height, backTargetHeight: backBox.height, emulatedTouch: true };
      await assertNoPageErrors(touch);
    } finally {
      await touch.close();
    }
    screenshots.push(await capture(page, caseDirectory, "after"));
    await assertNoPageErrors(scenario);
    return {
      screenshots,
      observations: {
        presentation,
        cancelFocus: "edit",
        backFocus,
        touch: touchObservation,
      },
      baselineComparison: baselineP1 ? { report: baselineP1.path, productSha256: baselineP1.productSha256, matched: true } : null,
      saveRequest: savedRequest.body,
      requests: clone(service.requests),
    };
  } finally {
    await scenario.close();
  }
}

async function testP2({ browser, product, caseDirectory }) {
  const scenario = await createScenario(browser, product);
  const screenshots = [];
  try {
    const { page, service } = scenario;
    await openDetail(scenario);
    await page.locator("#edit").click();
    await page.locator("#note-input").fill("P2 dirty local text remains intact");
    await page.locator("#note-input").evaluate((node) => node.setSelectionRange(4, 14));
    const scrollBefore = await page.locator(".detail-scroll").evaluate((node) => {
      node.scrollTop = Math.min(120, Math.max(1, node.scrollHeight - node.clientHeight));
      return node.scrollTop;
    });
    assert.ok(scrollBefore > 0, "the declared reading container must have a nonzero position");
    const before = await detailState(page);
    screenshots.push(await capture(page, caseDirectory, "before"));

    const beforeGets = requestCount(service, "GET", detailPath());
    service.setRecord("alpha", "a1", { exportStatus: "processing", exportRevision: 2 });
    await dispatchUpdate(page, "alpha", "a1");
    await service.waitForRequest((entry) => entry.method === "GET" && entry.pathname === detailPath() && requestCount(service, "GET", detailPath()) > beforeGets);
    await waitForText(page, "#export-status", "processing");
    const after = await detailState(page);
    assert.deepEqual(after, before, "incoming export status must not disturb editor value, selection, focus, or reading position");
    screenshots.push(await capture(page, caseDirectory, "after"));
    await assertNoPageErrors(scenario);
    return { screenshots, before, after, requests: clone(service.requests) };
  } finally {
    await scenario.close();
  }
}

async function testP3({ browser, product, caseDirectory }) {
  const scenario = await createScenario(browser, product);
  const screenshots = [];
  try {
    const { page, service } = scenario;
    await openDetail(scenario);
    await page.locator("#edit").click();
    await page.locator("#note-input").fill("P3 current local draft");
    const oldRecord = clone(service.getRecord("alpha", "a1"));
    const beforeGets = requestCount(service, "GET", detailPath());
    const lateRevisionTen = service.deferNextResponse({ method: "GET", pathname: detailPath(), body: oldRecord, tag: "late-revision-10" });
    await page.locator("#refresh").click();
    const heldRequest = await lateRevisionTen.waitForRequest();

    const revisionEleven = service.setRecord("alpha", "a1", {
      note: "Confirmed revision eleven from the service",
      revision: 11,
      exportRevision: 2,
      exportStatus: "processing",
    });
    service.queueResponse({ method: "GET", pathname: detailPath(), body: revisionEleven, tag: "current-revision-11" });
    await page.locator("#refresh").click();
    await service.waitForRequest((entry) => entry.method === "GET" && entry.pathname === detailPath() && requestCount(service, "GET", detailPath()) >= beforeGets + 2);
    await waitForRevision(page, 11, "Confirmed revision eleven from the service");
    screenshots.push(await capture(page, caseDirectory, "before-late-response"));
    const confirmedBeforeRelease = normalize(await page.locator("#revision").textContent());
    lateRevisionTen.release();
    const releasedResponse = await lateRevisionTen.waitForResponse();
    await page.waitForTimeout(80);
    assert.equal(normalize(await page.locator("#revision").textContent()), "11", "late revision 10 response cannot regress confirmed view");
    assert.match(await page.locator("#confirmed-note").textContent(), /revision eleven/i, "latest authoritative record remains displayed");
    assert.equal(await page.locator("#note-input").inputValue(), "P3 current local draft", "late response cannot overwrite current draft");
    screenshots.push(await capture(page, caseDirectory, "after-late-response"));
    await assertNoPageErrors(scenario);
    return {
      screenshots,
      barrier: { heldRequest, releaseAfterConfirmedRevision: confirmedBeforeRelease, releasedResponse },
      requests: clone(service.requests),
    };
  } finally {
    await scenario.close();
  }
}

async function testP4({ browser, product, caseDirectory }) {
  const scenario = await createScenario(browser, product);
  const screenshots = [];
  try {
    const { page, service } = scenario;
    await openDetail(scenario);
    await page.locator("#edit").click();
    await page.locator("#note-input").fill("P4 local reapply text");
    service.setRecord("alpha", "a1", { note: "Remote version eleven", revision: 11 });
    await page.locator("#save").click();
    const first = await service.waitForRequest((entry) => entry.method === "POST" && entry.pathname === detailPath());
    assert.equal(first.body.baseRevision, 10, "initial conflict attempt uses revision 10");
    await page.locator("#reapply").waitFor({ state: "visible", timeout: TIMEOUT });
    assert.equal(await page.locator("#note-input").inputValue(), "P4 local reapply text", "conflict preserves chosen local text");
    screenshots.push(await capture(page, caseDirectory, "before-reapply"));
    await page.locator("#reapply").click();
    await service.waitForRequest((entry) => entry.method === "POST" && entry.pathname === detailPath() && requestCount(service, "POST", detailPath()) >= 2);
    const saves = service.findRequests((entry) => entry.method === "POST" && entry.pathname === detailPath());
    const second = saves.at(-1);
    assert.equal(second.body.baseRevision, 11, "reapply rebases on returned revision 11");
    assert.notEqual(second.body.operationId, first.body.operationId, "reapply creates a new operation identity");
    assert.equal(second.body.note, "P4 local reapply text", "reapply sends the retained local text");
    await waitForRevision(page, 12, "P4 local reapply text");
    screenshots.push(await capture(page, caseDirectory, "after-reapply"));
    await assertNoPageErrors(scenario);
    return { screenshots, first: first.body, second: second.body, requests: clone(service.requests) };
  } finally {
    await scenario.close();
  }
}

function p5SaveRequests(service) {
  return service.findRequests((entry) => entry.method === "POST" && entry.pathname === detailPath());
}

function requestsAfter(service, anchor) {
  const index = service.requests.indexOf(anchor);
  assert.notEqual(index, -1, "the request anchor must be recorded by the controlled service");
  return service.requests.slice(index + 1);
}

function assertP5TransportLoss(service, save) {
  const attempts = p5SaveRequests(service);
  assert.ok(attempts.length >= 1, "the original save reaches the controlled service");
  assert.equal(attempts.filter((entry) => entry.committed).length, 1, "transport repeats cannot create another atomic effect");
  for (const [index, attempt] of attempts.entries()) {
    assert.equal(attempt.body.operationId, save.body.operationId, "all pre-lookup transport attempts retain the scoped operation identity");
    assert.equal(attempt.body.note, save.body.note, "all pre-lookup transport attempts retain the note intent");
    assert.equal(attempt.body.baseRevision, save.body.baseRevision, "all pre-lookup transport attempts retain the base revision");
    assert.equal(attempt.confirmationLost, true, "every pre-lookup save confirmation is deliberately lost");
    if (index > 0) assert.equal(attempt.deduped, true, "a transport repeat is deduplicated rather than a second effect");
  }
  const loss = service.getLostSaveConfirmation("alpha", "a1", save.body.operationId);
  assert.ok(loss?.active, "the same-operation response loss remains active until explicit recovery lookup");
  assert.equal(loss.transportAttempts, attempts.length, "loss accounting records each pre-lookup transport attempt");
  return { attempts: clone(attempts), loss };
}

async function prepareLostSaveScenario({ browser, product, caseDirectory, draft }) {
  fs.mkdirSync(caseDirectory, { recursive: true });
  const scenario = await createScenario(browser, product);
  try {
    const { page, service } = scenario;
    await openDetail(scenario);
    await page.locator("#edit").click();
    await page.locator("#note-input").fill(draft);
    service.dropNextSaveResponse();
    await page.locator("#save").click();
    const save = await service.waitForRequest((entry) => entry.method === "POST" && entry.pathname === detailPath());
    const operationId = save.body.operationId;
    assert.equal(service.commitCount, 1, "service commits before its confirmation is lost");
    await page.locator("#retry-save").waitFor({ state: "visible", timeout: TIMEOUT });
    await waitForEnabled(page, "#retry-save");
    const transport = assertP5TransportLoss(service, save);
    assert.equal(normalize(await page.locator("#revision").textContent()), "10", "lost response does not become a false confirmed success");
    assert.doesNotMatch(await page.locator("#confirmed-note").textContent(), new RegExp(draft), "lost response does not replace confirmed text before resolution");
    assert.equal(await page.locator("#note-input").inputValue(), draft, "lost response preserves draft");
    const screenshots = [await capture(page, caseDirectory, "after-response-loss")];
    return { scenario, save, operationId, screenshots, transport };
  } catch (error) {
    await scenario.close();
    throw error;
  }
}

async function testP5CommittedLookup({ browser, product, caseDirectory }) {
  const prepared = await prepareLostSaveScenario({ browser, product, caseDirectory, draft: "P5 committed lookup effect" });
  const { scenario, save, operationId, screenshots, transport } = prepared;
  try {
    const { page, service } = scenario;
    await page.locator("#retry-save").click();
    const lookup = await service.waitForRequest((entry) => entry.method === "GET" && entry.pathname === operationPath("alpha", "a1", operationId));
    await waitForRevision(page, 11, save.body.note);
    const operationGets = service.findRequests((entry) => entry.method === "GET" && entry.pathname === operationPath("alpha", "a1", operationId));
    const saves = p5SaveRequests(service);
    const applicationReplayPosts = requestsAfter(service, lookup).filter((entry) => entry.method === "POST" && entry.pathname === detailPath());
    const loss = service.getLostSaveConfirmation("alpha", "a1", operationId);
    assert.equal(operationGets.length, 1, "committed lookup uses the original operation identity once");
    assert.equal(lookup.releasedLostSaveConfirmation, true, "the explicit lookup ends same-operation transport response loss");
    assert.ok(loss, "the committed save has a scoped response-loss record");
    assert.equal(loss.active, false, "committed lookup releases the response-loss guard");
    assert.equal(applicationReplayPosts.length, 0, "committed lookup resolves without an application replay POST");
    assert.equal(saves.length, transport.attempts.length, "only pre-lookup transport attempts occurred for committed recovery");
    assert.equal(service.commitCount, 1, "committed lookup preserves the single atomic effect");
    screenshots.push(await capture(page, caseDirectory, "after-committed-lookup"));
    await assertNoPageErrors(scenario);
    return {
      screenshots,
      operationId,
      transportAttempts: transport.attempts,
      applicationReplayPosts,
      requests: clone(service.requests),
      commitCount: service.commitCount,
    };
  } finally {
    await scenario.close();
  }
}

async function testP5UnknownReplay({ browser, product, caseDirectory }) {
  const prepared = await prepareLostSaveScenario({ browser, product, caseDirectory, draft: "P5 unknown replay effect" });
  const { scenario, save, operationId, screenshots, transport } = prepared;
  try {
    const { page, service } = scenario;
    service.failNext({ pathname: operationPath("alpha", "a1", operationId), status: 503, body: { error: "controlled operation lookup failure" } });
    await page.locator("#retry-save").click();
    const failedLookup = await service.waitForRequest((entry) => entry.method === "GET" && entry.pathname === operationPath("alpha", "a1", operationId));
    await page.locator("#retry-save").waitFor({ state: "visible", timeout: TIMEOUT });
    await waitForEnabled(page, "#retry-save");
    assert.equal(await page.locator("#note-input").inputValue(), save.body.note, "lookup failure keeps the retryable draft");
    assert.equal(failedLookup.releasedLostSaveConfirmation, true, "the first explicit lookup ends same-operation transport response loss even when lookup fails");

    service.queueResponse({
      method: "GET",
      pathname: operationPath("alpha", "a1", operationId),
      body: { state: "unknown" },
      tag: "controlled-unknown-operation",
    });
    await page.locator("#retry-save").click();
    const unknownLookup = await service.waitForRequest((entry) => entry.method === "GET"
      && entry.pathname === operationPath("alpha", "a1", operationId)
      && requestCount(service, "GET", operationPath("alpha", "a1", operationId)) >= 2);
    await waitForRevision(page, 11, save.body.note);
    const operationGets = service.findRequests((entry) => entry.method === "GET" && entry.pathname === operationPath("alpha", "a1", operationId));
    const saves = p5SaveRequests(service);
    const applicationReplayPosts = requestsAfter(service, unknownLookup).filter((entry) => entry.method === "POST" && entry.pathname === detailPath());
    assert.equal(operationGets.length, 2, "unknown recovery retries lookup with the same operation identity after the retained failure");
    assert.equal(applicationReplayPosts.length, 1, "unknown lookup triggers exactly one application replay after the explicit unknown result");
    assert.equal(saves.length, transport.attempts.length + 1, "only the post-lookup application replay is added to lost transport attempts");
    const replay = applicationReplayPosts[0];
    assert.equal(replay.body.operationId, operationId, "unknown lookup replay retains the same scoped operation identity");
    assert.equal(replay.body.note, save.body.note, "unknown lookup replay retains the same note intent");
    assert.equal(replay.body.baseRevision, save.body.baseRevision, "unknown lookup replay retains the same base revision");
    assert.equal(replay.deduped, true, "server recognizes replayed unchanged scoped identity as its prior effect");
    assert.equal(service.commitCount, 1, "lookup failure and unknown replay still produce exactly one committed effect");
    screenshots.push(await capture(page, caseDirectory, "after-unknown-replay"));
    await assertNoPageErrors(scenario);
    return {
      screenshots,
      operationId,
      transportAttempts: transport.attempts,
      applicationReplayPosts,
      requests: clone(service.requests),
      commitCount: service.commitCount,
    };
  } finally {
    await scenario.close();
  }
}

async function testP5({ browser, product, caseDirectory }) {
  const committedLookup = await testP5CommittedLookup({ browser, product, caseDirectory: path.join(caseDirectory, "committed-lookup") });
  const unknownReplay = await testP5UnknownReplay({ browser, product, caseDirectory: path.join(caseDirectory, "unknown-replay") });
  return {
    screenshots: [...committedLookup.screenshots, ...unknownReplay.screenshots],
    committedLookup,
    unknownReplay,
  };
}

async function testP6({ browser, product, caseDirectory }) {
  const scenario = await createScenario(browser, product);
  const screenshots = [];
  try {
    const { page, service } = scenario;
    await openDetail(scenario, "alpha", "a1");
    await page.locator("#edit").click();
    await page.locator("#note-input").fill("P6 alpha draft that must not leak");
    const oldAlpha = {
      ...clone(service.getRecord("alpha", "a1")),
      note: "Stale alpha generation-zero callback",
      revision: 99,
      exportStatus: "stale-alpha",
      exportRevision: 99,
    };
    const beforeGets = requestCount(service, "GET", detailPath());
    const lateAlpha = service.deferNextResponse({ method: "GET", pathname: detailPath(), body: oldAlpha, tag: "late-alpha-callback" });
    await page.locator("#refresh").click();
    const heldRequest = await lateAlpha.waitForRequest();
    await page.locator("#account").selectOption("beta");
    await page.locator("#notes-view").waitFor({ state: "visible", timeout: TIMEOUT });
    await page.locator("button[data-note-id='a1']").click();
    await waitForRevision(page, 10, "Beta confirmed note");
    service.setRecord("alpha", "a1", {
      note: "Fresh alpha generation-two record",
      revision: 12,
      exportStatus: "complete",
      exportRevision: 4,
    });
    await page.locator("#account").selectOption("alpha");
    await page.locator("#notes-view").waitFor({ state: "visible", timeout: TIMEOUT });
    await page.locator("button[data-note-id='a1']").click();
    await waitForRevision(page, 12, "Fresh alpha generation-two record");
    screenshots.push(await capture(page, caseDirectory, "before-old-alpha-arrives"));
    const sessionBeforeRelease = {
      account: await page.locator("#account").inputValue(),
      revision: normalize(await page.locator("#revision").textContent()),
    };
    lateAlpha.release();
    const releasedResponse = await lateAlpha.waitForResponse();
    await page.waitForTimeout(80);
    assert.match(await page.locator("#confirmed-note").textContent(), /^Fresh alpha generation-two record/i, "late alpha response cannot replace a later alpha generation");
    assert.doesNotMatch(await page.locator("#note-input").inputValue(), /P6 alpha draft/i, "former-account draft is discarded across alpha-to-beta-to-alpha");
    assert.doesNotMatch(normalize(await page.locator("#export-status").textContent()), /stale-alpha|generation-zero/i, "former-account cue cannot affect the replacement alpha generation");
    screenshots.push(await capture(page, caseDirectory, "after-old-alpha-arrives"));
    await assertNoPageErrors(scenario);
    return {
      screenshots,
      barrier: { heldRequest, sessionBeforeRelease, releasedResponse },
      requests: clone(service.requests),
    };
  } finally {
    await scenario.close();
  }
}

async function runMotionVariant({ browser, product, caseDirectory, reducedMotion }) {
  const scenario = await createScenario(browser, product, { reducedMotion });
  const screenshots = [];
  try {
    const { page, service } = scenario;
    await openDetail(scenario);
    await page.locator("#edit").click();
    await page.locator("#note-input").fill(`P7 ${reducedMotion} draft`);
    await page.locator("#note-input").focus();
    service.setRecord("alpha", "a1", { exportStatus: "processing", exportRevision: 2 });
    await dispatchUpdate(page, "alpha", "a1");
    await waitForText(page, "#export-status", "processing");
    let oldAnimation;
    if (reducedMotion === "no-preference") {
      await page.waitForFunction(() => document.querySelector("#export-status")?.getAnimations().some((animation) => animation.playState === "running"), undefined, { timeout: TIMEOUT });
      oldAnimation = await page.evaluate(() => {
        const animation = document.querySelector("#export-status").getAnimations().find((candidate) => candidate.playState === "running");
        window.__shiploopFixtureOldCue = animation;
        return { playState: animation.playState, currentTime: animation.currentTime };
      });
      assert.equal(oldAnimation.playState, "running", "normal-motion status update starts a real Web Animation cue");
    } else {
      await page.waitForTimeout(240);
      assert.equal(await page.locator("#export-status").evaluate((node) => node.getAnimations().length), 0, "reduced motion performs no nonessential status animation");
    }
    screenshots.push(await capture(page, caseDirectory, `${reducedMotion}-before-interruption`));
    service.setRecord("alpha", "a1", { exportStatus: "complete", exportRevision: 3 });
    await dispatchUpdate(page, "alpha", "a1");
    await waitForText(page, "#export-status", "complete");
    const cue = await page.evaluate(() => {
      const old = window.__shiploopFixtureOldCue;
      return old ? { playState: old.playState, currentTime: old.currentTime } : null;
    });
    if (reducedMotion === "no-preference") {
      assert.equal(cue.playState, "idle", "newer export state cancels the older cue before it owns an outcome");
    }
    assert.equal(await page.locator("#note-input").evaluate((node) => document.activeElement === node), true, "status cue does not steal editor focus");
    assert.equal(await page.locator("#note-input").inputValue(), `P7 ${reducedMotion} draft`, "cue completion cannot replace the active draft");
    screenshots.push(await capture(page, caseDirectory, `${reducedMotion}-after-interruption`));
    await assertNoPageErrors(scenario);
    return { screenshots, reducedMotion, oldAnimation, cue, requests: clone(service.requests) };
  } finally {
    await scenario.close();
  }
}

async function testP7({ browser, product, caseDirectory }) {
  const normal = await runMotionVariant({ browser, product, caseDirectory, reducedMotion: "no-preference" });
  const reduced = await runMotionVariant({ browser, product, caseDirectory, reducedMotion: "reduce" });
  return { screenshots: [...normal.screenshots, ...reduced.screenshots], normal, reduced };
}

async function visibilityProbe(scenario) {
  const { context, page, server } = scenario;
  const observer = await context.newPage();
  await observer.goto(`${server.baseURL}/`, { waitUntil: "domcontentloaded" });
  await page.bringToFront();
  await page.waitForTimeout(40);
  const before = await page.evaluate(() => document.visibilityState);
  await observer.bringToFront();
  await page.waitForTimeout(80);
  const after = await page.evaluate(() => document.visibilityState);
  const actual = after === "hidden";
  if (actual) {
    await page.bringToFront();
    await page.waitForTimeout(40);
  } else {
    await observer.close();
    await page.bringToFront();
  }
  return { actual, before, after, observer: actual ? observer : null };
}

async function testPollingWithClock({ browser, product, caseDirectory }) {
  fs.mkdirSync(caseDirectory, { recursive: true });
  const scenario = await createScenario(browser, product, { clock: true });
  const screenshots = [];
  try {
    const { context, page, service } = scenario;
    await openDetail(scenario);
    const beforeVisibleAdvance = requestCount(service, "GET", detailPath());
    await context.clock.runFor(14_000);
    assert.equal(requestCount(service, "GET", detailPath()), beforeVisibleAdvance, "visible polling does not run during the first 14 emulated seconds");
    await context.clock.runFor(1_500);
    await service.waitForRequest((entry) => entry.method === "GET" && entry.pathname === detailPath() && requestCount(service, "GET", detailPath()) === beforeVisibleAdvance + 1);
    screenshots.push(await capture(page, caseDirectory, "clock-visible-poll"));

    await setSyntheticVisibility(page, "hidden");
    const beforeHiddenAdvance = requestCount(service, "GET", detailPath());
    await context.clock.runFor(45_000);
    assert.equal(requestCount(service, "GET", detailPath()), beforeHiddenAdvance, "hidden state pauses all three synthetic 15-second poll opportunities");
    await setSyntheticVisibility(page, "visible");
    await service.waitForRequest((entry) => entry.method === "GET" && entry.pathname === detailPath() && requestCount(service, "GET", detailPath()) === beforeHiddenAdvance + 1);
    screenshots.push(await capture(page, caseDirectory, "clock-visible-resume"));
    await assertNoPageErrors(scenario);
    return {
      screenshots,
      clock: {
        mode: "playwright-clock-emulation",
        visiblePollAfterMs: 15_000,
        visibleNoPollThroughMs: 14_000,
        visibleObservationAdvanceMs: 15_500,
        hiddenAdvanceMs: 45_000,
        visibility: "synthetic-visibility-injection",
        claim: "Timer behavior exercised with Playwright clock emulation; this is not wall-clock or operating-system background validation.",
      },
      requests: clone(service.requests),
    };
  } finally {
    await scenario.close();
  }
}

async function testP8({ browser, product, caseDirectory }) {
  const scenario = await createScenario(browser, product);
  const screenshots = [];
  try {
    const { page, service } = scenario;
    await openDetail(scenario);
    const visibility = await visibilityProbe(scenario);
    await page.locator("#edit").click();
    await page.locator("#note-input").fill("P8 dirty draft survives resume");
    await attachStatusObserver(page);
    await markStatus(page, "before-hidden");
    const beforeGets = requestCount(service, "GET", detailPath());
    if (visibility.actual) {
      await visibility.observer.bringToFront();
      await page.waitForFunction(() => document.visibilityState === "hidden", undefined, { timeout: TIMEOUT });
    } else {
      await setSyntheticVisibility(page, "hidden");
    }
    service.setRecord("alpha", "a1", { exportStatus: "complete", exportRevision: 4 });
    await dispatchUpdate(page, "alpha", "a1");
    await dispatchUpdate(page, "alpha", "a1");
    await dispatchUpdate(page, "alpha", "a1");
    await page.waitForTimeout(120);
    assert.equal(requestCount(service, "GET", detailPath()), beforeGets, "hidden duplicate hints only mark dirty and do not fetch");
    await markStatus(page, "after-hidden-burst");
    screenshots.push(await capture(page, caseDirectory, "hidden-before-resume"));

    service.failNext({ pathname: detailPath(), status: 503, body: { error: "controlled resume refresh failure" } });
    await markStatus(page, "before-resume");
    if (visibility.actual) {
      await page.bringToFront();
      await page.waitForFunction(() => document.visibilityState === "visible", undefined, { timeout: TIMEOUT });
    } else {
      await setSyntheticVisibility(page, "visible");
    }
    await service.waitForRequest((entry) => entry.method === "GET" && entry.pathname === detailPath() && requestCount(service, "GET", detailPath()) > beforeGets);
    await page.locator("#refresh").waitFor({ state: "visible", timeout: TIMEOUT });
    const failureStatus = await waitForExplicitFetchError(page);
    assert.ok(failureStatus.some((value) => EXPLICIT_ERROR.test(value)), "resume fetch failure is described semantically in a live status region");
    assert.equal(await page.locator("#refresh").isEnabled(), true, "Refresh remains usable after the failed reconciliation");
    assert.equal(await page.locator("#note-input").inputValue(), "P8 dirty draft survives resume", "failure does not erase the dirty draft");
    await page.waitForTimeout(180);
    const persistentFailureStatus = await visibleStatusTexts(page);
    assert.ok(persistentFailureStatus.some((value) => EXPLICIT_ERROR.test(value)), "explicit fetch error persists until the user chooses Refresh");
    await markStatus(page, "after-error");
    const historyBeforeRecovery = await page.evaluate(() => window.__shiploopFixtureStatusEvents || []);
    const exportIndexBeforeRecovery = await page.evaluate(() => (window.__shiploopFixtureStatusNames || []).indexOf("export-status"));
    const resumeStart = historyBeforeRecovery.findIndex((event) => event.kind === "mark" && event.label === "before-resume");
    const failureEnd = historyBeforeRecovery.findIndex((event) => event.kind === "mark" && event.label === "after-error");
    assert.ok(exportIndexBeforeRecovery >= 0 && resumeStart >= 0 && failureEnd > resumeStart, "resume trace contains an export status boundary");
    const preRecoveryExportMutations = historyBeforeRecovery.slice(resumeStart + 1, failureEnd)
      .filter((event) => event.kind === "mutation")
      .map((event) => event.values[exportIndexBeforeRecovery] || "")
      .filter(Boolean);
    assert.equal(preRecoveryExportMutations.some((value) => /\bidle\b|\bprocessing\b|\bcomplete\b/i.test(value)), false, "resume failure does not replay stale export-state history before recovery");
    await markStatus(page, "before-retry");
    await page.locator("#refresh").click();
    await waitForText(page, "#export-status", "complete");
    await page.waitForTimeout(40);
    await markStatus(page, "after-complete");
    assert.equal(await page.locator("#note-input").inputValue(), "P8 dirty draft survives resume", "reconciliation does not erase the dirty draft");
    const getsAfterRecovery = requestCount(service, "GET", detailPath());
    assert.equal(getsAfterRecovery, beforeGets + 2, "duplicate hidden hints coalesce to one failed resume fetch and one explicit retry");
    await page.waitForTimeout(220);
    await markStatus(page, "after-settled");
    const history = await readStatusHistory(page);
    const postRecoveryExportMutations = statusValuesBetween(history, "export-status", "before-retry", "after-complete");
    assert.ok(postRecoveryExportMutations.some((value) => /complete/i.test(value)), "authoritative resumed state is announced in the status area after successful Refresh");
    assert.equal(postRecoveryExportMutations.some((value) => /\bidle\b|\bprocessing\b/i.test(value)), false, "stale intermediate export states do not reappear before the latest complete state");
    const settledExportMutations = statusValuesBetween(history, "export-status", "after-complete", "after-settled");
    assert.equal(settledExportMutations.some((value) => /\bidle\b|\bprocessing\b/i.test(value)), false, "no late stale export state reappears after the current complete state");
    assert.equal((await visibleStatusTexts(page)).some((value) => EXPLICIT_ERROR.test(value)), false, "successful Refresh clears the prior explicit fetch error");
    screenshots.push(await capture(page, caseDirectory, "after-resume-recovery"));
    await assertNoPageErrors(scenario);
    const polling = await testPollingWithClock({ browser, product, caseDirectory: path.join(caseDirectory, "polling-clock") });
    return { screenshots: [...screenshots, ...polling.screenshots], visibility: { actual: visibility.actual, before: visibility.before, after: visibility.after, mode: visibility.actual ? "two-tab-browser" : "synthetic-visibility-injection" }, statusHistory: history, polling, requests: clone(service.requests) };
  } finally {
    if (scenario.context) {
      await scenario.close();
    }
  }
}

async function testNewerDraftDuringPendingSave({ browser, product, caseDirectory }) {
  const scenario = await createScenario(browser, product);
  const screenshots = [];
  try {
    const { page, service } = scenario;
    await openDetail(scenario);
    await page.locator("#edit").click();
    await page.locator("#note-input").fill("X1 first save intent");
    const delayedResponse = service.deferNextSaveResponse();
    await page.locator("#save").click();
    const committed = await delayedResponse.waitForCommit();
    assert.equal(service.commitCount, 1, "X1 response gate is reached only after the real atomic save commit");
    assert.equal(committed.record.note, "X1 first save intent", "X1 gates the committed first intent rather than a fabricated response");
    await page.locator("#note-input").fill("X1 newer draft typed while save is pending");
    assert.equal(await page.locator("#note-input").inputValue(), "X1 newer draft typed while save is pending", "newer draft is present before the held response is released");
    screenshots.push(await capture(page, caseDirectory, "before-delayed-success"));
    delayedResponse.release();
    const releasedResponse = await delayedResponse.waitForResponse();
    await waitForRevision(page, 11, "X1 first save intent");
    assert.equal(await page.locator("#confirmed-note").textContent(), "X1 first save intent", "confirmed state reflects the completed first intent");
    assert.equal(await page.locator("#note-input").inputValue(), "X1 newer draft typed while save is pending", "late save success cannot overwrite a newer draft");
    screenshots.push(await capture(page, caseDirectory, "after-delayed-success"));
    await assertNoPageErrors(scenario);
    return { screenshots, barrier: { committed, releasedResponse }, requests: clone(service.requests) };
  } finally {
    await scenario.close();
  }
}

function screenshotFiles(directory) {
  const files = [];
  function visit(current) {
    for (const entry of fs.readdirSync(current, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const file = path.join(current, entry.name);
      if (entry.isDirectory()) visit(file);
      else if (entry.isFile() && entry.name.endsWith(".png")) files.push(file);
    }
  }
  visit(directory);
  return files;
}

async function runCase(definition, shared) {
  const caseDirectory = path.join(shared.output, definition.id);
  fs.mkdirSync(caseDirectory, { recursive: true });
  const result = { id: definition.id, family: definition.family, title: definition.title, status: "failed", startedAt: new Date().toISOString(), screenshots: [] };
  try {
    const evidence = await definition.run({ ...shared, caseDirectory });
    result.status = "passed";
    result.evidence = evidence;
    result.screenshots = evidence.screenshots || [];
  } catch (error) {
    result.error = { message: error.message, stack: error.stack };
  }
  result.screenshots = screenshotFiles(caseDirectory);
  result.finishedAt = new Date().toISOString();
  return result;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  createFreshOutputDirectory(options.output);
  const { api: playwright, modulePath } = loadPlaywright();
  const executablePath = process.env.BROWSER_EXECUTABLE_PATH || null;
  if (executablePath && !fs.existsSync(executablePath)) throw new Error(`Browser executable is missing: ${executablePath}`);
  const browser = await playwright.chromium.launch({ ...(executablePath ? { executablePath } : {}), headless: !options.headed });
  const servedProduct = hashServedProduct(options.product);
  const harnessSource = hashHarnessSource();
  const baselineP1 = loadBaselineP1(options.baselineReport);
  const report = {
    harness: "shiploop-ui-consumer-browser",
    startedAt: new Date().toISOString(),
    command: process.argv.slice(2),
    mode: options.mode,
    product: options.product,
    productSha256: servedProduct.sha256,
    servedProductFiles: servedProduct.files,
    harnessSha256: harnessSource.sha256,
    harnessSourceFiles: harnessSource.files,
    playwrightModule: modulePath,
    browserExecutable: executablePath || "playwright-managed",
    browserVersion: browser.version(),
    csp: CSP,
    visibilityClaim: "P8 records whether two-tab browser visibility occurred. When it does not, the test labels synthetic visibility injection and makes no browser-lifecycle claim.",
    baselineComparison: baselineP1 ? { report: baselineP1.path, productSha256: baselineP1.productSha256 } : null,
    cases: [],
  };
  const definitions = [
    { id: "P1", family: "primary", title: "existing list/detail/edit/save/cancel/back journeys", run: testP1 },
    { id: "P2", family: "primary", title: "export update preserves active editor state", run: testP2 },
    { id: "P3", family: "primary", title: "reversed responses cannot regress confirmed state", run: testP3 },
    { id: "P4", family: "primary", title: "conflict reapply uses current revision and a new operation id", run: testP4 },
    { id: "P5", family: "primary", title: "lost save response retries by operation lookup without duplicate effect", run: testP5 },
    { id: "P6", family: "primary", title: "account change invalidates old callbacks and drafts", run: testP6 },
    { id: "P7", family: "primary", title: "interrupted normal/reduced-motion status cues", run: testP7 },
    { id: "P8", family: "primary", title: "hidden/resume reconciliation and burst coalescing", run: testP8 },
    { id: "X1", family: "extra", title: "newer draft survives delayed save success", run: testNewerDraftDuringPendingSave },
  ];
  report.registeredPrimaryCaseFamilies = definitions.filter((item) => item.family === "primary").map((item) => item.id);
  report.registeredExtraCases = definitions.filter((item) => item.family === "extra").map((item) => item.id);
  const defaultSelection = options.mode === "baseline" ? definitions.slice(0, 1) : definitions;
  const selected = options.cases
    ? definitions.filter((definition) => options.cases.includes(definition.id))
    : defaultSelection;
  if (options.cases && selected.length !== options.cases.length) {
    const known = new Set(selected.map((definition) => definition.id));
    throw new Error(`Unknown --case value: ${options.cases.filter((id) => !known.has(id)).join(", ")}`);
  }
  try {
    for (const definition of selected) {
      const result = await runCase(definition, { browser, product: options.product, output: options.output, baselineP1 });
      report.cases.push(result);
      process.stdout.write(`${result.status.toUpperCase()} ${result.id} — ${result.title}\n`);
    }
  } finally {
    await browser.close();
    report.finishedAt = new Date().toISOString();
    report.passed = report.cases.filter((item) => item.status === "passed").length;
    report.failed = report.cases.filter((item) => item.status !== "passed").length;
    report.executedPrimaryCaseFamilies = report.cases.filter((item) => item.family === "primary").map((item) => item.id);
    report.executedExtraCases = report.cases.filter((item) => item.family === "extra").map((item) => item.id);
    fs.writeFileSync(path.join(options.output, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
  }
  if (report.failed) process.exitCode = 1;
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exitCode = 1;
});
