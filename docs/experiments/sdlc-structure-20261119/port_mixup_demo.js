'use strict';

/**
 * Shows how a test of the ticket fixture can end up talking to another program, and what listening on 127.0.0.1 changes.
 *
 * The fixture starts its server with `server.listen(port)` (no address: every address of the machine) and its test client
 * dials `127.0.0.1` (test/shiploop_e2e/fixtures/node-tickets/src/server.js and test/helpers.js). This script does the same
 * two things beside "another program" that listens on 127.0.0.1 itself.
 *
 * Part 1 uses one fixed port number below the range the system hands out, so it cannot touch anyone's test run.
 * Part 2 asks the system for a free port many times, the way the fixture does, and counts how often the number it is
 * given is one that another program on this machine already holds on 127.0.0.1. Each listener of part 2 is closed at
 * once and takes no connection.
 *
 *   node port_mixup_demo.js [tries per arm, default 40000]
 */

const { execFileSync, fork } = require('node:child_process');
const http = require('node:http');
const net = require('node:net');

const LOOPBACK = '127.0.0.1';
const FIRST_FIXED_PORT = 23117; // below 49152, the first number the system hands out for "any free port"
const HANDED_OUT_FROM = 49152;
const WAIT_MS = 3000;

if (process.argv[2] === 'another-program') {
  anotherProgram(Number(process.argv[3]), process.argv[4]);
} else {
  main(Number(process.argv[2]) || 40000).catch((error) => {
    console.error(error);
    process.exit(1);
  });
}

/** The other program: it listens on 127.0.0.1 only, and either answers every request or takes the call and says nothing. */
function anotherProgram(port, behaviour) {
  const server = behaviour === 'answers'
    ? http.createServer((req, res) => {
      res.setHeader('content-type', 'application/json');
      res.end(JSON.stringify({ from: 'another program' }));
    })
    : net.createServer(() => {}); // the connection is accepted and never answered
  server.listen(port, LOOPBACK, () => process.send('listening'));
}

function startAnotherProgram(port, behaviour) {
  return new Promise((resolve, reject) => {
    const child = fork(__filename, ['another-program', String(port), behaviour]);
    child.once('error', reject);
    child.once('message', () => resolve(child));
  });
}

function stopChild(child) {
  return new Promise((resolve) => {
    child.once('exit', resolve);
    child.kill();
  });
}

/** Listen the way the caller says; resolves to the server's address, rejects with the system's refusal. */
function listen(server, ...where) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(...where, () => {
      server.off('error', reject);
      resolve(server.address());
    });
  });
}

function close(server) {
  return new Promise((resolve) => server.close(resolve));
}

/** A GET to 127.0.0.1:port, as the fixture's client sends it, but given up after WAIT_MS (the fixture's never gives up). */
function ask(port) {
  return new Promise((resolve) => {
    const agent = new http.Agent();
    const req = http.request({ hostname: LOOPBACK, port, path: '/', method: 'GET', agent }, (res) => {
      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => {
        clearTimeout(limit);
        agent.destroy();
        resolve(`answered by: ${JSON.parse(Buffer.concat(chunks).toString('utf8')).from}`);
      });
    });
    const limit = setTimeout(() => {
      req.destroy();
      agent.destroy();
      resolve(`no answer after ${WAIT_MS / 1000} s`);
    }, WAIT_MS);
    req.on('error', (error) => {
      clearTimeout(limit);
      resolve(`error: ${error.code || error.message}`);
    });
    req.end();
  });
}

function ownServer() {
  return http.createServer((req, res) => {
    res.setHeader('content-type', 'application/json');
    res.end(JSON.stringify({ from: "the test's own server" }));
  });
}

async function fixedPort() {
  for (let port = FIRST_FIXED_PORT; port < FIRST_FIXED_PORT + 50; port += 1) {
    try {
      const everywhere = net.createServer();
      await listen(everywhere, port);
      await close(everywhere);
      const here = net.createServer();
      await listen(here, port, LOOPBACK);
      await close(here);
      return port;
    } catch {
      // taken: try the next number
    }
  }
  throw new Error('no free fixed port found');
}

async function part1() {
  const port = await fixedPort();
  console.log(`Part 1: one port number, ${port}, held by two programs at once`);

  let other = await startAnotherProgram(port, 'answers');
  console.log(`  another program listens on ${LOOPBACK}:${port}`);
  const own = ownServer();
  const address = await listen(own, port); // the fixture's call: a port, no address
  console.log(`  the test's server then listens on the same number with no address given: accepted by the system, ` +
    `as ${address.family} ${address.address} port ${address.port}`);
  console.log(`  the test's client asks ${LOOPBACK}:${port} -> ${await ask(port)}`);

  await stopChild(other);
  console.log(`  with the other program gone, the same question -> ${await ask(port)}`);

  other = await startAnotherProgram(port, 'silent');
  console.log(`  another program that takes the call and says nothing now listens on ${LOOPBACK}:${port} ` +
    `(started after the test's server: the order does not matter)`);
  console.log(`  the test's client asks ${LOOPBACK}:${port} -> ${await ask(port)}`);

  const fixed = ownServer();
  try {
    await listen(fixed, port, LOOPBACK);
    console.log(`  a server told to listen on ${LOOPBACK}:${port} itself: accepted by the system (not expected)`);
    await close(fixed);
  } catch (error) {
    console.log(`  a server told to listen on ${LOOPBACK}:${port} itself: refused by the system, ${error.code}`);
  }
  await stopChild(other);
  await close(own);
}

/** The port numbers that other programs hold on 127.0.0.1 itself, in the range the system hands out, with the program. */
function heldOnLoopback() {
  const rows = execFileSync('lsof', ['-nP', '-iTCP', '-sTCP:LISTEN'], { encoding: 'utf8' }).split('\n').slice(1);
  const held = new Map();
  for (const row of rows) {
    const cells = row.trim().split(/\s+/);
    if (cells.length < 9 || cells[4] !== 'IPv4' || !cells[8].startsWith(`${LOOPBACK}:`) || Number(cells[1]) === process.pid) continue;
    const port = Number(cells[8].slice(cells[8].lastIndexOf(':') + 1));
    if (port >= HANDED_OUT_FROM) held.set(port, cells[0]);
  }
  return held;
}

/** Ask for "any free port" `tries` times, closing each listener at once; count the numbers given that are in `held`. */
async function lottery(tries, held, ...where) {
  const given = new Map();
  for (let index = 0; index < tries; index += 1) {
    const server = net.createServer();
    const { port } = await listen(server, 0, ...where);
    if (held.has(port)) given.set(port, (given.get(port) || 0) + 1);
    await close(server);
  }
  return given;
}

function total(given) {
  return [...given.values()].reduce((sum, count) => sum + count, 0);
}

async function part2(tries) {
  const before = heldOnLoopback();
  const started = Date.now();
  const everywhere = await lottery(tries, before);
  const onLoopback = await lottery(tries, before, LOOPBACK);
  const after = heldOnLoopback();
  const stayed = new Map([...before].filter(([port]) => after.has(port)));
  const programs = {};
  for (const program of stayed.values()) programs[program] = (programs[program] || 0) + 1;
  const count = (given) => total(new Map([...given].filter(([port]) => stayed.has(port))));

  console.log(`Part 2: asking the system for "any free port", ${tries} times each way (${((Date.now() - started) / 1000).toFixed(1)} s)`);
  console.log(`  port numbers other programs hold on ${LOOPBACK} itself, in the range handed out (${HANDED_OUT_FROM} to 65535), ` +
    `for the whole of the count: ${stayed.size} (${Object.entries(programs).map(([name, n]) => `${n} ${name}`).join(', ')})`);
  console.log(`  listening with no address, as the fixture does: given one of those numbers ${count(everywhere)} times ` +
    `in ${tries} (${[...everywhere].filter(([port]) => stayed.has(port)).length} of the ${stayed.size} numbers)`);
  console.log(`  listening on ${LOOPBACK}: given one of those numbers ${count(onLoopback)} times in ${tries}`);
}

async function main(tries) {
  console.log(`node ${process.version} on ${process.platform} ${require('node:os').release()}`);
  await part1();
  await part2(tries);
}
