'use strict';

const fs = require('node:fs');

// This module is also preloaded by the npm start process to control external time and, when requested, observe binds.
if (process.env.ACCEPTANCE_PROCESS_FILE) {
  if (process.env.npm_lifecycle_event === 'start') installRuntime();
  return;
}

function installRuntime() {
  fs.appendFileSync(process.env.ACCEPTANCE_PROCESS_FILE, `${process.pid}\n`);
  const bindFile = process.env.ACCEPTANCE_BIND_FILE;
  if (bindFile) {
    const { Server } = require('node:net');
    const listen = Server.prototype.listen;
    Server.prototype.listen = function (...args) {
      const requested = args[0];
      const port = requested !== null && typeof requested === 'object' ? requested.port : requested;
      if (port !== undefined && /^\d+$/.test(String(port))) {
        fs.appendFileSync(bindFile, `${port}\n`);
        if (process.env.ACCEPTANCE_REDIRECT_BIND === '1') {
          args[0] = typeof requested === 'object' ? { ...requested, port: 0 } : 0;
        }
      }
      return listen.apply(this, args);
    };
  }
  const file = process.env.ACCEPTANCE_CLOCK_FILE;
  if (file && fs.existsSync(file)) {
    const NativeDate = Date;
    const step = Number(process.env.ACCEPTANCE_CLOCK_STEP ?? 0);
    let offset = 0;
    const now = () => {
      const value = NativeDate.parse(fs.readFileSync(file, 'utf8')) + offset;
      offset += step;
      return value;
    };
    global.Date = new Proxy(NativeDate, {
      apply: () => new NativeDate(now()).toString(),
      construct: (target, args, newTarget) => Reflect.construct(target, args.length ? args : [now()], newTarget),
      get: (target, field, receiver) => field === 'now' ? now : Reflect.get(target, field, receiver),
    });
  }
}

const assert = require('node:assert/strict');
const { spawn, spawnSync } = require('node:child_process');
const http = require('node:http');
const net = require('node:net');
const os = require('node:os');
const path = require('node:path');
const { test } = require('node:test');
const { setTimeout: pause } = require('node:timers/promises');

const root = path.join(__dirname, '..');
const commandDeadline = Date.now() + 45000;
const plannedRelease = 'ada051d';
const localBase = '72d9828';
const instant = '2025-09-01T08:15:00.000Z';
const hour = 3_600_000;
const priorities = ['urgent', 'high', 'normal', 'low'];
const statuses = ['open', 'in_progress', 'resolved', 'closed'];
const ticketFields = ['id', 'title', 'priority', 'requester', 'status', 'created', 'updated'];
const setting = {
  urgent: 'DUE_HOURS_URGENT', high: 'DUE_HOURS_HIGH', normal: 'DUE_HOURS_NORMAL', low: 'DUE_HOURS_LOW',
};
const appVariables = ['PORT', 'DATA_FILE', 'NOTIFY_FILE', 'WORKER_INTERVAL_MS', 'MAX_BODY_BYTES', 'LOG_REQUESTS',
  'DUE_TIMES', ...Object.values(setting)];

function git(args) {
  return spawnSync('git', args, { cwd: root, maxBuffer: 10 * 1024 * 1024, timeout: 4000 });
}

function fileBytes(file) {
  return fs.readFileSync(file, 'utf8');
}

function saved(file) {
  return JSON.parse(fileBytes(file));
}

function write(file, document) {
  fs.writeFileSync(file, `${JSON.stringify(document)}\n`);
}

function select(record, fields) {
  return Object.fromEntries(fields.map((field) => [field, record[field]]));
}

function id(number) {
  return `T-${String(number).padStart(4, '0')}`;
}

function ticket(number, overrides = {}) {
  return {
    id: id(number), title: `Printer incident ${number}`, priority: 'normal', requester: 'owner@example.test',
    status: 'open', created: instant, updated: '2025-09-01T09:15:00.000Z', ...overrides,
  };
}

function document(tickets = [], overrides = {}) {
  return {
    version: 1, savedAt: instant, nextNumber: 1 + Math.max(0, ...tickets.map((row) => Number(row.id.slice(2)))),
    tickets, audit: [], outbox: { nextId: 1, events: [] }, ...overrides,
  };
}

function signal(pid, name) {
  try {
    process.kill(pid, name);
  } catch (error) {
    if (error.code !== 'ESRCH') throw error;
  }
}

function descendants(parent) {
  const result = spawnSync('ps', ['-axo', 'pid=,ppid='], { encoding: 'utf8', timeout: 2000 });
  const pairs = (result.stdout || '').trim().split('\n').map((line) => line.trim().split(/\s+/).map(Number));
  const childrenOf = (pid) => pairs.filter(([, ppid]) => ppid === pid).flatMap(([child]) => [...childrenOf(child), child]);
  return childrenOf(parent);
}

function launch(command, args, options) {
  assert.ok(Date.now() < commandDeadline, 'acceptance command exceeded its time budget');
  const child = spawn(command, args, { ...options, stdio: ['ignore', 'pipe', 'pipe'] });
  const run = { pid: child.pid, stdout: '', stderr: '', exit: null };
  child.stdout.setEncoding('utf8').on('data', (chunk) => { run.stdout += chunk; });
  child.stderr.setEncoding('utf8').on('data', (chunk) => { run.stderr += chunk; });
  run.done = new Promise((resolve) => {
    child.on('error', (error) => { run.error = error; });
    child.on('close', (code, stoppedBy) => {
      run.exit = { code, signal: stoppedBy };
      resolve(run.exit);
    });
  });
  run.diagnostic = () => [run.error?.message, run.stdout, run.stderr].filter(Boolean).join('\n');
  run.kill = async () => {
    if (run.exit || !run.pid) return;
    for (const pid of [...descendants(run.pid), run.pid]) signal(pid, 'SIGKILL');
    await run.done;
  };
  return run;
}

async function until(get, message, timeout = 6000) {
  const end = Math.min(Date.now() + timeout, commandDeadline);
  do {
    const result = get();
    if (result) return result;
    await pause(15);
  } while (Date.now() < end);
  assert.fail(typeof message === 'function' ? message() : message);
}

function api(port) {
  function send(hostname, method, target, body, actor) {
    const headers = { accept: 'application/json' };
    const payload = body === undefined ? undefined : JSON.stringify(body);
    if (payload !== undefined) {
      headers['content-type'] = 'application/json';
      headers['content-length'] = Buffer.byteLength(payload);
    }
    if (actor !== undefined) headers['x-actor'] = actor;
    return new Promise((resolve, reject) => {
      const req = http.request({ hostname, port, path: target, method, headers, agent: false,
        signal: AbortSignal.timeout(Math.max(1, Math.min(2500, commandDeadline - Date.now()))) }, (res) => {
        let text = '';
        res.setEncoding('utf8');
        res.on('data', (chunk) => { text += chunk; });
        res.on('error', reject);
        res.on('end', () => resolve({ status: res.statusCode, text }));
      });
      req.on('error', reject);
      req.end(payload);
    });
  }

  async function request(method, target, body, actor) {
    let response = await send('127.0.0.1', method, target, body, actor);
    if (response.status === 404 && response.text.trim() === 'not found') {
      // A plain-text loopback 404 lacks the service's JSON error envelope. Try the other local address.
      try {
        response = await send('::1', method, target, body, actor);
      } catch (error) {
        if (error.code !== 'ECONNREFUSED' && error.code !== 'EADDRNOTAVAIL') throw error;
        await pause(20);
        response = await send('127.0.0.1', method, target, body, actor);
      }
    }
    const { status, text } = response;
    try {
      return { status, body: text ? JSON.parse(text) : null };
    } catch (error) {
      throw new Error(`${method} ${target} on port ${port} returned non-JSON (HTTP ${status})`, { cause: error });
    }
  }

  const item = (ticketId) => `/tickets/${encodeURIComponent(ticketId)}`;
  return {
    health: () => request('GET', '/health'),
    list: (params = {}) => request('GET', `/tickets?${new URLSearchParams(params)}`),
    get: (ticketId) => request('GET', item(ticketId)),
    create: ({ title = 'Printer offline', requester = 'owner@example.test', ...fields } = {}, actor) =>
      request('POST', '/tickets', { title, requester, ...fields }, actor),
    patch: (ticketId, body, actor) => request('PATCH', item(ticketId), body, actor),
    transition: (ticketId, to, actor) => request('POST', `${item(ticketId)}/transition`,
      typeof to === 'string' ? { to } : to, actor),
    audit: (ticketId) => request('GET', `${item(ticketId)}/audit`),
    outbox: () => request('GET', '/admin/outbox'),
  };
}

async function portAvailable(port) {
  const probe = net.createServer();
  return new Promise((resolve, reject) => {
    probe.once('error', (error) => {
      if (['EADDRINUSE', 'EACCES', 'EADDRNOTAVAIL'].includes(error.code)) resolve(false);
      else reject(error);
    });
    probe.listen(port, () => probe.close((error) => error ? reject(error) : resolve(true)));
  });
}

function bodyOf(response, status) {
  assert.equal(response.status, status, JSON.stringify(response.body));
  return response.body;
}

function invalid(response) {
  assert.equal(response.status, 400);
  assert.equal(response.body.error?.code, 'invalid');
}

function ids(page) {
  return page.items.map((row) => row.id);
}

function context(directory) {
  const children = [];
  let fileIndex = 0;
  let archive;
  const nextPath = (name) => path.join(directory, `${++fileIndex}-${name}`);

  function env(options = {}) {
    const result = { ...process.env, npm_config_cache: path.join(directory, 'npm-cache'),
      npm_config_update_notifier: 'false', npm_config_color: 'false' };
    for (const key of [...appVariables, 'NODE_OPTIONS', 'NODE_V8_COVERAGE', 'NODE_TEST_CONTEXT', 'npm_lifecycle_event']) delete result[key];
    const { data, flag, hours = {}, port = 0, worker = 0, notify, tz = 'UTC' } = options;
    Object.assign(result, { WORKER_INTERVAL_MS: String(worker), TZ: tz });
    if (port !== null) result.PORT = String(port);
    if (data !== undefined) result.DATA_FILE = data;
    if (flag !== undefined) result.DUE_TIMES = flag;
    if (notify !== undefined) result.NOTIFY_FILE = notify;
    for (const [priority, value] of Object.entries(hours)) result[setting[priority]] = String(value);
    return result;
  }

  function file(data) {
    const name = nextPath('tickets.json');
    if (data !== undefined) write(name, data);
    return name;
  }

  function legacy() {
    if (archive) return archive;
    const ref = git(['cat-file', '-e', `${plannedRelease}^{commit}`]).status === 0 ? plannedRelease : localBase;
    const tar = git(['archive', ref]);
    assert.equal(tar.status, 0, tar.stderr.toString());
    const source = nextPath('release-1.4.0');
    fs.mkdirSync(source);
    const unpack = spawnSync('tar', ['-xf', '-', '-C', source], { input: tar.stdout, timeout: 4000 });
    assert.equal(unpack.status, 0, unpack.stderr.toString());
    assert.equal(saved(path.join(source, 'package.json')).version, '1.4.0');
    archive = { ref, source };
    return archive;
  }

  async function start(options = {}) {
    const launchEnv = env(options);
    const clockFile = nextPath('clock');
    const processFile = nextPath('processes');
    const bindFile = nextPath('binds');
    if (options.at !== null) fs.writeFileSync(clockFile, options.at ?? instant);
    launchEnv.NODE_OPTIONS = `--require ${JSON.stringify(__filename)}`;
    launchEnv.ACCEPTANCE_CLOCK_FILE = clockFile;
    launchEnv.ACCEPTANCE_PROCESS_FILE = processFile;
    if (options.inspectBind) launchEnv.ACCEPTANCE_BIND_FILE = bindFile;
    if (options.redirectBind) launchEnv.ACCEPTANCE_REDIRECT_BIND = '1';
    if (options.clockStep !== undefined) launchEnv.ACCEPTANCE_CLOCK_STEP = String(options.clockStep);
    const cwd = options.old ? legacy().source : root;
    const run = options.fileBlocks === undefined
      ? launch('npm', ['start'], { cwd, env: launchEnv })
      : launch('sh', ['-c', 'ulimit -f "$1" && exec npm start', 'npm-start', String(options.fileBlocks)],
        { cwd, env: launchEnv });
    children.push(run);

    const service = {
      async stop() {
        if (!run.exit) {
          const pids = fs.existsSync(processFile) ? fileBytes(processFile).trim().split('\n').map(Number) : [];
          assert.ok(pids.length > 0, 'npm start did not register a service process');
          for (const pid of pids) signal(pid, 'SIGTERM');
          await until(() => run.exit, () => `npm start did not stop\n${run.diagnostic()}`, 3000);
          assert.equal(run.exit.code, 0, run.diagnostic());
        }
      },
      crash: () => run.kill(),
      binds: () => fs.existsSync(bindFile) ? fileBytes(bindFile).trim().split('\n').map(Number) : [],
      setTime(at) {
        fs.writeFileSync(clockFile, at);
      },
      run,
    };

    const outcome = await until(() => {
      const listening = /\btickets listening on (\d+)\b/.exec(`${run.stdout}\n${run.stderr}`);
      return listening ? { port: Number(listening[1]) } : run.exit;
    }, () => `npm start did not report readiness or exit\n${run.diagnostic()}`);
    if (outcome.port !== undefined) {
      service.port = outcome.port;
      service.api = api(outcome.port);
    }
    return service;
  }

  async function serve(options) {
    const service = await start(options);
    assert.ok(service.api, `expected the service to listen\n${service.run.diagnostic()}`);
    return service;
  }

  async function command(executable, args, { cwd = root, env: commandEnv = env(), timeout = 15000 } = {}) {
    const run = launch(executable, args, { cwd, env: commandEnv });
    children.push(run);
    await until(() => run.exit, () => `${executable} did not finish\n${run.diagnostic()}`, timeout);
    return run;
  }

  async function cli(data, action, { via = 'env', flag, status, priority, raw = false } = {}) {
    const args = ['bin/tickets.js'];
    if (via === 'argument') args.push('--data', data);
    args.push(...action);
    if (status !== undefined) args.push('--status', status);
    if (priority !== undefined) args.push('--priority', priority);
    if (raw) args.push('--raw');
    const run = await command(process.execPath, args, { env: env({ data: via === 'env' ? data : undefined, flag }) });
    assert.equal(run.exit.code, 0, run.diagnostic());
    return run.stdout;
  }

  async function report(data, json = false) {
    const run = await command('npm', ['run', 'report:weekly', ...(json ? ['--', '--json'] : [])], { env: env({ data }) });
    assert.equal(run.exit.code, 0, run.diagnostic());
    return json ? JSON.parse(run.stdout.trim().split('\n').at(-1)) : run.stdout;
  }

  async function suite(old = false) {
    const cwd = old ? legacy().source : root;
    const suiteEnv = env();
    const reporter = path.join(__dirname, 'reporter.mjs');
    suiteEnv.NODE_OPTIONS = `--test-reporter ${JSON.stringify(reporter)}`;
    const run = await command('npm', ['test'], { cwd, env: suiteEnv, timeout: 20000 });
    const cases = run.stdout.split('\n').filter((line) => line.startsWith('ACCEPTANCE_CASE ')).map((line) => {
      const entry = JSON.parse(line.slice('ACCEPTANCE_CASE '.length));
      return { ...entry, file: entry.file ? path.relative(cwd, entry.file) : '' };
    });
    return { run, cases };
  }

  function originalTestPaths() {
    const { ref } = legacy();
    const listed = git(['ls-tree', '-r', '--name-only', ref, '--', 'test']);
    assert.equal(listed.status, 0, listed.stderr.toString());
    return listed.stdout.toString().trim().split('\n');
  }

  function originalTests() {
    const files = originalTestPaths();
    const { ref } = legacy();
    const unchanged = git(['diff', '--exit-code', ref, '--', ...files]);
    assert.equal(unchanged.status, 0, `original test files changed\n${unchanged.stdout}\n${unchanged.stderr}`);
  }

  function newTestSources() {
    const originals = new Set(originalTestPaths());
    const testDirectory = path.join(root, 'test');
    return fs.readdirSync(testDirectory, { recursive: true }).filter((file) => /\.[cm]?js$/.test(file)
      && !originals.has(path.join('test', file)) && fs.statSync(path.join(testDirectory, file)).isFile())
      .map((file) => fileBytes(path.join(testDirectory, file)));
  }

  // Generate a v1 file with actual 1.4.0 HTTP writes and all three historical notification states.
  async function legacyFixture() {
    const data = file();
    const old = await serve({ data, old: true });
    for (let index = 0; index < statuses.length; index += 1) {
      const priority = ['high', 'urgent', 'normal', 'low'][index];
      old.setTime(instant);
      const row = bodyOf(await old.api.create({ title: `Legacy incident ${index + 1}`,
        priority: index === 0 ? 'normal' : priority }, 'requester'), 201);
      old.setTime('2025-09-01T11:45:00.000Z');
      if (index === 0) {
        bodyOf(await old.api.patch(row.id, { title: 'Legacy incident updated', priority }, 'agent'), 200);
      }
      for (const status of statuses.slice(1, index + 1)) {
        bodyOf(await old.api.transition(row.id, status, 'agent'), 200);
      }
    }
    await old.stop();
    const source = saved(data);
    // Operators can retain old records and counters after archived entries have been removed.
    source.nextNumber = 42;
    source.outbox.nextId = 23;
    Object.assign(source.outbox.events[1], { status: 'sent', attempts: 1, nextAttemptAt: null,
      sentAt: '2025-09-01T12:00:00.000Z' });
    Object.assign(source.outbox.events[2], { status: 'dead', attempts: 5, nextAttemptAt: null,
      lastError: 'mail relay unavailable' });
    write(data, source);
    return { data, source };
  }

  function recoverableFile(data) {
    const parent = nextPath('production');
    fs.mkdirSync(parent);
    const target = path.join(parent, 'tickets.json');
    write(target, data);
    return {
      data: target,
      async blockWrites(fn) {
        fs.chmodSync(target, 0o444);
        fs.chmodSync(parent, 0o555);
        try {
          assert.throws(() => fs.accessSync(target, fs.constants.W_OK), { code: 'EACCES' });
          assert.throws(() => fs.accessSync(parent, fs.constants.W_OK), { code: 'EACCES' });
          return await fn();
        } finally {
          fs.chmodSync(parent, 0o755);
          fs.chmodSync(target, 0o644);
        }
      },
    };
  }

  return { file, nextPath, start, serve, cli, report, suite, originalTests, newTestSources, legacyFixture, recoverableFile,
    packageOf: () => saved(path.join(root, 'package.json')),
    async cleanup() { await Promise.all(children.map((child) => child.kill())); } };
}

function check(name, fn) {
  test(name, { timeout: 50000 }, async (t) => {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'due-acceptance-'));
    const harness = context(directory);
    t.after(async () => {
      await harness.cleanup();
      fs.rmSync(directory, { recursive: true, force: true });
    });
    await fn(harness, t);
  });
}

module.exports = {
  check, portAvailable, until, fileBytes, saved, write, select, id, ticket, document, bodyOf, invalid, ids,
  setting, instant, hour, priorities, statuses, ticketFields,
};
