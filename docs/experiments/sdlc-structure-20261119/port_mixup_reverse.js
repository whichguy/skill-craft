'use strict';

/**
 * The other direction of port_mixup_demo.js, part 2: can a listener that asks for "any free port" ON 127.0.0.1 be
 * given a number that a listener on EVERY address already holds?
 *
 * It holds HELD listeners on every address (its own; they take no connection), then asks for a port on 127.0.0.1 TRIES
 * times, closing each at once, and counts the numbers given that are among the held ones. Then the same asking with no
 * address, which the system must never answer with a held number (two listeners on every address cannot share one).
 *
 *   node port_mixup_reverse.js [HELD, default 2000] [TRIES, default 40000]
 */

const net = require('node:net');

const held = Number(process.argv[2]) || 2000;
const tries = Number(process.argv[3]) || 40000;

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

async function lottery(count, numbers, ...where) {
  let hits = 0;
  for (let index = 0; index < count; index += 1) {
    const server = net.createServer();
    const { port } = await listen(server, 0, ...where);
    if (numbers.has(port)) hits += 1;
    await close(server);
  }
  return hits;
}

async function main() {
  const servers = [];
  const numbers = new Set();
  let family = '';
  for (let index = 0; index < held; index += 1) {
    const server = net.createServer();
    const address = await listen(server, 0);
    family = `${address.family} ${address.address}`;
    numbers.add(address.port);
    servers.push(server);
  }
  console.log(`node ${process.version} on ${process.platform}: holding ${numbers.size} port numbers on every address (${family})`);
  const onLoopback = await lottery(tries, numbers, '127.0.0.1');
  console.log(`asked for "any free port" on 127.0.0.1 ${tries} times: given a held number ${onLoopback} times ` +
    `(a held number counted as free would be about ${Math.round(tries * numbers.size / 16384)})`);
  const everywhere = await lottery(tries, numbers);
  console.log(`asked with no address ${tries} times: given a held number ${everywhere} times`);
  await Promise.all(servers.map(close));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
