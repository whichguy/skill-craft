'use strict';

const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { execFileSync, spawn } = require('node:child_process');
const { once } = require('node:events');
const fs = require('node:fs/promises');
const net = require('node:net');
const path = require('node:path');
const { createInterface } = require('node:readline');
const { setTimeout: delay } = require('node:timers/promises');

const root = path.resolve(__dirname, '..');
const entry = 'server.js';

// The runtime coverage probe flushes Node's own counters before a test service exits.
if (process.env.RATCHET_ACCEPTANCE_COVERAGE === '1') {
  process.once('SIGTERM', () => {
    require('node:v8').takeCoverage();
    process.exit(0);
  });
}
const initialFiles = {
  'provider/standin.js': '1e899517fc4f678873ce528abfc5a9380f960789',
  'records/people.json': '3e15da27216e9e471c0ca7efa60ae487ef93015c',
  'records/records.json': 'c0262ffbb0014c5a6bb2e35319d2f5257c5a74e8',
};
const fixtureNames = ['records/people.json', 'records/records.json'];
const shortToken = 'sk-local-aB34eF78iJ12';
const longToken = 'sk-local-mN56qR90uV34wX78';
const refused = ['sk-local-12345678901', 'sk-local-12345678901é', ''];

const role = (kind, name, within) => ({ kind, name, within });
const region = name => role('region', name);
const nav = name => role('navigation', name);
const button = (name, within) => role('button', name, within);
const textbox = (name, within) => role('textbox', name, within);
const article = (name, within) => role('article', name, within);

async function eventually(read, predicate, description, ms = 7300) {
  const deadline = Date.now() + ms;
  let value;
  do {
    value = await read();
    if (predicate(value)) return value;
    await delay(55);
  } while (Date.now() < deadline);
  assert.fail(description + ' (last observation: ' + JSON.stringify(value)?.slice(0, 280) + ')');
}

function processHandle(command, args, options = {}) {
  const child = spawn(command, args, { ...options, stdio: ['pipe', 'pipe', 'pipe'] });
  const log = { stdout: '', stderr: '', done: false };
  for (const key of ['stdout', 'stderr']) {
    child[key].setEncoding('utf8');
    child[key].on('data', part => { log[key] = (log[key] + part).slice(-131072); });
  }
  child.stdin.on('error', () => {});
  const done = new Promise(resolve => {
    child.once('error', error => { log.done = true; resolve({ error }); });
    child.once('close', (code, signal) => { log.done = true; resolve({ code, signal }); });
  });
  async function stop(signal = 'SIGTERM') {
    if (log.done) return done;
    child.kill(signal);
    const timer = setTimeout(() => child.kill('SIGKILL'), 1000);
    try { return await done; } finally { clearTimeout(timer); }
  }
  return { child, log, done, stop };
}

function killTree(child) {
  if (!child.pid || child.exitCode !== null || child.signalCode !== null) return;
  child.kill('SIGSTOP');
  try {
    const relationships = execFileSync('ps', ['-axo', 'pid=,ppid='], { encoding: 'utf8', timeout: 1000 });
    const pairs = relationships.trim().split('\n').map(row => row.trim().split(/\s+/).map(Number));
    function children(parent) {
      for (const [pid, ppid] of pairs) {
        if (ppid !== parent) continue;
        children(pid);
        try { process.kill(pid, 'SIGKILL'); } catch (error) { if (error.code !== 'ESRCH') throw error; }
      }
    }
    children(child.pid);
  } finally {
    child.kill('SIGKILL');
  }
}

async function run(command, args, options, ms = 10000, signal) {
  const proc = processHandle(command, args, options);
  const abort = () => killTree(proc.child);
  signal?.addEventListener('abort', abort, { once: true });
  const timer = setTimeout(abort, ms);
  try {
    return { ...await proc.done, ...proc.log };
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', abort);
  }
}

async function portAvailable(port = 0) {
  const socket = net.createServer();
  socket.listen({ port });
  await once(socket, 'listening');
  const actual = socket.address().port;
  await new Promise(resolve => socket.close(resolve));
  return actual;
}

async function bytes(file, folder = root) {
  return fs.readFile(path.join(folder, file));
}

async function fixtureBytes(folder = root) {
  return Promise.all(fixtureNames.map(file => bytes(file, folder)));
}

async function original(file, folder = root) {
  const content = await bytes(file, folder);
  const digest = createHash('sha1').update('blob ' + content.length + '\0').update(content).digest('hex');
  assert.equal(digest, initialFiles[file], file + ' still has the supplied bytes');
}

async function fixtures() {
  const [people, records] = (await fixtureBytes()).map(value => JSON.parse(value));
  return { people, records };
}

function provider() {
  // This documented dependency is the product interface shipped in the starting checkout.
  return require('../provider/standin.js');
}

async function offline(prompt, {
  person = 'Maya', bot = 'Assistant', instructions = '', history = [], memory = [], records, attempt = 1,
} = {}) {
  const seed = await fixtures();
  const reader = seed.people.find(item => item.name === person);
  return provider().respond({
    token: shortToken,
    person: reader,
    bot: { name: bot, instructions },
    memory,
    messages: [...history, { from: 'person', text: prompt }],
    records: records ?? seed.records.filter(row => row.readers.includes(reader.id)),
    attempt,
  });
}

async function stepsOf(prompt) {
  const { steps } = (await offline(prompt)).task;
  return steps.map(step => 'Done: ' + step);
}

async function delivered() {
  return fs.stat(path.join(root, entry)).then(info => info.isFile(), error => {
    if (error.code === 'ENOENT') return false;
    throw error;
  });
}

const settingNames = ['PORT', 'DATA_DIR', 'PROVIDER_TOKEN', 'STANDIN_SLOW_MS', 'STANDIN_STEP_MS'];

function environment(settings, defaults, data, port) {
  const env = { ...process.env };
  for (const name of settingNames) delete env[name];
  delete env.NODE_OPTIONS;
  delete env.NODE_V8_COVERAGE;
  delete env.RATCHET_ACCEPTANCE_COVERAGE;
  if (!defaults.data) env.DATA_DIR = data;
  if (!defaults.port) env.PORT = String(port);
  if (settings.token !== null) env.PROVIDER_TOKEN = settings.token ?? shortToken;
  if (settings.slow !== undefined) env.STANDIN_SLOW_MS = String(settings.slow);
  if (settings.step !== undefined) env.STANDIN_STEP_MS = String(settings.step);
  // The provider is local. Keep proxy-aware clients on the loopback when checking offline replies.
  if (settings.offline) {
    for (const name of ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']) {
      env[name] = 'http://127.0.0.1:1';
    }
    env.NO_PROXY = env.no_proxy = 'localhost,127.0.0.1';
  }
  return env;
}

async function deliveryCopy(dir) {
  const delivery = await fs.mkdtemp(path.join(dir, 'checkout-'));
  await fs.cp(root, delivery, {
    recursive: true,
    filter(source) {
      const parts = path.relative(root, source).split(path.sep);
      return !parts.includes('node_modules') && !['.git', 'data', 'acceptance', 'ratchet'].includes(parts[0]);
    },
  });
  return delivery;
}

async function tree(dir) {
  const files = new Map();
  async function collect(folder) {
    for (const file of await fs.readdir(folder, { withFileTypes: true })) {
      const target = path.join(folder, file.name);
      if (file.isDirectory()) await collect(target);
      else if (file.isFile()) files.set(path.relative(dir, target), createHash('sha256').update(await fs.readFile(target)).digest('hex'));
    }
  }
  await collect(dir);
  return Object.fromEntries([...files].sort());
}

async function sandbox(t) {
  const dir = await fs.mkdtemp(path.join(process.env.TMPDIR, 'chat-acceptance-'));
  const resources = [];
  let driver;
  t.after(async () => {
    for (const close of resources.reverse()) await close();
    await fs.rm(dir, { recursive: true, force: true });
  });

  async function service(settings = {}) {
    t.signal.throwIfAborted();
    const folder = await deliveryCopy(dir);
    const defaults = { data: !!settings.defaultData, port: !!settings.defaultPort };
    const data = defaults.data ? path.join(folder, 'data') : await fs.mkdtemp(path.join(dir, 'data-'));
    const initialTree = settings.copy ? await tree(folder) : null;
    // Asking the OS to bind first keeps all checks away from occupied ports, including the documented default.
    let port;
    const deadline = Date.now() + 8000;
    while (port === undefined) {
      try {
        port = await portAvailable(defaults.port ? 3000 : 0);
      } catch (error) {
        if (!defaults.port || error.code !== 'EADDRINUSE') throw error;
        if (Date.now() >= deadline) {
          t.diagnostic('Port 3000 stayed occupied. The unset PORT observation is unavailable on this host.');
          defaults.port = false;
        } else await delay(200, undefined, { signal: t.signal });
      }
    }
    const env = environment(settings, defaults, data, port);
    const args = [entry];
    if (settings.coverage) {
      env.NODE_V8_COVERAGE = settings.coverage;
      env.RATCHET_ACCEPTANCE_COVERAGE = '1';
      args.unshift('--require', __filename);
    }
    const url = 'http://127.0.0.1:' + port + '/';
    const request = () => fetch(url, { signal: AbortSignal.timeout(800) });
    let proc;
    async function start() {
      t.signal.throwIfAborted();
      proc = processHandle(process.execPath, args, { cwd: folder, env });
      try {
        await eventually(async () => {
          if (proc.log.done) return 'exited';
          try {
            const response = await request();
            await response.arrayBuffer();
            return 'reachable';
          } catch {
            return 'waiting';
          }
        }, value => value !== 'waiting', 'The app should start and accept HTTP on its configured port', 4400);
        assert.equal(proc.log.done, false, 'The running service is absent: ' + proc.log.stderr.trim().split('\n').find(line => line.includes('Error:')));
      } catch (error) {
        await proc.stop();
        throw error;
      }
    }
    const stop = signal => proc.stop(signal);
    resources.push(stop);
    await start();
    return {
      url, request, folder, data, initialTree, stop,
      async restart(signal) { await stop(signal); await start(); },
    };
  }

  async function browser(service, options = {}) {
    t.signal.throwIfAborted();
    driver ??= (async () => {
      const binary = path.join(dir, 'webkit-driver');
      const result = await run('swiftc', [path.join(__dirname, 'webkit.swift'), '-o', binary], { cwd: root }, 12000, t.signal);
      assert.equal(result.code, 0, 'The WebKit driver must compile: ' + result.stderr);
      return binary;
    })();
    const binary = await driver;
    t.signal.throwIfAborted();
    const page = new Page(binary, service.url, options);
    resources.push(() => page.dispose());
    await page.open();
    return page;
  }

  async function coveredProviderReply() {
    const coverage = path.join(dir, 'provider-coverage');
    const live = await service({ coverage });
    const page = await browser(live);
    await page.enter();
    assert.equal(await page.ask('provider identity'), (await offline('provider identity')).text);
    await live.stop();
    const hits = await touched(coverage, live.folder);
    assert.ok(hits.get('provider/standin.js')?.some(fn => fn.functionName === 'respond'),
      'Serving the reply executes respond in the original provider file');
  }

  async function ruleTests() {
    const appCoverage = path.join(dir, 'app-coverage');
    const testCoverage = path.join(dir, 'test-coverage');
    const live = await service({ coverage: appCoverage });
    const page = await browser(live);
    await page.enter();
    await page.ask('remember that acceptance covers rules');
    await live.stop();
    const ranInTest = await npmRuleTests(live.folder, testCoverage, t.signal);
    const ranInApp = await touched(appCoverage, live.folder);
    const ruleModules = [...ranInTest].filter(([file, functions]) =>
      file !== entry && !/^(provider|records|acceptance|test)\//.test(file) &&
      functions.some(fn => fn.functionName &&
        ranInApp.get(file)?.some(appFn => appFn.ranges[0].startOffset === fn.ranges[0].startOffset)));
    assert.ok(ruleModules.length, 'The app and npm test execute common functions in application rule modules');
  }

  return { service, browser, coveredProviderReply, ruleTests, tree };
}

async function touched(dir, folder) {
  const hits = new Map();
  for (const file of await fs.readdir(dir)) {
    if (!file.endsWith('.json')) continue;
    const data = JSON.parse(await bytes(file, dir));
    for (const script of data.result) {
      const prefix = 'file://' + folder + '/';
      if (!script.url.startsWith(prefix)) continue;
      const file = decodeURIComponent(script.url.slice(prefix.length));
      const functions = script.functions.filter(fn => fn.ranges[0]?.count > 0);
      hits.set(file, [...hits.get(file) ?? [], ...functions]);
    }
  }
  return hits;
}

async function npmRuleTests(folder, coverage, signal) {
  const result = await run('npm', ['test'], {
    cwd: folder,
    env: { ...process.env, NODE_V8_COVERAGE: coverage },
  }, 16000, signal);
  assert.equal(result.code, 0, 'npm test succeeds: ' + result.stdout + result.stderr);
  assert.match(result.stdout + result.stderr, /\b(?:ok\s+\d+|pass\s+[1-9]\d*)\b/i, 'npm test reports passing Node tests');
  const hits = await touched(coverage, folder);
  assert.ok([...hits].some(([file, functions]) => file.startsWith('test/') && functions.length),
    'The Node test runner executes files under test/');
  return hits;
}

async function baselineRuleTests(t) {
  const dir = await fs.mkdtemp(path.join(process.env.TMPDIR, 'chat-tests-coverage-'));
  t.after(() => fs.rm(dir, { recursive: true, force: true }));
  await npmRuleTests(await deliveryCopy(dir), dir, t.signal);
}

// Installed before the page's scripts. Queries depend only on public names and markup semantics.
// The network hooks can hold or drop a response and replay a browser's actual HTTP command.
function browserTools() {
  const clean = text => String(text ?? '').replace(/\s+/g, ' ').trim();
  const aria = (node, key) => node.getAttribute('aria-' + key);
  function name(node, seen = new Set()) {
    if (seen.has(node)) return '';
    seen.add(node);
    const references = aria(node, 'labelledby')?.split(/\s+/).map(id => document.getElementById(id)).filter(Boolean);
    if (references?.length) return clean(references.map(target => name(target, seen)).join(' '));
    if (aria(node, 'label')) return clean(aria(node, 'label'));
    if (node.labels?.length) return clean([...node.labels].map(label => label.textContent).join(' '));
    if (node.matches('input[type=submit],input[type=button],input[type=reset]')) return clean(node.value);
    if (node.matches('img,input[type=image]')) return clean(node.alt);
    if (['region', 'navigation', 'article', 'status', 'listitem', 'textbox', 'alert'].includes(kind(node))) {
      return clean(node.title);
    }
    return clean(node.textContent || node.title);
  }
  function kind(node) {
    const explicit = node.getAttribute('role')?.trim().split(/\s+/)[0];
    if (explicit) return explicit;
    if (node.matches('nav')) return 'navigation';
    if (node.matches('section') && (aria(node, 'label') || aria(node, 'labelledby') || node.title)) return 'region';
    if (node.matches('article')) return 'article';
    if (node.matches('textarea,input:not([type]),input[type=text],input[type=password],input[type=email],input[type=url],input[type=tel]')) return 'textbox';
    if (node.matches('button,input[type=button],input[type=submit],input[type=reset],input[type=image],summary')) return 'button';
    if (node.matches('output')) return 'status';
    if (node.matches('li')) return 'listitem';
    if (node.matches('a[href]')) return 'link';
    return '';
  }
  function shown(node) {
    if (node.closest('[aria-hidden="true"],[hidden],[inert]')) return false;
    const style = getComputedStyle(node);
    return node.getClientRects().length > 0 && style.visibility === 'visible' &&
      (typeof node.checkVisibility !== 'function' || node.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true }));
  }
  function matches(query, parent = document) {
    if (query.within) return matches(query.within, parent).flatMap(node => matches({ ...query, within: undefined }, node));
    return [...parent.querySelectorAll('*')].filter(node =>
      kind(node) === query.kind && (query.name === undefined || name(node) === query.name) && shown(node));
  }
  function messageText(node) {
    const label = name(node);
    if (!label.startsWith('Message from ')) return null;
    const speaker = label.slice('Message from '.length);
    const metadata = new Set([label, speaker, 'You']);
    const omitted = child => ['region', 'status', 'alert', 'button'].includes(kind(child)) ||
      child.matches('time,header,[aria-hidden="true"]') || metadata.has(clean(child.innerText));
    const parts = [...node.childNodes].map(child => {
      if (child.nodeType === Node.TEXT_NODE) return child.textContent;
      if (child.nodeType !== Node.ELEMENT_NODE || omitted(child) || !shown(child)) return '';
      return child.querySelector('[role="alert"],[role="status"],[role="region"],section[aria-label],button,time')
        ? [...child.childNodes].filter(part => part.nodeType === Node.TEXT_NODE || part.nodeType === Node.ELEMENT_NODE && !omitted(part))
          .map(part => part.innerText ?? part.textContent).join('\n')
        : child.innerText;
    });
    return parts.map(part => part.trim()).filter(Boolean).join('\n').trim() ||
      (node.innerText ?? node.textContent).trim();
  }
  function measure(node) {
    const { x, y, width, height, top, right, bottom, left } = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    const current = aria(node, 'current');
    return {
      kind: kind(node), name: name(node), text: node.innerText ?? node.textContent, payload: messageText(node),
      value: node.value ?? (node.isContentEditable ? node.innerText : null),
      current: !!current && current !== 'false',
      disabled: node.matches(':disabled') || aria(node, 'disabled') === 'true', focused: document.activeElement === node,
      focusVisible: node.matches(':focus-visible'),
      outline: style.outlineStyle === 'none' ? 0 : parseFloat(style.outlineWidth),
      boxShadow: style.boxShadow, fontSize: parseFloat(style.fontSize), lineHeight: style.lineHeight,
      box: { x, y, width, height, top, right, bottom, left },
      clientWidth: node.clientWidth, scrollWidth: node.scrollWidth,
      scrollTop: node.scrollTop, scrollHeight: node.scrollHeight, clientHeight: node.clientHeight,
    };
  }
  function fill(node, value) {
    node.focus();
    const prototype = node instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    if (node.isContentEditable) node.textContent = value;
    else Object.getOwnPropertyDescriptor(prototype, 'value').set.call(node, value);
    node.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText' }));
    node.dispatchEvent(new Event('change', { bubbles: true }));
  }
  const fetchOriginal = window.fetch.bind(window);
  const traffic = [];
  let gate;
  let watcher;
  let sequence = 0;
  const sameOrigin = url => new URL(url, location.href).origin === location.origin;
  window.fetch = async function (input, init) {
    const request = new Request(input, init);
    if (!sameOrigin(request.url)) return fetchOriginal(request);
    const log = { id: ++sequence, url: request.url, method: request.method, headers: [...request.headers] };
    traffic.push(log);
    const hold = gate?.method === request.method ? gate : null;
    if (hold) { gate = null; hold.claimed = true; }
    if (request.method !== 'GET' && request.method !== 'HEAD') log.body = await request.clone().text();
    if (hold?.mode === 'abort') {
      log.status = 0;
      throw new TypeError('acceptance: request stopped before transmission');
    }
    const response = await fetchOriginal(request);
    log.status = response.status;
    log.responseHeaders = [...response.headers];
    log.response = await response.clone().text();
    if (hold) {
      hold.received = true;
      if (hold.mode === 'drop') throw new TypeError('acceptance: response lost after service acknowledged it');
      await hold.promise;
    }
    return response;
  };
  window.__acceptance = {
    find: query => matches(query).map(measure),
    viewport: () => ({ width: innerWidth, height: innerHeight, scrollWidth: document.documentElement.scrollWidth }),
    html: () => document.documentElement.outerHTML,
    async assets() {
      const urls = [...document.querySelectorAll('script[src],link[rel=stylesheet][href]')]
        .map(node => node.src || node.href).filter(sameOrigin);
      return Promise.all(urls.map(async url => {
        const response = await fetchOriginal(url);
        return { headers: [...response.headers], text: await response.text() };
      }));
    },
    visibleText: () => document.body.innerText,
    click(query, index) { matches(query)[index]?.click(); },
    focus(query, index) { matches(query)[index]?.focus(); },
    fill(query, index, value) {
      const node = matches(query)[index];
      if (node) fill(node, value);
    },
    traffic: from => traffic.filter(item => item.id > from),
    stamp: () => sequence,
    watch(control, result) {
      watcher?.observer.disconnect();
      const samples = [];
      function sample() {
        const next = {
          actionable: matches(control).some(node => !measure(node).disabled),
          result: matches(result).map(node => node.innerText).join('\n'),
        };
        if (JSON.stringify(next) !== JSON.stringify(samples.at(-1))) samples.push(next);
      }
      const observer = new MutationObserver(sample);
      observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true, characterData: true });
      watcher = { observer, samples };
      sample();
    },
    watched() { return watcher?.samples ?? []; },
    arm(method, mode) {
      const hold = { method, mode, claimed: false, received: false };
      hold.promise = new Promise(resolve => { hold.release = resolve; });
      gate = hold;
      window.__acceptance.held = hold;
    },
    heldState() {
      const hold = window.__acceptance.held;
      return hold && { claimed: hold.claimed, received: hold.received };
    },
    release() { window.__acceptance.held?.release(); },
    async replay({ url, method, headers, body }) {
      const response = await fetchOriginal(url, { method, headers, body });
      return { status: response.status, text: await response.text() };
    },
  };
}

class Page {
  constructor(binary, url, { keyboard = false } = {}) {
    this.url = url;
    this.keyboard = keyboard;
    this.proc = processHandle(binary, []);
    this.waiting = new Map();
    this.id = 0;
    createInterface({ input: this.proc.child.stdout }).on('line', line => {
      const reply = JSON.parse(line);
      const entry = this.waiting.get(reply.id);
      if (!entry) return;
      if (reply.error) entry.reject(new Error(reply.error));
      else entry.resolve(reply.value);
    });
    this.proc.done.then(result => {
      for (const { reject } of this.waiting.values()) {
        reject(new Error('WebKit driver exited: ' + JSON.stringify(result) + this.proc.log.stderr));
      }
    });
  }
  async call(op, args = {}) {
    const id = ++this.id;
    const response = new Promise((resolve, reject) => this.waiting.set(id, { resolve, reject }));
    const timer = setTimeout(() => this.waiting.get(id)?.reject(new Error('WebKit timed out performing ' + op)), 4500);
    try {
      this.proc.child.stdin.write(JSON.stringify({ id, op, ...args }) + '\n');
      return await response;
    } finally {
      clearTimeout(timer);
      this.waiting.delete(id);
    }
  }
  evaluate(source) { return this.call('eval', { source }); }
  inspect(action, ...args) {
    return this.evaluate('return await window.__acceptance[' + JSON.stringify(action) + '](...' + JSON.stringify(args) + ');');
  }
  async open() { return this.call('open', { url: this.url, script: '(' + browserTools.toString() + ')();' }); }
  reload() { return this.call('reload'); }
  close() { return this.call('close'); }
  reopen() { return this.call('return', { url: this.url }); }
  size(width, height = 900) { return this.call('size', { width, height }); }
  key(key) { return this.call('key', { key }); }
  async dispose() {
    this.proc.child.stdin.end();
    let timer;
    try {
      const expired = new Promise(resolve => { timer = setTimeout(() => resolve(true), 650); });
      if (await Promise.race([this.proc.done.then(() => false), expired])) await this.proc.stop();
    } finally { clearTimeout(timer); }
  }
  find(query) { return this.inspect('find', query); }
  wait(query, index = 0) {
    return eventually(() => this.find(query), found => found.length > index, 'Find accessible ' + JSON.stringify(query));
  }
  absent(query) {
    return eventually(() => this.find(query), found => found.length === 0, 'No accessible ' + JSON.stringify(query));
  }
  async text(query) { return (await this.find(query)).map(item => item.text).join('\n').trim(); }
  async value(query) { return (await this.wait(query))[0].value; }
  async focusByKey(query, index = 0) {
    for (let visited = 0; visited < 100; visited += 1) {
      const row = (await this.find(query))[index];
      if (row?.focused) return row;
      // Option+Tab in WebKit traverses every control, regardless of the host's keyboard preference.
      await this.key('Option+Tab');
    }
    assert.fail('Reach ' + JSON.stringify(query) + ' with keyboard navigation');
  }
  async click(query, index = 0) {
    await eventually(() => this.find(query), rows => rows[index] && !rows[index].disabled,
      'Activate ' + JSON.stringify(query));
    if (this.keyboard) {
      await this.focusByKey(query, index);
      await this.key('Enter');
    } else {
      await this.inspect('click', query, index);
    }
  }
  async fill(query, value, index = 0) {
    if (this.keyboard) await this.focusByKey(query, index);
    else await this.wait(query, index);
    await this.inspect('fill', query, index, value);
  }
  async enter(name = 'Maya') { await this.click(button('Continue as ' + name)); }
  async switch() { await this.click(button('Switch person')); }
  async person(name) { await this.switch(); await this.enter(name); }
  async ready() {
    await eventually(() => this.find(textbox('Message')), rows => rows.some(row => !row.disabled), 'The message composer is available');
  }
  async selectBot(name) { await this.click(button(name, nav('Bots'))); }
  async newBot(name, rename = false) {
    await this.click(button(rename ? 'Rename bot' : 'New bot'));
    await this.fill(textbox('Bot name'), name);
    await this.click(button('Save bot name'));
    await this.wait(button(name, nav('Bots')));
  }
  async newChat() {
    await this.click(button('New conversation'));
    await eventually(() => this.messages(), messages => messages.length === 0, 'New conversation has an empty transcript');
  }
  messages(name) {
    return this.find(article(name === undefined ? undefined : 'Message from ' + name, region('Conversation')));
  }
  async send(text, key) {
    await this.fill(textbox('Message'), text);
    if (key) await this.key(key);
    else await this.click(button('Send'));
  }
  async nextReply(previousCount, person = 'Maya') {
    const rows = await eventually(() => this.messages(),
      all => all.filter(item => item.name !== 'Message from ' + person).length > previousCount,
      'A new assistant reply appears in the transcript');
    const reply = rows.filter(item => item.name !== 'Message from ' + person).at(-1);
    return (reply.payload ?? reply.text).trim();
  }
  async ask(text, person = 'Maya') {
    await this.ready();
    const count = (await this.messages()).filter(item => item.name !== 'Message from ' + person).length;
    await this.send(text);
    return this.nextReply(count, person);
  }
  async save(kind, name, text) {
    const scope = region(kind === 'Instruction' ? 'Saved instructions' : 'Saved tasks');
    await this.fill(textbox(kind + ' name', scope), name);
    await this.fill(textbox(kind + (kind === 'Instruction' ? ' text' : ' request'), scope), text);
    await this.click(button('Save ' + kind.toLowerCase(), scope));
  }
  async token(token) {
    const setup = region('Setup');
    await this.fill(textbox('Provider token', setup), token);
    await this.click(button('Save token', setup));
  }
  async capture(action) {
    const cursor = await this.inspect('stamp');
    await action();
    const writes = await eventually(() => this.inspect('traffic', cursor),
      items => items.some(item => item.method === 'POST' && item.status !== undefined),
      'The public HTTP command was issued');
    return writes.find(item => item.method === 'POST' && item.status !== undefined);
  }
  replay(command, currentCommand) {
    const next = { ...command };
    if (currentCommand) {
      const current = JSON.parse(currentCommand.body);
      const original = JSON.parse(command.body);
      for (const key of Object.keys(current)) {
        if (/^(?:expected)?(?:selection)?(?:version|revision)$/i.test(key) && key in original) original[key] = current[key];
      }
      next.body = JSON.stringify(original);
    }
    return this.inspect('replay', next);
  }
}

module.exports = {
  assert, delay, role, region, nav, button, textbox, article, eventually,
  original, fixtureNames, fixtureBytes, fixtures, offline, provider, stepsOf,
  shortToken, longToken, refused, delivered, sandbox, baselineRuleTests,
};
