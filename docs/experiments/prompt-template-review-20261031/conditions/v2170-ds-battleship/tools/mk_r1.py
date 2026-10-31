import sys; sys.path.insert(0, '/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/v2170-ds-battleship')
from mk_common import write

# helper block shared by the PORT witnesses: where does the server end up listening?
PORTHELP = r"""
function expectPort(r, port, label) {
  const ok = (r.kind === 'listening' && r.ports.includes(port))
    || (r.kind === 'refused' && r.port === port)
    || (r.kind === 'died' && new RegExp('127\\.0\\.0\\.1:' + port + '\\b').test(r.err));
  check(ok, label + ': expected the server to listen on (or be refused on) ' + port + ', got ' + JSON.stringify({ kind: r.kind, ports: r.ports, port: r.port, out: r.out.slice(0, 120), err: r.err.slice(0, 160) }));
}
"""
def portw(wid, value, port, label):
    v = 'undefined' if value is None else repr(value)
    expect = f"const r = await L.listenReport({v});\nexpectPort(r, {port}, {label!r});"
    write(wid, PORTHELP + "L.run(async () => {\n" + expect + "\n});")

write('R-1.1', r"""
L.run(async () => {
  const p = await L.freePort();
  const s = L.spawnServer({ port: p });
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/api/new')).status === 200; } catch { return false; } }, 6000, 'the server to answer');
    await L.sleep(6000);
    check(s.exited === null, 'the process exited ' + JSON.stringify(s.exited) + ' within 6 s of starting');
    const r = await L.getJson(p, '/api/new');
    check(r.status === 200, 'GET /api/new after 6 s idle answered ' + r.status);
    const page = await L.getJson(p, '/');
    check(page.status === 200, 'GET / after 6 s idle answered ' + page.status);
  } finally { await s.kill(); }
});
""")
p2 = r"""
L.run(async () => {
  const p = await L.freePort();
  const r = await L.listenReport(String(p));
  check(r.kind === 'listening' && r.ports.includes(p), 'PORT=' + p + ' should be listened on, got ' + JSON.stringify({ kind: r.kind, ports: r.ports, out: r.out.slice(0, 100) }));
});
"""
write('R-1.2', p2)
portw('R-1.3', '65535', 65535, 'PORT=65535')
portw('R-1.4', '65536', 3000, 'PORT=65536')
portw('R-1.5', '1', 1, 'PORT=1')
portw('R-1.6', None, 3000, 'PORT unset')
portw('R-1.7', 'abc', 3000, 'PORT=abc')
portw('R-1.8', '', 3000, 'PORT=""')
portw('R-1.9', '0', 3000, 'PORT=0')
portw('R-1.10', '70000', 3000, 'PORT=70000')
portw('R-1.11', '-1', 3000, 'PORT=-1')
portw('R-1.12', '1.5', 3000, 'PORT=1.5')

INUSE = r"""
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
"""
write('R-1.13', INUSE + r"""
L.run(async () => {
  const { s } = await second();
  check(s.exited !== null, 'the second server hung instead of exiting');
  check(s.exited.code !== 0 && s.exited.code !== null, 'exit status was ' + JSON.stringify(s.exited));
});
""")
write('R-1.14', INUSE + r"""
L.run(async () => {
  const { p, s } = await second();
  check(s.exited !== null, 'the second server hung instead of exiting');
  check(s.stderr.trim().length > 0, 'stderr is empty (stdout: ' + JSON.stringify(s.stdout) + ')');
  check(/in use|EADDRINUSE|already/i.test(s.stderr) && s.stderr.includes(String(p)), 'stderr does not clearly name the problem and port: ' + JSON.stringify(s.stderr.slice(0, 200)));
});
""")
write('R-1.15', r"""
L.run(async () => {
  const nets = Object.values(L.os.networkInterfaces()).flat().filter((a) => a && a.family === 'IPv4' && !a.internal);
  if (nets.length === 0) { console.log('no non-internal IPv4 address on this host'); process.exit(3); }
  const p = await L.freePort();
  const s = L.spawnServer({ port: p });
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/api/new')).status === 200; } catch { return false; } }, 6000, 'start');
    const refused = await new Promise((resolve) => {
      const c = L.net.connect({ host: nets[0].address, port: p, timeout: 2000 });
      c.on('connect', () => { c.destroy(); resolve(false); });
      c.on('error', () => resolve(true));
      c.on('timeout', () => { c.destroy(); resolve(true); });
    });
    check(refused, 'a connection to ' + nets[0].address + ':' + p + ' was accepted (the service is not loopback-only)');
  } finally { await s.kill(); }
});
""")
write('R-1.16', r"""
L.run(async () => {
  const p = await L.freePort();
  const s = L.spawnServer({ port: p });
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/api/new')).status === 200; } catch { return false; } }, 6000, 'start');
    await L.sleep(100);
    const out = s.stdout + s.stderr;
    check(new RegExp('https?://[^\\s]*:' + p + '\\b').test(out), 'startup output does not name an http URL with port ' + p + ': ' + JSON.stringify(out.slice(0, 200)));
  } finally { await s.kill(); }
});
""")
print('ok')
