import sys; sys.path.insert(0, '/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/v2170-ds-battleship')
from mk_common import write

PRE = """const s = await L.inproc({ random: L.seeded(2) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
"""
POST = "\n  } finally { await s.close(); }"
def w(wid, body):
    write(wid, "L.run(async () => {\n  " + PRE + body + POST + "\n});")
def st(wid, rawbody, status, label):
    w(wid, f"const x = await L.rawFire(s.port, {rawbody});\n    check(x.status === {status}, {label!r} + ' answered ' + x.status + ' ' + x.text.slice(0, 100));")

st('R-7.1', "'{not json'", 400, 'malformed JSON')
st('R-7.2', "'{}'", 400, '{}')
st('R-7.3', "JSON.stringify({ game: 123, row: 0, col: 0 })", 400, 'numeric game')
st('R-7.4', "JSON.stringify({ game: '', row: 0, col: 0 })", 400, 'empty game')
st('R-7.5', "JSON.stringify({ game: g, row: 1.5, col: 0 })", 400, 'row 1.5')
st('R-7.6', "JSON.stringify({ game: g, row: '1', col: 0 })", 400, 'row "1"')
st('R-7.7', "JSON.stringify({ game: g, row: 0, col: 1.5 })", 400, 'col 1.5')
st('R-7.8', "JSON.stringify({ game: g, row: 0, col: '1' })", 400, 'col "1"')
st('R-7.9', "JSON.stringify({ game: '00000000-0000-4000-8000-000000000000', row: 0, col: 0 })", 404, 'unknown UUID')
st('R-7.10', "JSON.stringify({ game: 'not-a-uuid', row: 0, col: 0 })", 404, 'non-UUID id')
w('R-7.11', """const body = JSON.stringify({ game: g, row: 0, col: 0 });
    const big = body + ' '.repeat(1024 * 1024 + 1 - body.length);
    check(big.length === 1024 * 1024 + 1, 'test body size');
    const x = await L.rawFire(s.port, big);
    check(x.status === 413, 'a body of 1 MB + 1 byte answered ' + x.status);""")
w('R-7.12', """const body = JSON.stringify({ game: g, row: 0, col: 0 });
    const big = body + ' '.repeat(1000000 - body.length);
    const x = await L.rawFire(s.port, big);
    check(x.status !== 413 && x.status === 200, 'a valid body of 1,000,000 bytes answered ' + x.status);""")
w('R-7.13', "const x = await L.req(s.port, 'GET', '/api/fire'); check(x.status === 405, 'GET /api/fire answered ' + x.status);")
w('R-7.14', "const x = await L.req(s.port, 'POST', '/api/new', { body: '{}', headers: { 'content-type': 'application/json' } }); check(x.status === 405, 'POST /api/new answered ' + x.status);")
w('R-7.15', "const x = await L.req(s.port, 'POST', '/', { body: '{}', headers: { 'content-type': 'application/json' } }); check(x.status === 405, 'POST / answered ' + x.status);")
w('R-7.16', "const x = await L.getJson(s.port, '/api/new?x=1'); check(x.status === 200 && x.json && typeof x.json.game === 'string', 'GET /api/new?x=1 answered ' + x.status);")
w('R-7.17', "const x = await L.getJson(s.port, '/api/fire/'); check(x.status === 404, 'GET /api/fire/ answered ' + x.status);")
w('R-7.18', "const x = await L.getJson(s.port, '/api'); check(x.status === 404, 'GET /api answered ' + x.status);")
w('R-7.19', "const x = await L.getJson(s.port, '/nope'); check(x.status === 404, 'GET /nope answered ' + x.status); check(x.json && typeof x.json.error === 'string', 'body is not JSON error: ' + x.text.slice(0, 80)); check(!/<html/i.test(x.text), 'the page was served');")

ERRS = """const errs = [];
    errs.push(await L.rawFire(s.port, '{bad'));
    errs.push(await L.rawFire(s.port, JSON.stringify({ game: 'zzz', row: 0, col: 0 })));
    errs.push(await L.req(s.port, 'GET', '/api/fire'));
    errs.push(await L.req(s.port, 'POST', '/api/new', { body: '{}' }));
    errs.push(await L.req(s.port, 'POST', '/', { body: '{}' }));
    errs.push(await L.getJson(s.port, '/nope'));
    await L.fire(s.port, g, 1, 1); errs.push(await L.fire(s.port, g, 1, 1));
    const body = JSON.stringify({ game: g, row: 0, col: 0 });
    errs.push(await L.rawFire(s.port, body + ' '.repeat(1024 * 1024 + 1 - body.length)));
    check(errs.map((e) => e.status).join() === '400,404,405,405,405,404,409,413', 'statuses ' + errs.map((e) => e.status));
"""
w('R-7.20', ERRS + """for (const e of errs) {
      check(e.json && typeof e.json === 'object' && !Array.isArray(e.json), 'status ' + e.status + ' body is not a JSON object: ' + e.text.slice(0, 80));
      check(Object.keys(e.json).join() === 'error' && typeof e.json.error === 'string' && e.json.error.length > 0, 'status ' + e.status + ' body keys ' + Object.keys(e.json));
    }""")
w('R-7.21', ERRS + """for (const e of errs) check(/application\\/json/.test(e.headers['content-type'] || ''), 'status ' + e.status + ' content-type ' + e.headers['content-type']);""")

# crash conditions: a real child process
SPAWN = """const p = await L.freePort();
  const s = L.spawnServer({ port: p });
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/api/new')).status === 200; } catch { return false; } }, 6000, 'start');
    const g = (await L.getJson(p, '/api/new')).json.game;
"""
def sp(wid, body):
    write(wid, "L.run(async () => {\n  " + SPAWN + "    " + body + "\n    await L.sleep(400);\n    const alive = await L.getJson(p, '/api/new').catch(() => null);\n    check(s.exited === null && alive && alive.status === 200, 'the server is gone or not serving afterwards: ' + JSON.stringify(s.exited) + ' ' + s.stderr.slice(0, 120));\n  } finally { await s.kill(); }\n});")
sp('R-7.22', "const x = await L.rawFire(p, '{not json'); check(x.status === 400, 'malformed body answered ' + x.status);")
sp('R-7.23', "const body = JSON.stringify({ game: g, row: 0, col: 0 }); const x = await L.rawFire(p, body + ' '.repeat(1024 * 1024 + 1 - body.length)); check(x.status === 413, 'oversized body answered ' + x.status);")
sp('R-7.24', """const raw = await new Promise((resolve) => {
      const sock = L.net.connect(p, '127.0.0.1');
      let data = '';
      sock.on('connect', () => sock.write('GET http://[ HTTP/1.1\\r\\nHost: x\\r\\nConnection: close\\r\\n\\r\\n'));
      sock.on('data', (d) => { data += d; });
      sock.on('close', () => resolve(data));
      sock.on('error', () => resolve(data));
      setTimeout(() => { sock.destroy(); resolve(data); }, 3000);
    });
    check(/^HTTP\\/1\\.1 400/.test(raw), 'GET http://[ answered ' + JSON.stringify(raw.slice(0, 60)));""")
# 7.25: degenerate Math.random, child process
write('R-7.25', r"""
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
});""")
write('R-8.1', r"""
L.run(async () => {
  const child = L.cp.spawn(process.execPath, ['-e', "require('./battleship.js'); setTimeout(() => {}, 1500);"], { cwd: L.WORK, stdio: 'ignore' });
  let code = 'running';
  child.once('exit', (c) => { code = c; });
  await L.sleep(700);
  const ports = L.lsofPorts(child.pid);
  check(ports.length === 0, 'requiring battleship.js opened listening sockets: ' + ports);
  await L.sleep(1800);
  check(code === 0, 'the process did not exit normally (exit ' + code + ')');
  if (code === 'running') child.kill('SIGKILL');
});""")

# ---------------- R-10 HTTP/process ----------------
write('R-10.5', r"""
L.run(async () => {
  const p = await L.freePort();
  let s = L.spawnServer({ port: p });
  let id;
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/api/new')).status === 200; } catch { return false; } }, 6000, 'start');
    id = (await L.getJson(p, '/api/new')).json.game;
    check((await L.fire(p, id, 0, 0)).status === 200, 'a shot in the first process');
  } finally { await s.kill(); }
  await L.sleep(300);
  s = L.spawnServer({ port: p });
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/api/new')).status === 200; } catch { return false; } }, 6000, 'restart');
    const x = await L.fire(p, id, 0, 0);
    check(x.status === 404, 'an id issued before the restart answered ' + x.status + ' after it');
  } finally { await s.kill(); }
});""")

def two(wid, body):
    write(wid, "L.run(async () => {\n  const s = await L.inproc({ random: L.seeded(12) });\n  try {\n    const a = (await L.getJson(s.port, '/api/new')).json.game, b = (await L.getJson(s.port, '/api/new')).json.game;\n    " + body + "\n  } finally { await s.close(); }\n});")
two('R-10.8', """const x = await L.fire(s.port, a, 0, 0);
    check(x.status === 200, 'game A shot answered ' + x.status);
    const y = await L.fire(s.port, b, 0, 0);
    check(y.status === 200, "a shot at game B's cell (0,0) answered " + y.status + ' after game A fired there');
    const z = await L.fire(s.port, b, 0, 0);
    check(z.status === 409, 'repeat in game B answered ' + z.status);""")
two('R-10.9', """// drive game A to gameOver with a row-major walk
    for (let i = 0; i < 100; i++) { const x = await L.fire(s.port, a, Math.floor(i / 10), i % 10); if (x.json && x.json.gameOver) break; }
    let waterB = null;
    const y = await L.fire(s.port, b, 9, 9);
    check(y.status === 200, "game B's shot after game A ended answered " + y.status);
    check(y.json.gameOver === false && y.json.shipsRemaining >= 4, "game B's answer after game A ended: " + JSON.stringify(y.json));""")
two('R-10.10', """const fleet = L.fleetOf(12); // first game dealt from seed 12 is game A
    const c = fleet[0].cells[0];
    const [x, y] = await Promise.all([L.fire(s.port, a, c.row, c.col), L.fire(s.port, a, c.row, c.col)]);
    check([x.status, y.status].sort().join() === '200,409', 'two simultaneous shots at one cell answered ' + [x.status, y.status]);""")
two('R-10.11', """const fleet = L.fleetOf(12);
    const c = fleet[0].cells[0];
    const [x, y] = await Promise.all([L.fire(s.port, a, c.row, c.col), L.fire(s.port, a, c.row, c.col)]);
    const ok = [x, y].find((r) => r.status === 200);
    check(ok && ok.json.shipsRemaining === 5, 'the accepted shot reported ' + JSON.stringify(ok && ok.json));
    const again = await L.fire(s.port, a, c.row, c.col);
    check(again.status === 409, 'after the simultaneous pair the cell counts as fired once, but a further shot answered ' + again.status);
    // the rest of the game reconciles: sunk 5, hit 12 including the pair's accepted shot
    const m = L.modelFor(fleet); m.expect(c.row, c.col);
    let sunk = ok.json.result === 'sunk' ? 1 : 0, hit = ok.json.result === 'hit' ? 1 : 0, last = ok.json, over = false;
    for (let i = 0; i < 100 && !over; i++) {
      const r = Math.floor(i / 10), cc = i % 10;
      if (r === c.row && cc === c.col) continue;
      const q = await L.fire(s.port, a, r, cc);
      check(q.status === 200, 'shot ' + r + ',' + cc + ' answered ' + q.status);
      if (q.json.result === 'sunk') sunk++; if (q.json.result === 'hit') hit++;
      last = q.json; if (q.json.gameOver) over = true;
    }
    check(sunk === 5 && hit === 12 && last.shipsRemaining === 0, 'totals sunk ' + sunk + ' hit ' + hit + ' final ' + JSON.stringify(last));""")
print('ok')
