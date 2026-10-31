'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const pre = L.path.join(L.os.tmpdir(), 'wit-always0-' + process.pid + '.js');
  L.fs.writeFileSync(pre, 'Math.random = () => 0;\n');
  const p = await L.freePort();
  const s = L.spawnServer({ port: p, args: ['-r', pre] });
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/')).status === 200; } catch { return false; } }, 6000, 'start');
    const x = await L.getJson(p, '/api/new').catch((e) => ({ status: 'error ' + e.message }));
    check(x.status === 500, 'GET /api/new with an unplaceable fleet answered ' + x.status);
    check(x.json && typeof x.json.error === 'string' && /json/.test(x.headers['content-type'] || ''), 'body is not a JSON error: ' + x.text);
    await L.sleep(300);
    const page = await L.getJson(p, '/').catch(() => null);
    check(s.exited === null && page && page.status === 200, 'the server stopped serving: ' + JSON.stringify(s.exited) + ' ' + s.stderr.slice(0, 160));
  } finally { await s.kill(); try { L.fs.unlinkSync(pre); } catch {} }
});
