'use strict';

const assert = require('node:assert/strict');
const { execFileSync, spawn } = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const net = require('node:net');
const os = require('node:os');
const path = require('node:path');
const { setTimeout: delay } = require('node:timers/promises');

const ROOT = path.resolve(__dirname, '..');
const CONTROL = path.join(__dirname, 'child-controls.cjs');
const REPORTER = path.join(__dirname, 'suite-reporter.cjs');
const PLAN_REVISION = 'ada051d8b4eca7b4b67a5b904f50fc7dd5612ff6';
const LOCAL_1_4_0 = '72d982867f943160fbde9456c9f523c5001dd7f3';
const ENV = {
  npm_config_update_notifier: 'false',
  npm_config_offline: 'true',
  npm_config_logs_max: '0',
};
const HOUR_SETTINGS = {
  urgent: 'DUE_HOURS_URGENT',
  high: 'DUE_HOURS_HIGH',
  normal: 'DUE_HOURS_NORMAL',
  low: 'DUE_HOURS_LOW',
};
const CREATION = '2025-09-01T08:15:00.000Z';
const DEFAULT_HOURS = { urgent: 4, high: 24, normal: 72, low: 168 };
const STATUSES = ['open', 'in_progress', 'resolved', 'closed'];

function envFor(overrides) {
  const env = { ...process.env, ...ENV };
  for (const name of [
    'PORT', 'DATA_FILE', 'NOTIFY_FILE', 'WORKER_INTERVAL_MS', 'MAX_BODY_BYTES', 'LOG_REQUESTS',
    'DUE_TIMES', ...Object.values(HOUR_SETTINGS), 'NODE_OPTIONS', 'NODE_TEST_CONTEXT', 'RATCHET_CHILD_CONTROL',
  ]) delete env[name];
  for (const [name, value] of Object.entries(overrides)) {
    if (value !== undefined) env[name] = String(value);
  }
  return env;
}

function run(command, args, options = {}) {
  return execFileSync(command, args, {
    cwd: options.cwd ?? ROOT,
    env: envFor(options.env ?? {}),
    timeout: 12000,
    encoding: 'utf8',
    maxBuffer: 4 * 1024 * 1024,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}

function signal(pid, value) {
  if (!pid) return;
  try {
    process.kill(pid, value);
  } catch (error) {
    if (error.code !== 'ESRCH') throw error;
  }
}

async function until(tryRead, message, options = {}) {
  const end = performance.now() + (options.timeout ?? 5000);
  do {
    const result = await tryRead();
    if (result) return result;
    await delay(10);
  } while (performance.now() < end);
  assert.fail(typeof message === 'function' ? message() : message);
}

function httpClient(port) {
  const agent = new http.Agent({ keepAlive: true });
  function call(method, route, body, actor) {
    const payload = body === undefined ? undefined : JSON.stringify(body);
    const headers = {};
    if (payload !== undefined) {
      headers['content-type'] = 'application/json';
      headers['content-length'] = Buffer.byteLength(payload);
    }
    if (actor !== undefined) headers['x-actor'] = actor;
    return new Promise((resolve, reject) => {
      const request = http.request({
        host: '127.0.0.1', port, method, path: route, headers, agent,
        signal: AbortSignal.timeout(2500),
      }, (response) => {
        let text = '';
        response.setEncoding('utf8');
        response.on('data', (chunk) => { text += chunk; });
        response.on('error', reject);
        response.on('end', () => {
          try {
            resolve({ status: response.statusCode, body: JSON.parse(text) });
          } catch (error) {
            reject(new Error(`${method} ${route} returned invalid JSON: ${text}`, { cause: error }));
          }
        });
      });
      request.on('error', reject);
      request.end(payload);
    });
  }

  const ticket = (id) => `/tickets/${encodeURIComponent(id)}`;
  return {
    close: () => agent.destroy(),
    health: () => call('GET', '/health'),
    create: (input, actor) => call('POST', '/tickets', input, actor),
    get: (id) => call('GET', ticket(id)),
    patch: (id, input, actor) => call('PATCH', ticket(id), input, actor),
    transition: (id, input, actor) => call('POST', `${ticket(id)}/transition`, input, actor),
    audit: (id) => call('GET', `${ticket(id)}/audit`),
    outbox: () => call('GET', '/admin/outbox'),
    list: (query = {}) => {
      const params = new URLSearchParams(query).toString();
      return call('GET', params ? `/tickets?${params}` : '/tickets');
    },
    overdue: (filters = {}) => call('GET', `/tickets?${new URLSearchParams({ overdue: 'true', ...filters })}`),
  };
}

function writeJson(file, document) {
  fs.writeFileSync(file, `${JSON.stringify(document, null, 2)}\n`);
}

function readText(file) {
  return fs.readFileSync(file, 'utf8');
}

function readData(file) {
  return JSON.parse(readText(file));
}

function scope(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'due-acceptance-'));
  const children = new Set();
  let serial = 0;
  let original;
  let clean;

  function file(name = 'tickets.json') {
    return path.join(dir, `${++serial}-${name}`);
  }

  t.after(async () => {
    try {
      await Promise.all([...children].map((child) => child.stop('SIGKILL')));
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  function oldRelease() {
    if (original) return original;
    const probe = (revision) => {
      try {
        return JSON.parse(run('git', ['show', `${revision}:package.json`])).version;
      } catch {
        return null;
      }
    };
    const revision = [PLAN_REVISION, LOCAL_1_4_0].find((candidate) => probe(candidate) === '1.4.0');
    assert.ok(revision, 'the original 1.4.0 release is available in local Git history');
    const archive = file('original.tar');
    original = fs.mkdtempSync(path.join(dir, 'original-'));
    run('git', ['archive', '--format=tar', `--output=${archive}`, revision]);
    run('tar', ['-xf', archive, '-C', original]);
    return original;
  }

  function cleanCheckout() {
    if (clean) return clean;
    clean = fs.mkdtempSync(path.join(dir, 'checkout-'));
    fs.cpSync(ROOT, clean, {
      recursive: true,
      filter(source) {
        if (source === ROOT) return true;
        const relative = path.relative(ROOT, source).split(path.sep);
        return relative[0] !== '.git' && relative[0] !== 'acceptance' && !relative.includes('node_modules');
      },
    });
    return clean;
  }

  function launch(options = {}) {
    const {
      dataFile, notifyFile, enabled, flag = enabled ? 'on' : undefined,
      hours = {}, workerInterval = 0, port = '0', remapPort = false,
      now = CREATION, tz = 'UTC', cwd = ROOT, fault, deferFault = false,
    } = options;
    const clockFile = file('clock');
    const faultFile = fault ? file('fault') : undefined;
    function setTime(iso) {
      const instant = Date.parse(iso);
      assert.ok(Number.isFinite(instant), `valid test clock instant: ${iso}`);
      fs.writeFileSync(`${clockFile}.new`, String(instant));
      fs.renameSync(`${clockFile}.new`, clockFile);
    }
    setTime(now);
    const armFault = () => { if (faultFile) fs.writeFileSync(faultFile, 'armed'); };
    if (!deferFault) armFault();

    const child = spawn('npm', ['start'], {
      cwd,
      env: envFor({
        PORT: port === null ? undefined : port, DATA_FILE: dataFile, NOTIFY_FILE: notifyFile,
        DUE_TIMES: flag, WORKER_INTERVAL_MS: workerInterval, TZ: tz,
        ...Object.fromEntries(Object.entries(hours).map(([priority, value]) => [HOUR_SETTINGS[priority], value])),
        NODE_OPTIONS: `--require "${CONTROL}"`,
        RATCHET_CHILD_CONTROL: JSON.stringify({
          clockFile, remapPort, fault: fault ? { dataFile, mode: fault, marker: faultFile } : undefined,
        }),
      }),
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let logs = '';
    let ended;
    let api;
    let stopped;
    const clients = new Set();
    const closed = new Promise((resolve) => {
      child.once('error', (error) => { ended = { error }; resolve(ended); });
      child.once('close', (code, terminationSignal) => { ended = { code, signal: terminationSignal }; resolve(ended); });
    });
    for (const output of [child.stdout, child.stderr]) {
      output.setEncoding('utf8');
      output.on('data', (chunk) => { logs += chunk; });
    }
    const event = (name) => logs.match(new RegExp(`^RATCHET ${name} (.+)$`, 'm'))?.[1];
    const boundPort = () => Number(logs.match(/tickets listening on (\d+)/)?.[1]) || undefined;
    const serverPid = () => Number(event('pid')) || undefined;
    const control = {
      setTime,
      event,
      logs: () => logs,
      armFault,
      disarmFault: () => { if (faultFile) fs.rmSync(faultFile, { force: true }); },
      get port() { return boundPort(); },
      get pid() { return serverPid(); },
      async outcome() {
        return until(() => {
          if (ended) return { exit: ended };
          const portNumber = boundPort();
          if (portNumber) return { port: portNumber };
          return undefined;
        }, () => `npm start neither answered on a port nor exited\n${logs}`);
      },
      async ready() {
        const result = await control.outcome();
        assert.ok(result.port, `npm start should serve on its configured port\n${logs}`);
        if (!api) {
          api = httpClient(result.port);
          clients.add(api);
        }
        return api;
      },
      async meetSaveBoundary() {
        return until(() => {
          const phase = event('save-boundary');
          if (phase) return phase;
          assert.ok(!boundPort(), 'service became ready without attempting the preparation save');
          assert.ok(!ended, `service exited without reaching the preparation save\n${logs}`);
          return undefined;
        }, () => `preparation did not reach the active-file write boundary\n${logs}`);
      },
      async stop(value = 'SIGTERM') {
        if (stopped) return stopped;
        stopped = (async () => {
          try {
            for (const client of clients) client.close();
            if (!ended && !serverPid()) {
              await until(() => serverPid() || ended, 'npm did not start its server process', { timeout: 800 })
                .catch(() => undefined);
            }
            if (!ended) signal(serverPid() ?? child.pid, value);
            try {
              return await until(() => ended, 'npm start did not shut down', { timeout: 1600 });
            } catch {
              signal(serverPid(), 'SIGKILL');
              signal(child.pid, 'SIGKILL');
              return await closed;
            }
          } finally {
            children.delete(control);
          }
        })();
        return stopped;
      },
    };
    children.add(control);
    return control;
  }

  async function serving(options, fn) {
    const control = launch(options);
    try {
      return await fn(await control.ready(), control);
    } finally {
      await control.stop();
    }
  }

  return {
    file, launch, serving, oldRelease, cleanCheckout,
    seed(document, name) {
      const target = file(name);
      writeJson(target, document);
      return target;
    },
    copy(source) {
      const target = file();
      fs.copyFileSync(source, target);
      return target;
    },
  };
}

function suite(cwd, { report = false } = {}) {
  const env = report ? { NODE_OPTIONS: `--test-reporter="${REPORTER}"` } : {};
  const output = run('npm', ['test'], { cwd, env });
  if (!report) return output;
  return output.split('\n')
    .filter((line) => line.startsWith('RATCHET_TEST '))
    .map((line) => JSON.parse(line.slice('RATCHET_TEST '.length)));
}

function assertOriginalTests(original, current, cases) {
  for (const name of new Set(cases.map(({ file }) => file))) {
    assert.ok(fs.existsSync(path.join(current, name)), `${name} is still present`);
    const expected = readText(path.join(original, name)).trimEnd().split('\n');
    let matched = 0;
    for (const line of readText(path.join(current, name)).trimEnd().split('\n')) {
      if (line === expected[matched]) matched += 1;
    }
    assert.equal(matched, expected.length, `${name} keeps the original test source`);
  }
}

function passedTests(events, cwd) {
  return events
    .filter((event) => event.type === 'test:pass' && event.kind === 'test' && event.line && !event.skipped && event.file)
    .map((event) => ({ file: path.relative(cwd, event.file), name: event.name }))
    .filter(({ file }) => file.startsWith(`test${path.sep}`));
}

function cli(file, command, args = [], { viaEnv = false } = {}) {
  return run(process.execPath, ['bin/tickets.js', ...(viaEnv ? [] : ['--data', file]), command, ...args], {
    env: viaEnv ? { DATA_FILE: file } : {},
  });
}

function weekly(file) {
  return JSON.parse(run(process.execPath, ['scripts/weekly-report.js', '--data', file, '--json']));
}

async function freePort() {
  const socket = net.createServer();
  await new Promise((resolve, reject) => {
    socket.once('error', reject);
    socket.listen(0, resolve);
  });
  const { port } = socket.address();
  await new Promise((resolve, reject) => socket.close((error) => error ? reject(error) : resolve()));
  return port;
}

function newTicket(fields = {}) {
  return { title: 'VPN disconnects on the fourth floor', requester: 'maria@example.com', ...fields };
}

function ticketId(number) {
  return `T-${String(number).padStart(4, '0')}`;
}

function ticketRecord(number, fields = {}) {
  const priority = fields.priority ?? 'high';
  const created = fields.created ?? (fields.due ? plusHours(fields.due, -DEFAULT_HOURS[priority]) : CREATION);
  return {
    id: ticketId(number),
    ...newTicket({ title: `Support request ${number}`, requester: `requester-${number}@example.com` }),
    priority, status: 'open', created, updated: fields.due ? created : '2025-09-01T09:45:00.000Z',
    ...fields,
  };
}

function dataDocument(tickets = [], { nextNumber, audit = [], events = [], nextEvent = 1 } = {}) {
  const lastTicketNumber = Math.max(0, ...tickets.map((ticket) => Number(ticket.id.slice(2))));
  return {
    version: 1, savedAt: CREATION, nextNumber: nextNumber ?? lastTicketNumber + 1, tickets, audit,
    outbox: { nextId: nextEvent, events },
  };
}

function legacyFixture() {
  const tickets = [
    ticketRecord(2),
    ticketRecord(7, { status: 'in_progress', priority: 'urgent', created: '2025-09-01T04:15:00-04:00' }),
    ticketRecord(14, { status: 'resolved', priority: 'normal', created: '2025-08-31T19:05:00.000Z' }),
    ticketRecord(28, { status: 'closed', priority: 'low', created: '2025-08-27T10:20:00.000Z' }),
  ];
  const [first, second] = tickets;
  const audit = [
    {
      seq: 1, ticket: first.id, action: 'ticket.created', actor: 'intake', at: first.created,
      changes: {
        title: { from: null, to: first.title },
        priority: { from: null, to: first.priority },
        requester: { from: null, to: first.requester },
        status: { from: null, to: first.status },
      },
    },
    {
      seq: 2, ticket: second.id, action: 'ticket.transitioned', actor: 'dana', at: second.updated,
      changes: { status: { from: 'open', to: 'in_progress' } },
    },
    {
      seq: 3, ticket: first.id, action: 'ticket.updated', actor: 'queue-lead', at: first.updated,
      changes: { priority: { from: 'normal', to: 'high' } },
    },
  ];
  const events = [{
    id: 3, key: `ticket.created:${first.id}`, type: 'ticket.created', to: first.requester, ticket: first.id,
    data: { title: first.title }, status: 'pending', attempts: 0, created: first.created,
    nextAttemptAt: '2025-09-03T08:15:00.000Z', lastError: null, sentAt: null,
  }];
  return dataDocument(tickets, { nextNumber: 43, audit, events, nextEvent: 8 });
}

function plusHours(timestamp, hours) {
  return new Date(Date.parse(timestamp) + hours * 3600000).toISOString();
}

function preparedFixture(document = legacyFixture(), schedule = DEFAULT_HOURS) {
  return {
    ...document,
    tickets: document.tickets.map((ticket) => ({ ...ticket, due: plusHours(ticket.created, schedule[ticket.priority]) })),
  };
}

module.exports = {
  scope, until, readText, readData, freePort, suite, assertOriginalTests, passedTests, cli, weekly,
  CREATION, DEFAULT_HOURS, STATUSES, newTicket, ticketId, ticketRecord, dataDocument, legacyFixture, preparedFixture,
  plusHours, hourSetting: (priority) => HOUR_SETTINGS[priority],
};
