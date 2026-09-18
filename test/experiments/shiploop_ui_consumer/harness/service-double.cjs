"use strict";

const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

const CSP = [
  "default-src 'self'",
  "base-uri 'none'",
  "object-src 'none'",
  "script-src 'self'",
  "style-src 'self'",
  "img-src 'self'",
  "connect-src 'self'",
  "font-src 'self'",
  "frame-ancestors 'none'",
].join("; ");

const DEFAULT_DEFERRED_WAIT_TIMEOUT_MS = Number.isFinite(Number(process.env.SERVICE_DEFERRED_TIMEOUT_MS || process.env.BROWSER_TEST_TIMEOUT_MS))
  && Number(process.env.SERVICE_DEFERRED_TIMEOUT_MS || process.env.BROWSER_TEST_TIMEOUT_MS) > 0
  ? Number(process.env.SERVICE_DEFERRED_TIMEOUT_MS || process.env.BROWSER_TEST_TIMEOUT_MS)
  : 5000;

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function fixture() {
  return {
    alpha: {
      a1: {
        id: "a1",
        title: "Alpha marsh observations",
        note: "Alpha confirmed note. ".repeat(32),
        revision: 10,
        exportStatus: "idle",
        exportRevision: 1,
      },
      a2: {
        id: "a2",
        title: "Alpha ridge observations",
        note: "Alpha ridge confirmed note.",
        revision: 10,
        exportStatus: "idle",
        exportRevision: 1,
      },
    },
    beta: {
      a1: {
        id: "a1",
        title: "Beta marsh observations",
        note: "Beta confirmed note. ".repeat(32),
        revision: 10,
        exportStatus: "idle",
        exportRevision: 1,
      },
      a2: {
        id: "a2",
        title: "Beta ridge observations",
        note: "Beta ridge confirmed note.",
        revision: 10,
        exportStatus: "idle",
        exportRevision: 1,
      },
    },
  };
}

function json(res, status, body) {
  const text = JSON.stringify(body);
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "content-length": Buffer.byteLength(text),
  });
  res.end(text);
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function waitWithTimeout(promise, label, timeoutMs = DEFAULT_DEFERRED_WAIT_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`Timed out waiting for deferred ${label} after ${timeoutMs}ms`)), timeoutMs);
    promise.then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      (error) => {
        clearTimeout(timer);
        reject(error);
      },
    );
  });
}

function createDeferredControl(label) {
  let releaseGate;
  let firstResolve;
  let responseResolve;
  const gate = new Promise((resolve) => { releaseGate = resolve; });
  const first = new Promise((resolve) => { firstResolve = resolve; });
  const response = new Promise((resolve) => { responseResolve = resolve; });
  return {
    gate,
    release: releaseGate,
    notifyFirst: firstResolve,
    notifyResponse: responseResolve,
    waitForFirst: (phase, timeoutMs) => waitWithTimeout(first, `${label} ${phase}`, timeoutMs),
    waitForResponse: (timeoutMs) => waitWithTimeout(response, `${label} response`, timeoutMs),
  };
}

function decode(segment) {
  return decodeURIComponent(segment);
}

function operationKey(account, noteId, operationId) {
  return `${account}\u0000${noteId}\u0000${operationId}`;
}

function mimeType(file) {
  return {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".ico": "image/x-icon",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
  }[path.extname(file)] || "application/octet-stream";
}

class ServiceDouble {
  constructor(seed = fixture()) {
    this.seed = clone(seed);
    this.reset();
  }

  reset() {
    this.accounts = clone(this.seed);
    this.requests = [];
    this.rules = [];
    this.operations = new Map();
    this.deferredControls = [];
    this.deferredNextSave = null;
    this.lostSaveConfirmations = new Map();
    this.commitCount = 0;
    this.dropNextSave = false;
    this.delayNextSaveMs = 0;
  }

  getRecord(account, noteId) {
    const record = this.accounts[account]?.[noteId];
    if (!record) throw new Error(`Unknown fixture record ${account}/${noteId}`);
    return record;
  }

  setRecord(account, noteId, patch) {
    Object.assign(this.getRecord(account, noteId), clone(patch));
    return clone(this.getRecord(account, noteId));
  }

  replaceRecord(account, noteId, record) {
    this.accounts[account][noteId] = clone(record);
    return clone(this.accounts[account][noteId]);
  }

  queueResponse({ method = "GET", pathname, status = 200, body, delayMs = 0, close = false, tag = "scripted" }) {
    if (!pathname) throw new Error("queueResponse requires pathname");
    this.rules.push({ method: method.toUpperCase(), pathname, status, body: body === undefined ? undefined : clone(body), delayMs, close, tag });
  }

  deferNextResponse({ method = "GET", pathname, status = 200, body, tag = "deferred" }) {
    if (!pathname) throw new Error("deferNextResponse requires pathname");
    const deferred = createDeferredControl(tag);
    const control = {
      release: deferred.release,
      waitForRequest: (timeoutMs) => deferred.waitForFirst("request", timeoutMs),
      waitForResponse: (timeoutMs) => deferred.waitForResponse(timeoutMs),
    };
    this.deferredControls.push(control);
    this.rules.push({
      method: method.toUpperCase(),
      pathname,
      status,
      body: body === undefined ? undefined : clone(body),
      delayMs: 0,
      close: false,
      tag,
      deferred: { gate: deferred.gate, startedResolve: deferred.notifyFirst, responseResolve: deferred.notifyResponse },
    });
    return control;
  }

  deferNextSaveResponse() {
    if (this.deferredNextSave) throw new Error("A deferred save response is already pending");
    const deferred = createDeferredControl("save");
    const control = {
      release: deferred.release,
      waitForCommit: (timeoutMs) => deferred.waitForFirst("commit", timeoutMs),
      waitForResponse: (timeoutMs) => deferred.waitForResponse(timeoutMs),
    };
    this.deferredControls.push(control);
    this.deferredNextSave = {
      gate: deferred.gate,
      committedResolve: deferred.notifyFirst,
      responseResolve: deferred.notifyResponse,
    };
    return control;
  }

  releaseAllDeferred() {
    for (const control of this.deferredControls) control.release();
  }

  failNext({ method = "GET", pathname, status = 503, body = { error: "controlled failure" }, delayMs = 0, tag = "controlled-failure" }) {
    this.queueResponse({ method, pathname, status, body, delayMs, tag });
  }

  dropNextSaveResponse() {
    this.dropNextSave = true;
  }

  delayNextSaveResponse(delayMs) {
    this.delayNextSaveMs = delayMs;
  }

  findRequests(predicate) {
    return this.requests.filter(predicate);
  }

  getLostSaveConfirmation(account, noteId, operationId) {
    const loss = this.lostSaveConfirmations.get(operationKey(account, noteId, operationId));
    return loss ? clone(loss) : null;
  }

  releaseLostSaveConfirmationForLookup(method, pathname, entry) {
    if (method !== "GET") return;
    const match = pathname.match(/^\/api\/accounts\/([^/]+)\/notes\/([^/]+)\/operations\/([^/]+)$/);
    if (!match) return;
    const [, rawAccount, rawNoteId, rawOperationId] = match;
    const loss = this.lostSaveConfirmations.get(operationKey(decode(rawAccount), decode(rawNoteId), decode(rawOperationId)));
    if (!loss || !loss.active) return;
    loss.active = false;
    loss.releasedBy = { method, pathname, at: entry.at };
    entry.releasedLostSaveConfirmation = true;
  }

  dropSaveConfirmation(res, entry, loss) {
    loss.transportAttempts += 1;
    entry.confirmationLost = true;
    entry.transportAttempt = loss.transportAttempts;
    // Starting a deliberately incomplete response makes fetch fail after the
    // server has committed, without inviting Chrome to replay a bare socket
    // reset as a successful deduplicated POST. Every same-operation POST stays
    // in this state until an explicit operation lookup reaches the double.
    const confirmation = JSON.stringify({ record: {} });
    res.writeHead(200, {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "content-length": Buffer.byteLength(confirmation),
    });
    res.flushHeaders?.();
    res.write(confirmation.slice(0, -1));
    const truncate = setTimeout(() => res.destroy(), 40);
    truncate.unref?.();
  }

  async waitForRequest(predicate, timeoutMs = 5000) {
    const deadline = Date.now() + timeoutMs;
    for (;;) {
      const found = this.requests.find(predicate);
      if (found) return found;
      if (Date.now() >= deadline) throw new Error("Timed out waiting for controlled service request");
      await delay(20);
    }
  }

  takeRule(method, pathname) {
    const index = this.rules.findIndex((rule) => rule.method === method && rule.pathname === pathname);
    return index === -1 ? null : this.rules.splice(index, 1)[0];
  }

  async handle(req, res) {
    const url = new URL(req.url, "http://fixture.local");
    const pathname = url.pathname;
    const rawBody = await new Promise((resolve, reject) => {
      let body = "";
      req.setEncoding("utf8");
      req.on("data", (chunk) => { body += chunk; });
      req.on("end", () => resolve(body));
      req.on("error", reject);
    });
    let body = null;
    if (rawBody) {
      try { body = JSON.parse(rawBody); } catch { body = rawBody; }
    }
    const entry = { method: req.method, pathname, body: clone(body), at: new Date().toISOString() };
    this.requests.push(entry);
    this.releaseLostSaveConfirmationForLookup(req.method, pathname, entry);

    const scripted = this.takeRule(req.method, pathname);
    if (scripted) {
      entry.scripted = scripted.tag;
      if (scripted.deferred) {
        scripted.deferred.startedResolve(entry);
        await scripted.deferred.gate;
      }
      if (scripted.delayMs) await delay(scripted.delayMs);
      if (scripted.close) {
        req.socket.destroy();
        scripted.deferred?.responseResolve({ entry, closed: true });
        return;
      }
      json(res, scripted.status, scripted.body);
      scripted.deferred?.responseResolve({ entry, status: scripted.status });
      return;
    }

    const operationMatch = pathname.match(/^\/api\/accounts\/([^/]+)\/notes\/([^/]+)\/operations\/([^/]+)$/);
    if (req.method === "GET" && operationMatch) {
      const [, rawAccount, rawNoteId, rawOperationId] = operationMatch;
      const account = decode(rawAccount);
      const noteId = decode(rawNoteId);
      const operationId = decode(rawOperationId);
      const operation = this.operations.get(operationKey(account, noteId, operationId));
      json(res, 200, operation ? { state: "committed", record: clone(operation.record) } : { state: "unknown" });
      return;
    }

    const noteMatch = pathname.match(/^\/api\/accounts\/([^/]+)\/notes\/([^/]+)$/);
    if (noteMatch) {
      const [, rawAccount, rawNoteId] = noteMatch;
      const account = decode(rawAccount);
      const noteId = decode(rawNoteId);
      const record = this.accounts[account]?.[noteId];
      if (!record) {
        json(res, 404, { error: "not found" });
        return;
      }
      if (req.method === "GET") {
        json(res, 200, clone(record));
        return;
      }
      if (req.method === "POST") {
        await this.handleSave(req, res, entry, account, noteId, record, body);
        return;
      }
    }

    const listMatch = pathname.match(/^\/api\/accounts\/([^/]+)\/notes$/);
    if (req.method === "GET" && listMatch) {
      const account = decode(listMatch[1]);
      const notes = this.accounts[account] ? Object.values(this.accounts[account]).map(clone) : null;
      if (!notes) {
        json(res, 404, { error: "not found" });
        return;
      }
      json(res, 200, notes);
      return;
    }

    json(res, 404, { error: "unknown fixture endpoint" });
  }

  async handleSave(req, res, entry, account, noteId, record, body) {
    if (!body || typeof body.note !== "string" || !Number.isInteger(body.baseRevision) || typeof body.operationId !== "string" || !body.operationId) {
      json(res, 400, { error: "invalid save body" });
      return;
    }
    const key = operationKey(account, noteId, body.operationId);
    const existing = this.operations.get(key);
    const sameIntent = existing && existing.intent.note === body.note && existing.intent.baseRevision === body.baseRevision;
    if (sameIntent) {
      entry.deduped = true;
      const loss = this.lostSaveConfirmations.get(key);
      if (loss?.active) {
        this.dropSaveConfirmation(res, entry, loss);
        return;
      }
      json(res, 200, { record: clone(existing.record) });
      return;
    }
    if (existing || body.baseRevision !== record.revision) {
      entry.conflict = true;
      json(res, 409, { record: clone(record) });
      return;
    }

    const committed = { ...record, note: body.note, revision: record.revision + 1 };
    this.accounts[account][noteId] = committed;
    this.operations.set(key, {
      intent: { note: body.note, baseRevision: body.baseRevision },
      record: clone(committed),
    });
    this.commitCount += 1;
    entry.committed = true;
    if (this.dropNextSave) {
      this.dropNextSave = false;
      const loss = { active: true, transportAttempts: 0, releasedBy: null };
      this.lostSaveConfirmations.set(key, loss);
      this.dropSaveConfirmation(res, entry, loss);
      return;
    }
    const deferred = this.deferredNextSave;
    if (deferred) {
      this.deferredNextSave = null;
      deferred.committedResolve({ entry, record: clone(committed) });
      await deferred.gate;
      json(res, 200, { record: clone(committed) });
      deferred.responseResolve({ entry, status: 200 });
      return;
    }
    if (this.delayNextSaveMs) {
      const delayMs = this.delayNextSaveMs;
      this.delayNextSaveMs = 0;
      await delay(delayMs);
    }
    json(res, 200, { record: clone(committed) });
  }
}

async function createStaticServer({ productDir, service = new ServiceDouble(), csp = CSP }) {
  const root = path.resolve(productDir);
  const server = http.createServer((req, res) => {
    if (new URL(req.url, "http://fixture.local").pathname.startsWith("/api/")) {
      service.handle(req, res).catch((error) => {
        if (!res.headersSent) json(res, 500, { error: error.message });
        else res.destroy(error);
      });
      return;
    }

    const requested = decodeURIComponent(new URL(req.url, "http://fixture.local").pathname);
    const relative = requested === "/" ? "index.html" : requested.replace(/^\/+/, "");
    const file = path.resolve(root, relative);
    if (file !== root && !file.startsWith(`${root}${path.sep}`)) {
      res.writeHead(403).end();
      return;
    }
    fs.readFile(file, (error, content) => {
      if (error) {
        res.writeHead(error.code === "ENOENT" ? 404 : 500).end();
        return;
      }
      res.writeHead(200, {
        "content-type": mimeType(file),
        "content-security-policy": csp,
        "cache-control": "no-store",
      });
      res.end(content);
    });
  });

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      server.off("error", reject);
      resolve();
    });
  });
  const address = server.address();
  return {
    baseURL: `http://127.0.0.1:${address.port}`,
    service,
    close: () => {
      service.releaseAllDeferred();
      return new Promise((resolve, reject) => {
        const forceClose = setTimeout(() => server.closeAllConnections?.(), 50);
        server.close((error) => {
          clearTimeout(forceClose);
          if (error) reject(error);
          else resolve();
        });
      });
    },
  };
}

module.exports = { CSP, ServiceDouble, createStaticServer, fixture };
