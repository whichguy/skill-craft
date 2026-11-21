const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const fs = require('node:fs');
const http = require('node:http');
const net = require('node:net');
const os = require('node:os');
const path = require('node:path');
const readline = require('node:readline');
const { setTimeout: wait } = require('node:timers/promises');
const { isDeepStrictEqual } = require('node:util');

const root = path.resolve(__dirname, '..');
const entry = 'server.js';
const rules = 'game';
const testDirectory = path.join(root, 'test') + path.sep;
const portVariable = 'PORT';
const defaultPort = 3000;
const rows = 10;
const columns = 10;
const paths = { page: '/', start: '/api/new', fire: '/api/fire' };
const instrument = path.join(__dirname, 'instrument.cjs');
const reporter = './acceptance/reporter.cjs';
const host = '127.0.0.1';
const outcomes = new Set(['miss', 'hit', 'sunk']);

function tempDirectory(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'battleship-acceptance-'));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  return directory;
}

function childProcess(t, command, args, options = {}) {
  const child = spawn(command, args, options);
  let stdout = '';
  let stderr = '';
  child.stdout?.on('data', chunk => { stdout += chunk; });
  child.stderr?.on('data', chunk => { stderr += chunk; });
  const finished = new Promise(resolve => {
    child.once('error', error => resolve({ error, stdout, stderr }));
    child.once('close', (code, signal) => resolve({ code, signal, stdout, stderr }));
  });
  let closed = false;
  finished.then(() => { closed = true; });
  const stop = async () => {
    if (closed || !child.pid) return;
    child.kill('SIGTERM');
    const timer = setTimeout(() => child.kill('SIGKILL'), 800).unref();
    await finished;
    clearTimeout(timer);
  };
  t.after(stop);
  return { child, finished, stop, stderr: () => stderr, closed: () => closed };
}

async function listen(server, port = 0) {
  server.listen(port, host);
  await once(server, 'listening');
  return server.address().port;
}

async function freePort(candidate = 0) {
  const reservation = net.createServer();
  const port = await listen(reservation, candidate);
  await new Promise((resolve, reject) => reservation.close(error => error ? reject(error) : resolve()));
  return port;
}

function canConnect(port) {
  return new Promise(resolve => {
    const socket = net.connect(port, host);
    socket.setTimeout(250);
    function complete(success) {
      socket.destroy();
      resolve(success);
    }
    socket.on('connect', () => complete(true));
    socket.on('error', () => complete(false));
    socket.on('timeout', () => complete(false));
  });
}

async function eventually(read, description, timeout = 5000) {
  const deadline = Date.now() + timeout;
  do {
    const result = await read();
    if (result) return result;
    await wait(20);
  } while (Date.now() < deadline);
  assert.fail(description);
}

function cleanCheckout(t) {
  const directory = tempDirectory(t);
  for (const item of fs.readdirSync(root)) {
    if (['.git', 'acceptance', 'ratchet', 'node_modules'].includes(item)) continue;
    fs.cpSync(path.join(root, item), path.join(directory, item), {
      recursive: true,
      filter: source => path.basename(source) !== 'node_modules',
    });
  }
  return directory;
}

async function server(t, observable, options = {}) {
  const cwd = options.clean ? cleanCheckout(t) : root;
  const capture = options.unset || options.ephemeral || options.capture;
  const port = capture ? undefined : await freePort(options.port);
  const env = { ...process.env, NODE_PATH: '' };
  delete env[portVariable];
  if (options.ephemeral) env[portVariable] = '0';
  if (options.capture) env[portVariable] = String(options.port);
  if (port !== undefined) env[portVariable] = String(port);
  if (capture) env.RATCHET_CAPTURE_PORT = '1';
  if (options.observeRules) env.RATCHET_RULES_FILE = path.join(cwd, rules);
  const instrumented = capture || options.observeRules;
  const args = instrumented ? ['--require', instrument, entry] : [entry];
  const processControl = childProcess(t, process.execPath, args, {
    cwd, env, stdio: ['ignore', 'ignore', 'pipe', 'ipc'],
  });
  const observations = [];
  processControl.child.on('message', message => observations.push(message));
  const ready = await eventually(async () => {
    const actual = port ?? observations.find(message => message.kind === 'bound')?.address?.port;
    if (processControl.closed()) return { started: false };
    if (actual && await canConnect(actual)) return { started: true, port: actual };
  }, observable + ' — no HTTP listener became reachable.');
  // Startup absence is a missing user-visible feature, including in the empty baseline.
  const detail = fs.existsSync(path.join(cwd, entry)) ? processControl.stderr().trim() : '';
  assert.ok(ready.started, observable + ' — no HTTP game became reachable.' +
    (detail ? '\n' + detail : ''));

  const base = `http://${host}:${ready.port}`;
  const request = (route, init) => fetch(base + route, {
    signal: AbortSignal.any([t.signal, AbortSignal.timeout(3500)]),
    ...init,
  });
  let identifiedBy;
  const api = {
    base,
    observations,
    stop: processControl.stop,
    page: () => request(paths.page),
    async newGame() {
      const count = observations.filter(message => message.creation).length;
      const reply = await response(await request(paths.start));
      if (options.observeRules) {
        // IPC is emitted before the HTTP response, on a separate stream.
        await wait(10);
      }
      const creation = observations.filter(message => message.creation)[count];
      const identifier = identifiedBy ? identifiedBy(reply.json) : idSelectors(reply.json)[0](reply.json);
      return { reply, id: identifier, creation, cells: placement(creation?.snapshot) };
    },
    identifyBy: selector => { identifiedBy = selector; },
    fire(game, square) {
      return api.rawFire(JSON.stringify({ game, row: square[0], col: square[1] }));
    },
    async rawFire(body) {
      return response(await request(paths.fire, {
        method: 'POST', headers: { 'content-type': 'application/json' }, body,
      }));
    },
    async malformedFire(game, square) {
      const [row, col] = square;
      const malformed = ['', '{"game":', 'null', '[]', JSON.stringify({ game, row }),
        JSON.stringify({ game, col }), JSON.stringify({ game, row: row + 0.5, col }),
        JSON.stringify({ game, row, col: col + 0.5 })];
      for (const body of malformed) {
        try {
          await api.rawFire(body);
        } catch (error) {
          if (error.cause?.code !== 'UND_ERR_SOCKET') throw error;
        }
      }
    },
    async paddedFire(game, square, bytes) {
      const json = JSON.stringify({ game, row: square[0], col: square[1] });
      try {
        return await api.rawFire(json.padEnd(bytes, ' '));
      } catch (error) {
        if (error.cause?.code !== 'UND_ERR_SOCKET') throw error;
        return { ok: false };
      }
    },
    async abandonFire(game, square) {
      const json = JSON.stringify({ game, row: square[0], col: square[1] });
      const socket = net.connect(ready.port, host);
      socket.on('error', () => {});
      try {
        await once(socket, 'connect');
        socket.write(`POST ${paths.fire} HTTP/1.1\r\nHost: ${host}\r\n` +
          'Content-Type: application/json\r\n' +
          `Content-Length: ${Buffer.byteLength(json) + 1}\r\n\r\n${json}`);
        await wait(35);
      } finally {
        socket.destroy();
      }
    },
  };
  return api;
}

async function response(reply) {
  const body = await reply.text();
  let json;
  try { json = JSON.parse(body); } catch { /* Callers assert only their required format. */ }
  return { ok: reply.ok, status: reply.status, headers: reply.headers, body, json };
}

function idSelectors(json) {
  const identity = value => value;
  if (json && typeof json === 'object' && !Array.isArray(json)) {
    const fields = Object.keys(json);
    const known = ['game', 'id', 'gameId', ...fields.filter(key => /id$/i.test(key))];
    const selectors = [...new Set([...known, ...fields])].filter(key => Object.hasOwn(json, key))
      .map(key => value => value?.[key]);
    return [...selectors, identity];
  }
  return [identity];
}

function matchesGameId(json, submitted) {
  return idSelectors(json).some(select => isDeepStrictEqual(select(json), submitted));
}

function isShot(reply) {
  return outcomes.has(reply.json?.result);
}

function unknownId(id) {
  const token = 'unrecognized-' + require('node:crypto').randomUUID();
  if (typeof id === 'number') return Number.MAX_SAFE_INTEGER - Math.floor(Math.random() * 1000000);
  if (id && typeof id === 'object') return Array.isArray(id) ? [token] : { unrecognized: token };
  return token;
}

function boardSquares(origin = 0) {
  return Array.from({ length: rows * columns }, (_, index) =>
    [origin + Math.floor(index / columns), origin + index % columns]);
}

async function coordinates(api) {
  // Probe a separate round, preferring the plan's named JSON field and
  // zero-based coordinates. Retain whichever representation the API accepts.
  for (const [origin, edge] of [[0, 0], [1, rows]]) {
    const { reply } = await api.newGame();
    const json = reply.json;
    for (const candidate of idSelectors(json)) {
      const shot = await api.fire(candidate(json), [edge, edge]);
      if (shot.ok && isShot(shot)) {
        api.identifyBy(candidate);
        return origin;
      }
    }
  }
  return 0;
}

function placement(snapshot) {
  const board = snapshot?.board;
  let squares;
  if (Array.isArray(board) && board.length === rows &&
      board.every(row => Array.isArray(row) && row.length === columns)) {
    squares = board.flat();
  } else if (Array.isArray(board) && board.length === rows * columns) {
    squares = board;
  } else if (Array.isArray(board?.entries)) {
    const cells = new Map(board.entries.map(([key, value]) => [String(key).replace(/[: ]/, ','), value]));
    const keys = [...cells.keys()];
    if (keys.every(key => /^\d,\d$/.test(key))) {
      squares = boardSquares().map(square => cells.get(String(square)) ?? null);
    } else if (keys.every(key => /^\d{1,2}$/.test(key))) {
      squares = boardSquares().map((_, index) => cells.get(String(index)) ?? null);
    } else {
      return undefined;
    }
  } else {
    return undefined;
  }
  const known = snapshot?.labels;
  const hasZero = squares.includes(0);
  const usesZeroAsWater = hasZero && !squares.some(value => value == null || value === -1) &&
    (known?.length ? !known.includes(0) : squares.filter(value => value === 0).length > squares.length / 2);
  const cells = squares.map(value => {
    if (value == null || value === false || value === -1 || value === '' ||
        (usesZeroAsWater && value === 0) ||
        typeof value === 'string' && /^(?:water|empty|[.~])$/i.test(value)) return null;
    if (typeof value !== 'object') return value;
    const field = ['shipId', 'shipIndex', 'ship', 'id'].find(key => Object.hasOwn(value, key));
    const ship = value[field];
    return ship && typeof ship === 'object' ? ship.id ?? ship.name : ship;
  });
  if (cells.some(cell => cell === undefined || typeof cell === 'object' && cell !== null) ||
      cells.every(cell => cell === null) || cells.some(cell => cell === true)) return undefined;
  return cells;
}

function preferredPort(api) {
  return api.observations.find(message => message.kind === 'listen')?.requested;
}

async function runRuleTests(t, trace = false) {
  const env = { ...process.env };
  const traceFile = trace && path.join(tempDirectory(t), 'rule-calls.ndjson');
  const args = [];
  if (trace) {
    args.push('--require', instrument);
    env.RATCHET_RULES_FILE = path.join(root, rules);
    env.RATCHET_TRACE_FILE = traceFile;
  }
  args.push('--test', '--test-timeout', '10000', '--test-reporter', reporter);
  const execution = childProcess(t, process.execPath, args, { cwd: root, env });
  const result = await execution.finished;
  const parseLines = data => data.split('\n').filter(Boolean).flatMap(line => {
    try { return [JSON.parse(line)]; } catch { return []; }
  });
  const cases = parseLines(result.stdout).filter(item =>
    item.file?.startsWith(testDirectory) && item.caseType !== 'suite' && !item.skip && !item.todo);
  const events = traceFile && fs.existsSync(traceFile) ? parseLines(fs.readFileSync(traceFile, 'utf8')) : [];
  return { ...result, cases, events };
}

async function browser(t, api, intercept) {
  const traffic = [];
  const proxy = http.createServer(async (request, reply) => {
    try {
      const chunks = [];
      for await (const chunk of request) chunks.push(chunk);
      const body = Buffer.concat(chunks).toString();
      const event = { method: request.method, path: request.url, body };
      try { event.json = JSON.parse(body); } catch { /* GET has no body. */ }
      event.isCreation = event.method === 'GET' && event.path === paths.start;
      event.isFire = event.method === 'POST' && event.path === paths.fire;
      if (event.isFire) {
        event.square = [event.json?.row, event.json?.col];
        event.game = event.json?.game;
      }
      traffic.push(event);
      const forward = async () => {
        const upstream = await fetch(api.base + request.url, {
          method: request.method,
          headers: request.headers['content-type'] ?
            { 'content-type': request.headers['content-type'] } : undefined,
          body: chunks.length ? body : undefined,
          signal: AbortSignal.timeout(3000),
        });
        return response(upstream);
      };
      const outcome = await intercept?.(event, forward) ?? await forward();
      event.response = outcome;
      if (outcome.drop) {
        reply.destroy();
        return;
      }
      const headers = {};
      for (const key of ['content-type', 'cache-control', 'location']) {
        const value = outcome.headers?.get(key);
        if (value) headers[key] = value;
      }
      const rendered = outcome.body ?? JSON.stringify(outcome.json);
      if (!outcome.body && outcome.json) headers['content-type'] = 'application/json';
      reply.writeHead(outcome.status ?? 200, headers);
      reply.end(rendered);
    } catch (error) {
      reply.writeHead(502);
      reply.end(String(error));
    }
  });
  const port = await listen(proxy);
  t.after(async () => {
    const closed = new Promise(resolve => proxy.close(resolve));
    proxy.closeAllConnections();
    await closed;
  });
  const directory = tempDirectory(t);
  const binary = path.join(directory, 'browser');
  const compilation = childProcess(t, 'clang', [
    '-fobjc-arc', '-framework', 'AppKit', '-framework', 'WebKit',
    path.join(__dirname, 'webkit.m'), '-o', binary,
  ]);
  const compiled = await compilation.finished;
  assert.equal(compiled.code, 0, 'The WebKit browser driver must compile. ' + compiled.stderr);

  const processControl = childProcess(t, binary, [], { stdio: ['pipe', 'pipe', 'pipe'] });
  const lines = readline.createInterface({ input: processControl.child.stdout });
  const pending = new Map();
  let next = 0;
  lines.on('line', line => {
    const reply = JSON.parse(line);
    const resolve = pending.get(reply.id);
    pending.delete(reply.id);
    resolve?.(reply);
  });
  async function send(command) {
    const id = ++next;
    const reply = await new Promise(resolve => {
      const timeout = setTimeout(() => {
        pending.delete(id);
        resolve({ error: 'The browser did not respond. ' + processControl.stderr() });
      }, 4000);
      pending.set(id, message => {
        clearTimeout(timeout);
        resolve(message);
      });
      processControl.child.stdin.write(JSON.stringify({ id, ...command }) + '\n');
    });
    assert.ok(!reply.error, reply.error);
    return reply.value;
  }
  const view = script => send({ script });
  return {
    traffic,
    fires: () => traffic.filter(event => event.isFire),
    creations: () => traffic.filter(event => event.isCreation),
    open: () => send({ url: `http://${host}:${port}${paths.page}` }),
    view,
    async inspect() {
      return JSON.parse(await view(pageInspection));
    },
    async click(index) {
      await view(`(() => { const cell = (${findTargets})(); cell[${index}]?.click(); return true; })()`);
    },
  };
}

const findTargets = `function () {
  const visible = element => {
    const bounds = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return bounds.width > 0 && bounds.height > 0 && style.visibility === 'visible';
  };
  const selectors = [
    'button, [role="button"], input[type="button"]',
    '[role="gridcell"], td',
    '[data-row][data-col], [data-row][data-column]',
    'canvas',
  ];
  const groups = selectors.map(selector => [...document.querySelectorAll(selector)].filter(visible));
  let targets = groups.find(group => group.length >= 90) ?? groups.find(group => group.length) ?? [];
  if (targets.length > 100) {
    for (const parent of new Set(targets.map(element => element.parentElement))) {
      const siblings = targets.filter(element => parent.contains(element));
      if (siblings.length === 100) return order(siblings);
    }
  }
  return order(targets);
  function order(elements) {
    return elements.sort((left, right) => {
      const a = left.getBoundingClientRect();
      const b = right.getBoundingClientRect();
      return Math.abs(a.top - b.top) > 3 ? a.top - b.top : a.left - b.left;
    });
  }
}`;

const pageInspection = `JSON.stringify((() => {
  const targets = (${findTargets})();
  return {
    title: document.title,
    text: document.body?.innerText ?? '',
    targets: targets.map(element => {
      const bounds = element.getBoundingClientRect();
      const css = getComputedStyle(element);
      return {
        x: bounds.x, y: bounds.y,
        text: element.innerText ?? element.value ?? '',
        label: element.getAttribute('aria-label') ?? '',
        tooltip: element.title ?? '',
        disabled: element.matches(':disabled,[aria-disabled="true"]'),
        style: [css.backgroundColor, css.backgroundImage, css.color, css.borderColor,
          getComputedStyle(element, '::before').content, getComputedStyle(element, '::after').content],
      };
    }),
  };
})())`;

module.exports = {
  server, browser, eventually, isShot, unknownId, coordinates, boardSquares, runRuleTests,
  preferredPort, defaultPort, matchesGameId, testDirectory, rows, columns,
};
