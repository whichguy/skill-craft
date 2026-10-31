'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
async function second() {
  const p = await L.freePort();
  const holder = L.net.createServer();
  await new Promise((r) => holder.listen(p, '127.0.0.1', r));
  const s = L.spawnServer({ port: p });
  const t0 = Date.now();
  await Promise.race([s.exitP, L.sleep(6000)]);
  const res = { p, s, ms: Date.now() - t0 };
  await s.kill(); holder.close();
  return res;
}

L.run(async () => {
  const { s } = await second();
  check(s.exited !== null, 'the second server hung instead of exiting');
  check(s.exited.code !== 0 && s.exited.code !== null, 'exit status was ' + JSON.stringify(s.exited));
});
