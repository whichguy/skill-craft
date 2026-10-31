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
  const { p, s } = await second();
  check(s.exited !== null, 'the second server hung instead of exiting');
  check(s.stderr.trim().length > 0, 'stderr is empty (stdout: ' + JSON.stringify(s.stdout) + ')');
  check(/in use|EADDRINUSE|already/i.test(s.stderr) && s.stderr.includes(String(p)), 'stderr does not clearly name the problem and port: ' + JSON.stringify(s.stderr.slice(0, 200)));
});
