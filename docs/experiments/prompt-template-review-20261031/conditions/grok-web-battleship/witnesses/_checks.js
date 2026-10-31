'use strict';
// One named check per candidate condition. Each exits through _w.js: HOLDS (0), VIOLATED (1), HARNESS-ERROR (3).
// The checks use the spec text only: the HTTP surface, the rules module's public functions placeFleet and
// fireShot, and a reference model of R-4 written from the spec text. They never import the run's tests.

const fs = require('node:fs');
const path = require('node:path');

const C = {};
const ERRORS = {
  json: { error: 'invalid JSON' },
  shot: { error: 'invalid shot' },
  game: { error: 'unknown game' },
};

function logFile(w) {
  const dir = path.join(w.SCRATCH, 'tmp');
  fs.mkdirSync(dir, { recursive: true });
  const f = path.join(dir, 'remap-' + process.pid + '.log');
  fs.writeFileSync(f, '');
  return f;
}
function readLog(f) {
  return fs.readFileSync(f, 'utf8').trim().split('\n').filter(Boolean).map((l) => JSON.parse(l));
}
// Start the server with PORT set as given, with listen(from) remapped into our range.
async function portCase(w, portEnv, from) {
  const p = await w.freePort();
  const lf = logFile(w);
  const r = w.remapOptions([[from, p]], lf);
  const child = w.spawnServer({ PORT: portEnv, ...r.env }, [], r.options);
  return { child, p, lf };
}
async function expectListensOn(w, portEnv, wanted) {
  const { child, p, lf } = await portCase(w, portEnv, wanted);
  const up = await w.waitUp(child, p, 5000);
  const asked = readLog(lf);
  w.check(asked.some((a) => a.port === wanted && a.host === '127.0.0.1'), 'server did not listen on 127.0.0.1:' + wanted + ' (asked ' + JSON.stringify(asked) + ') ' + child.stderrText);
  w.check(up, 'no connection accepted (remapped ' + wanted + '): ' + child.stderrText);
  await w.stopServer(child);
}
async function expectRefuses(w, portEnv) {
  const { child, p } = await portCase(w, portEnv, 3000);
  const done = await Promise.race([child.exited, w.delay(3500).then(() => null)]);
  const open = await w.connect(p);
  const lsof = child.exitCode === null ? w.listening(child.pid) : '';
  if (done === null) await w.stopServer(child);
  w.check(done !== null, 'PORT=' + portEnv + ' kept running');
  w.check(done.code !== 0 && done.code !== null, 'PORT=' + portEnv + ' exited ' + JSON.stringify(done));
  w.check(!open, 'PORT=' + portEnv + ' left a listener');
  w.check(!lsof.includes('LISTEN'), 'PORT=' + portEnv + ' left ' + lsof);
}

// ---------------- R-1, R-2
C['R-1.1'] = async (w) => {
  const s = await w.startServer();
  const r = await w.req(s.port, 'GET', '/');
  w.check(typeof r.status === 'number', 'no HTTP reply');
  await s.stop();
};
C['R-2.1'] = (w) => expectListensOn(w, '3456', 3456);
C['R-2.2'] = (w) => expectListensOn(w, undefined, 3000);
C['R-2.3'] = (w) => expectListensOn(w, '', 3000);
C['R-2.4'] = (w) => expectRefuses(w, '0');
C['R-2.5'] = (w) => expectRefuses(w, '-1');
C['R-2.6'] = (w) => expectRefuses(w, '65536');
C['R-2.7'] = (w) => expectRefuses(w, 'abc');

// ---------------- R-3 static page
async function getPage(w) {
  const s = await w.startServer();
  const r = await w.req(s.port, 'GET', '/');
  return { s, r };
}
C['R-3.1'] = async (w) => { const { s, r } = await getPage(w); w.eq(r.status, 200, 'GET / status'); await s.stop(); };
C['R-3.2'] = async (w) => { const { s, r } = await getPage(w); w.check(/^text\/html/i.test(r.type), 'content type ' + r.type); await s.stop(); };
C['R-3.3'] = async (w) => {
  const { s, r } = await getPage(w);
  const m = r.text.match(/<title>([^<]*)<\/title>/i);
  w.eq(m && m[1], 'Battleship', 'document title');
  await s.stop();
};
async function pageControls(w) {
  const s = await w.startServer();
  const p = await w.openPage(s.port);
  await p.goto();
  const names = await p.eval(`[...document.querySelectorAll('button,[role=button],input[type=button]')].map((e) => e.getAttribute('aria-label') || e.textContent || '')`);
  p.close();
  await s.stop();
  const parsed = names.map((n) => { const m = n.match(/row\D*(\d+)\D+col\w*\D*(\d+)/i); return m ? [Number(m[1]), Number(m[2])] : null; }).filter(Boolean);
  return parsed;
}
C['R-3.4'] = async (w) => { const c = await pageControls(w); w.eq(c.length, 100, 'fire controls'); };
C['R-3.5'] = async (w) => {
  const c = await pageControls(w);
  const have = new Set(c.map((x) => x.join(',')));
  const missing = [];
  for (let r = 0; r < 10; r += 1) for (let k = 0; k < 10; k += 1) if (!have.has(r + ',' + k)) missing.push([r, k]);
  w.check(missing.length === 0, 'no control labeled for ' + JSON.stringify(missing));
};
C['R-3.6'] = async (w) => {
  const { s, r } = await getPage(w);
  w.check(!/\[\s*\[\s*\d+\s*,\s*\d+\s*\]\s*,\s*\[/.test(r.text), 'HTML embeds an array of coordinate pairs');
  w.check(!/\b(ships|fleet|board)\b\s*[:=]\s*[\[{]/i.test(r.text), 'HTML embeds a ships/fleet/board value');
  await s.stop();
};
C['R-3.7'] = async (w) => {
  const { s, r } = await getPage(w);
  const noTitle = r.text.replace(/<title>[^<]*<\/title>/i, '');
  for (const name of ['Carrier', 'Battleship', 'Cruiser', 'Submarine', 'Destroyer']) {
    w.check(!new RegExp(name, 'i').test(noTitle), 'HTML carries the ship name ' + name);
  }
  await s.stop();
};

// ---------------- R-3 browser behaviour
async function browserCase(w, rule, body) {
  const s = await w.startServer();
  const state = {};
  const p = await w.openPage(s.port, w.realNewRule(s.port, state, rule));
  await p.goto();
  // wait for the page to request and receive its game
  const deadline = Date.now() + 3000;
  while (Date.now() < deadline && !p.log.some((e) => /api\/new/.test(e.url))) await w.delay(50);
  await w.delay(300);
  try { await body(p, state, s); } finally { p.close(); await s.stop(); }
}
C['R-3.8'] = (w) => browserCase(w, null, async (p, state) => {
  w.check(state.id, 'the page never requested a game');
  w.check(await p.clickCell(2, 7), 'no control for row 2 column 7');
  await w.delay(500);
  const posts = p.posts();
  w.eq(posts.length, 1, 'POST /api/fire count');
  w.eq(JSON.parse(posts[0].post), { game: state.id, row: 2, col: 7 }, 'fire body');
});
C['R-3.9'] = (w) => {
  const answers = [{ result: 'sunk', gameOver: false }, { result: 'hit', gameOver: false }, { result: 'miss', gameOver: false }];
  let n = 0;
  const rule = (e) => (e.method === 'POST' && /api\/fire/.test(e.url) ? { status: 200, body: JSON.stringify(answers[n++]) } : 'continue');
  return browserCase(w, rule, async (p) => {
    const want = ['Sunk', 'Hit', 'Miss'];
    for (let i = 0; i < 3; i += 1) {
      w.check(await p.clickCell(0, i), 'no control for row 0 column ' + i);
      await w.delay(400);
      const t = await p.cellText(0, i);
      for (const word of want) {
        const has = new RegExp('\\b' + word + '\\b', 'i').test(t);
        w.check(has === (word === want[i]), 'cell (0,' + i + ') shows "' + t + '" for result ' + answers[i].result);
      }
    }
  });
};
C['R-3.10'] = (w) => {
  const rule = (e) => (e.method === 'POST' && /api\/fire/.test(e.url) ? 'hold' : 'continue');
  return browserCase(w, rule, async (p) => {
    w.check(await p.clickCell(3, 3), 'no control for row 3 column 3');
    await w.delay(500);
    w.eq(p.posts().length, 1, 'fire was sent');
    const t = await p.cellText(3, 3);
    w.check(!/\b(hit|miss|sunk)\b/i.test(t), 'cell shows "' + t + '" while the request has not returned');
  });
};
C['R-3.11'] = (w) => {
  let n = 0;
  const rule = (e) => (e.method === 'POST' && /api\/fire/.test(e.url) ? (n++ === 0 ? 'fail' : 'continue') : 'continue');
  return browserCase(w, rule, async (p) => {
    w.check(await p.clickCell(4, 4), 'no control');
    await w.delay(600);
    const t = await p.cellText(4, 4);
    w.check(!/\b(hit|miss|sunk)\b/i.test(t), 'failed shot left the cell showing "' + t + '"');
    w.check(await p.clickCell(4, 4), 'no control');
    await w.delay(600);
    w.check(p.posts().length === 2, 'after a transport failure the cell was no longer a fire control (' + p.posts().length + ' fires sent)');
  });
};
C['R-3.12'] = (w) => {
  let n = 0;
  const rule = (e) => (e.method === 'POST' && /api\/fire/.test(e.url) ? (n++ === 0 ? 'fail' : 'continue') : 'continue');
  return browserCase(w, rule, async (p) => {
    const err = /(error|fail|not |unable|could ?n|did ?n|wrong|problem|try again)/i;
    const before = await p.bodyText();
    w.check(!err.test(before), 'page already shows an error before the shot: ' + before.slice(0, 80));
    w.check(await p.clickCell(4, 4), 'no control');
    await w.delay(600);
    const after = await p.bodyText();
    w.check(err.test(after), 'no error shown after the transport failure');
  });
};
C['R-3.13'] = async (w) => {
  const s = await w.startServer();
  const p = await w.openPage(s.port);
  await p.goto();
  const deadline = Date.now() + 3000;
  while (Date.now() < deadline && !p.log.some((e) => e.method === 'GET' && /api\/new/.test(e.url))) await w.delay(50);
  const asked = p.log.some((e) => e.method === 'GET' && /api\/new/.test(e.url));
  p.close();
  await s.stop();
  w.check(asked, 'loading / never requested GET /api/new');
};
C['R-3.14'] = async (w) => {
  const s = await w.startServer();
  const p = await w.openPage(s.port, (e) => (/api\/new/.test(e.url) ? 'hold' : 'continue'));
  await p.goto();
  await w.delay(500);
  w.check(await p.clickCell(5, 5), 'no control');
  await w.delay(700);
  const sent = p.posts().length;
  p.close();
  await s.stop();
  w.eq(sent, 0, 'fires sent before the game id existed');
};
C['R-3.15'] = (w) => browserCase(w, null, async (p) => {
  w.check(await p.focusCell(4, 6), 'the cell cannot take keyboard focus');
  await p.pressEnter();
  await w.delay(600);
  w.check(p.posts().length >= 1, 'keyboard activation sent no fire');
});
C['R-3.16'] = async (w) => {
  const s = await w.startServer();
  const id = await w.newGame(s.port); // agent:false => the connection that created the game is closed
  await w.delay(300);
  const r = await w.fire(s.port, id, 0, 0);
  w.eq(r.status, 200, 'fire from a new connection after the creating connection closed');
  await s.stop();
};

// ---------------- R-4 over HTTP
async function withNew(w, fn) {
  const s = await w.startServer();
  try { await fn(s); } finally { await s.stop(); }
}
C['R-4.1'] = (w) => withNew(w, async (s) => { const r = await w.req(s.port, 'GET', '/api/new'); w.eq(r.status, 200, 'GET /api/new status'); });
C['R-4.2'] = (w) => withNew(w, async (s) => { const r = await w.req(s.port, 'GET', '/api/new'); w.check(/^application\/json/i.test(r.type), 'content type ' + r.type); });
C['R-4.3'] = (w) => withNew(w, async (s) => { const r = await w.req(s.port, 'GET', '/api/new'); w.eq(Object.keys(r.json || {}), ['game'], 'keys'); });
C['R-4.4'] = (w) => withNew(w, async (s) => { const r = await w.req(s.port, 'GET', '/api/new'); w.check(r.json && typeof r.json.game === 'string' && r.json.game.length > 0, 'game is ' + JSON.stringify(r.json && r.json.game)); });
C['R-4.5'] = (w) => withNew(w, async (s) => {
  const a = await w.req(s.port, 'GET', '/api/new');
  const b = await w.req(s.port, 'GET', '/api/new');
  w.check(a.json && b.json && a.json.game !== b.json.game, 'two calls gave the same game ' + JSON.stringify(a.json));
});
C['R-4.6'] = (w) => withNew(w, async (s) => { const r = await w.req(s.port, 'POST', '/api/new'); w.eq(r.status, 405, 'POST /api/new status'); });
C['R-4.7'] = async (w) => {
  const s = await w.startServer({ nodeOptions: '--require=' + w.DETID });
  await w.req(s.port, 'POST', '/api/new');
  await w.req(s.port, 'POST', '/api/new');
  for (const guess of ['g-1', 'g-2', 'g-3']) {
    const r = await w.fire(s.port, guess, 0, 0);
    w.eq([r.status, r.json], [404, ERRORS.game], 'fire at ' + guess + ' after POST /api/new');
  }
  await s.stop();
};
C['R-4.8'] = (w) => withNew(w, async (s) => {
  const r = await w.req(s.port, 'GET', '/api/new');
  w.eq(Object.keys(r.json || {}).filter((k) => k !== 'game'), [], 'extra properties');
  w.check(!/ship|board|cell|coord|row|col/i.test(JSON.stringify(r.json)), 'body names a coordinate, ship or board: ' + r.text);
});
C['R-4.9'] = async (w) => {
  const lens = (ships) => ships.map((x) => x.cells.length);
  w.eq(lens(w.rules().placeFleet(w.scripted(w.SEQ_A)).ships), [5, 4, 3, 3, 2], 'ship lengths (oracle draws)');
  const rnd = w.mulberry32(11);
  for (let i = 0; i < 100; i += 1) {
    const g = w.rules().placeFleet(rnd);
    w.eq(lens(g.ships), [5, 4, 3, 3, 2], 'ship lengths (random draws)');
    w.eq(new Set(g.ships.flatMap((x) => x.cells.map((c) => c.join(',')))).size, 17, 'distinct cells');
  }
  await withNew(w, async (s) => {
    const id = await w.newGame(s.port);
    const { first } = await w.sweep(s.port, id, { noSecond: true });
    const f = w.sweepFacts(first);
    w.eq([f.ship, f.sunk], [17, 5], 'sweep hit-or-sunk and sunk counts');
  });
};
C['R-4.10'] = async (w) => {
  const rnd = w.mulberry32(5);
  for (let i = 0; i < 20; i += 1) {
    const labels = w.rules().placeFleet(rnd).ships.map((x) => x.label).sort();
    w.eq(labels, ['Battleship', 'Carrier', 'Cruiser', 'Destroyer', 'Submarine'], 'labels');
  }
};
function randomDraws(w, seed, n) {
  const base = w.mulberry32(seed);
  let calls = 0;
  const f = () => {
    calls += 1;
    if (calls > 20000) throw new w.Violation('placeFleet did not settle');
    const u = base();
    if (u < 0.12) return 0.999999;
    if (u < 0.24) return 0;
    if (u < 0.30) return 0.5;
    return base();
  };
  return f;
}
C['R-4.11'] = async (w) => {
  for (let seed = 1; seed <= 300; seed += 1) {
    for (const ship of w.rules().placeFleet(randomDraws(w, seed)).ships) {
      const cs = ship.cells;
      const sameRow = cs.every((c) => c[0] === cs[0][0]);
      const sameCol = cs.every((c) => c[1] === cs[0][1]);
      w.check(sameRow || sameCol, ship.label + ' is not axis-aligned: ' + JSON.stringify(cs));
      const axis = sameRow ? 1 : 0;
      const sorted = cs.map((c) => c[axis]).sort((a, b) => a - b);
      w.check(sorted.every((v, i) => i === 0 || v === sorted[i - 1] + 1), ship.label + ' is not contiguous: ' + JSON.stringify(cs));
    }
  }
};
C['R-4.12'] = async (w) => {
  for (let seed = 1; seed <= 500; seed += 1) {
    for (const ship of w.rules().placeFleet(randomDraws(w, seed)).ships) {
      for (const [r, c] of ship.cells) w.check(r >= 0 && r <= 9 && c >= 0 && c <= 9, ship.label + ' has a cell outside the grid: ' + r + ',' + c);
    }
  }
};
C['R-4.13'] = async (w) => {
  for (let seed = 1; seed <= 500; seed += 1) {
    const cells = w.rules().placeFleet(randomDraws(w, seed)).ships.flatMap((x) => x.cells.map((c) => c.join(',')));
    w.eq([cells.length, new Set(cells).size], [17, 17], 'cells and distinct cells (seed ' + seed + ')');
  }
};
C['R-4.14'] = async (w) => {
  const sc = w.scripted(w.SEQ_A);
  const ships = w.rules().placeFleet(sc).ships;
  w.eq(Object.fromEntries(ships.map((x) => [x.label, x.cells])), w.LAYOUT, 'layout with touching ships (Carrier ends beside the Battleship)');
  w.eq(sc.used(), 15, 'draws used');
};
C['R-4.16'] = async (w) => {
  const draws = [0, 0, 0, 0, 0.1, 0, 0, 0.2, 0, 0, 0.3, 0, 0, 0.4, 0];
  const ships = w.rules().placeFleet(w.scripted(draws)).ships;
  const row = Object.fromEntries(ships.map((x) => [x.label, x.cells[0][0]]));
  w.eq(row, { Carrier: 0, Battleship: 1, Cruiser: 2, Submarine: 3, Destroyer: 4 }, 'row each ship took from the draws in label order');
};
C['R-4.17'] = (w) => w.compareToRef([0, 0.3, 0.6, 0, 0.1, 0.2, 0, 0.5, 0.1, 0, 0.7, 0.1, 0, 0.9, 0.1], 'draw order orientation, row, column');
C['R-4.18'] = async (w) => {
  const tail = [0, 0.6, 0, 0, 0.7, 0, 0, 0.8, 0, 0, 0.9, 0];
  const below = w.rules().placeFleet(w.scripted([0.4999999, 0, 0, ...tail])).ships[0].cells;
  w.eq(below, [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]], 'a draw just below 0.5 is horizontal');
  const exact = w.rules().placeFleet(w.scripted([0.5, 0, 0, ...tail])).ships[0].cells;
  w.eq(exact, [[0, 0], [1, 0], [2, 0], [3, 0], [4, 0]], 'a draw of exactly 0.5 is vertical');
};
C['R-4.19'] = (w) => w.compareToRef([0, 0.99, 0, 0, 0, 0, 0, 0.1, 0, 0, 0.2, 0, 0, 0.3, 0], 'horizontal start row up to 9');
C['R-4.20'] = (w) => w.compareToRef([0.5, 0.99, 0, 0, 0, 0, 0, 0.1, 0, 0, 0.2, 0, 0, 0.3, 0], 'vertical start row up to 10 - length');
C['R-4.21'] = (w) => w.compareToRef([0, 0, 0.99, 0, 0.1, 0, 0, 0.2, 0, 0, 0.3, 0, 0, 0.4, 0], 'horizontal start column up to 10 - length');
C['R-4.22'] = (w) => w.compareToRef([0.5, 0, 0.99, 0, 0.5, 0, 0, 0.6, 0, 0, 0.7, 0, 0, 0.8, 0], 'vertical start column up to 9');
C['R-4.23'] = (w) => w.compareToRef([0, 0.2, 0.4, 0, 0.5, 0, 0, 0.6, 0, 0, 0.7, 0, 0, 0.8, 0], 'start = floor(draw * (max + 1))');
C['R-4.24'] = (w) => w.compareToRef([0, 0.3, 0.2, 0, 0.5, 0, 0, 0.6, 0, 0, 0.7, 0, 0, 0.8, 0], 'horizontal cells toward increasing column');
C['R-4.25'] = (w) => w.compareToRef([0.5, 0.2, 0.3, 0, 0.6, 0, 0, 0.7, 0, 0, 0.8, 0, 0, 0.9, 0], 'vertical cells toward increasing row');
C['R-4.26'] = async (w) => {
  const sc = w.scripted(w.SEQ_B);
  const ships = w.rules().placeFleet(sc).ships;
  w.eq(Object.fromEntries(ships.map((x) => [x.label, x.cells])), w.LAYOUT, 'layout when the first Battleship attempt overlaps');
  w.eq(sc.used(), 18, 'draws used (the whole overlapping attempt of three draws is discarded)');
};
C['R-4.15'] = (w) => withNew(w, async (s) => {
  const r = await w.req(s.port, 'GET', '/api/new');
  w.eq(r.status, 200, 'GET /api/new with no body');
});
C['R-4.27'] = (w) => withNew(w, async (s) => {
  const a = await w.newGame(s.port);
  const b = await w.newGame(s.port);
  const sa = await w.sweep(s.port, a, { noSecond: true });
  const fa = w.sweepFacts(sa.first);
  w.eq([fa.ship, fa.overBad.length], [17, 0], 'game A sweep');
  const sb = await w.sweep(s.port, b, { noSecond: true });
  const fb = w.sweepFacts(sb.first);
  w.eq([fb.ship, fb.overBad.length], [17, 0], 'game B sweep after game A was played out');
});
C['R-4.28'] = (w) => withNew(w, async (s) => {
  const g = await w.newGame(s.port);
  const { first, second } = await w.sweep(s.port, g);
  const f = w.sweepFacts(first);
  w.eq([f.ship, f.sunk, f.overBad.length], [17, 5, 0], 'one game played over many requests');
  w.check(second.every((r, i) => r.json && r.json.result === first[i].json.result && r.json.gameOver === true), 'second pass differs from the first');
});
C['R-4.29'] = async (w) => {
  const port = await w.freePort();
  const first = await w.startServer({ port });
  const id = await w.newGame(port);
  const live = await w.fire(port, id, 0, 0);
  w.eq(live.status, 200, 'game is live before the restart');
  await first.stop();
  const second = await w.startServer({ port });
  const r = await w.fire(port, id, 0, 0);
  w.eq([r.status, r.json], [404, ERRORS.game], 'old game after restart');
  await second.stop();
};

// ---------------- R-5 over the rules module (seeded board) and over HTTP (random board)
function modAll(w, fn) { fn(w.rules()); }
function freshGame(w) { return w.seeded(); }
function shootAll(w, game, cells) {
  return cells.map(([r, c]) => w.seededFire(game, r, c));
}
function httpSweep(w, fn) {
  return withNew(w, async (s) => {
    const id = await w.newGame(s.port);
    const sw = await w.sweep(s.port, id);
    await fn(sw, w.sweepFacts(sw.first), s, id);
  });
}
C['R-5.1'] = async (w) => {
  await httpSweep(w, (sw) => {
    for (const r of [...sw.first, ...sw.second]) w.check(r.json && ['miss', 'hit', 'sunk'].includes(r.json.result), 'result ' + JSON.stringify(r.json));
  });
  const g = freshGame(w);
  for (const [r, c] of w.ALL_SHIP_CELLS) w.check(['hit', 'sunk'].includes(w.seededFire(g, r, c).result), 'module result');
};
C['R-5.2'] = (w) => httpSweep(w, (sw) => {
  for (const r of [...sw.first, ...sw.second]) w.check(r.json && typeof r.json.gameOver === 'boolean', 'gameOver is ' + JSON.stringify(r.json));
});
C['R-5.3'] = async (w) => {
  for (const name of w.SHIP_ORDER) {
    const cells = w.LAYOUT[name];
    for (let k = 0; k < cells.length - 1; k += 1) {
      const g = freshGame(w);
      shootAll(w, g, cells.slice(0, k));
      w.eq(w.seededFire(g, ...cells[k]), { result: 'hit', gameOver: false }, name + ' cell ' + k + ' while a cell is still unshot');
    }
  }
  await httpSweep(w, (sw, f) => w.eq(f.hit, 12, 'hit responses in a sweep'));
};
C['R-5.4'] = async (w) => {
  for (const name of w.SHIP_ORDER) {
    const g = freshGame(w);
    const cells = w.LAYOUT[name];
    const res = shootAll(w, g, cells).map((x) => x.result);
    w.eq(res, cells.map((_, i) => (i === cells.length - 1 ? 'sunk' : 'hit')), name + ' results');
  }
  await httpSweep(w, (sw, f) => w.eq(f.sunk, 5, 'sunk responses in a sweep'));
};
C['R-5.5'] = async (w) => {
  const g = freshGame(w);
  for (const [r, c] of [[1, 1], [9, 9], [8, 8], [3, 3], [5, 9], [9, 0], [0, 9], [7, 7], [4, 8]]) w.eq(w.seededFire(g, r, c), { result: 'miss', gameOver: false }, 'water cell ' + r + ',' + c);
  await httpSweep(w, (sw, f) => w.eq(f.miss, 83, 'miss responses in a sweep'));
};
C['R-5.6'] = async (w) => {
  for (let seed = 1; seed <= 20; seed += 1) {
    const rnd = w.mulberry32(seed);
    const cells = [...w.ALL_SHIP_CELLS].sort(() => rnd() - 0.5);
    const g = freshGame(w);
    const res = shootAll(w, g, cells);
    res.slice(0, -1).forEach((x, i) => w.eq(x.gameOver, false, 'gameOver after ' + (i + 1) + ' of 17 ship cells'));
  }
  await httpSweep(w, (sw, f) => w.check(sw.first.slice(0, f.seventeenth).every((r) => r.json.gameOver === false), 'gameOver true before the 17th ship cell'));
};
C['R-5.7'] = async (w) => {
  for (let seed = 1; seed <= 20; seed += 1) {
    const rnd = w.mulberry32(seed);
    const cells = [...w.ALL_SHIP_CELLS].sort(() => rnd() - 0.5);
    const g = freshGame(w);
    const res = shootAll(w, g, cells);
    w.eq(res[16].gameOver, true, 'gameOver on the shot that takes the 17th ship cell');
  }
  await httpSweep(w, (sw, f) => w.eq(sw.first[f.seventeenth].json.gameOver, true, 'gameOver on the response that brings the count to 17'));
};
C['R-5.8'] = async (w) => {
  const g = freshGame(w);
  shootAll(w, g, w.ALL_SHIP_CELLS);
  for (let r = 0; r < 10; r += 1) for (let c = 0; c < 10; c += 1) w.eq(w.seededFire(g, r, c).gameOver, true, 'gameOver after the game is over at ' + r + ',' + c);
  await httpSweep(w, (sw, f) => {
    w.check(sw.first.slice(f.seventeenth).every((r) => r.json.gameOver === true), 'gameOver went back to false in the first sweep');
    w.check(sw.second.every((r) => r.json.gameOver === true), 'gameOver false in the second sweep');
  });
};
C['R-5.9'] = async (w) => {
  const g = freshGame(w);
  for (let i = 0; i < 6; i += 1) w.eq(w.seededFire(g, 0, 0), { result: 'hit', gameOver: false }, 'repeat of (0,0)');
  w.eq(shootAll(w, g, [[0, 1], [0, 2], [0, 3]]).map((x) => x.result), ['hit', 'hit', 'hit'], 'rest of the Carrier after repeats of its first cell');
  w.eq(w.seededFire(g, 0, 4), { result: 'sunk', gameOver: false }, 'the Carrier sinks only on its last cell');
  await withNew(w, async (s) => {
    const id = await w.newGame(s.port);
    const first = [];
    for (let r = 0; r < 10; r += 1) for (let c = 0; c < 10; c += 1) {
      let firstRes;
      for (let k = 0; k < 5; k += 1) { const x = await w.fire(s.port, id, r, c); if (k === 0) firstRes = x; }
      first.push(firstRes);
    }
    const f = w.sweepFacts(first);
    w.eq([f.ship, f.sunk, f.hit, f.overBad.length], [17, 5, 12, 0], 'sweep with every cell fired five times in a row');
  });
};
C['R-5.10'] = async (w) => {
  const g = freshGame(w);
  shootAll(w, g, w.LAYOUT.Carrier);
  w.eq(w.seededFire(g, 0, 0).result, 'hit', 'repeat of the Carrier first cell after the Carrier sank');
  w.eq(w.seededFire(g, 0, 4).result, 'sunk', 'repeat of the Carrier last cell');
  w.eq(w.seededFire(g, 9, 9).result, 'miss', 'first water shot');
  w.eq(w.seededFire(g, 9, 9).result, 'miss', 'repeat water');
  await httpSweep(w, (sw) => w.check(sw.second.every((r, i) => r.json.result === sw.first[i].json.result), 'second pass returns a different result than the first shot'));
};
C['R-5.11'] = async (w) => {
  const g = freshGame(w);
  w.eq(w.seededFire(g, 0, 0).gameOver, false, 'first shot gameOver');
  shootAll(w, g, w.ALL_SHIP_CELLS);
  w.eq(w.seededFire(g, 0, 0), { result: 'hit', gameOver: true }, 'repeat of the first shot after the game is over');
  w.eq(w.seededFire(g, 6, 1), { result: 'sunk', gameOver: true }, 'repeat of the last ship cell');
  await httpSweep(w, (sw) => w.check(sw.second.every((r) => r.json.gameOver === true), 'repeat shot reported a stale gameOver'));
};
C['R-5.12'] = async (w) => {
  const g = freshGame(w);
  shootAll(w, g, w.ALL_SHIP_CELLS);
  for (const [r, c] of [[8, 8], [1, 1], [9, 0], [5, 5]]) w.eq(w.seededFire(g, r, c), { result: 'miss', gameOver: true }, 'unshot cell ' + r + ',' + c + ' after the game is over');
  await httpSweep(w, (sw, f) => w.check(sw.first.slice(f.seventeenth + 1).every((r) => r.json.result === 'miss'), 'an unshot cell after the game is over was not a miss'));
};
// errors
async function badRequests(w, s, id, list) {
  for (const body of list) await w.req(s.port, 'POST', '/api/fire', body);
  void id;
}
C['R-5.13'] = (w) => withNew(w, async (s) => {
  const id = await w.newGame(s.port);
  for (let r = 0; r < 10; r += 1) for (let c = 0; c < 10; c += 1) {
    const x = await w.fire(s.port, id, r + 0.5, c);
    w.eq(x.status, 400, 'fire at non-integer row');
    const y = await w.fire(s.port, id, r, c + 0.5);
    w.eq(y.status, 400, 'fire at non-integer col');
  }
  for (const [r, c] of [[10, 0], [-1, 0], [0, 10], [0, -1], [12, 3], [3, 12]]) {
    const z = await w.fire(s.port, id, r, c);
    w.eq(z.status, 400, 'fire out of range ' + r + ',' + c);
  }
  const { first } = await w.sweep(s.port, id, { noSecond: true });
  const f = w.sweepFacts(first);
  w.eq([f.ship, f.sunk, f.overBad.length], [17, 5, 0], 'sweep after many erroring requests');
});
C['R-5.14'] = (w) => withNew(w, async (s) => {
  const id = await w.newGame(s.port);
  const sw = await w.sweep(s.port, id, { noSecond: true });
  const f = w.sweepFacts(sw.first);
  w.eq([f.ship, sw.first[99].json.gameOver], [17, true], 'game over before the errors');
  for (const body of [{ game: id, row: 10, col: 0 }, 'not-json', { game: 'missing-game', row: 0, col: 0 }, { game: id, row: 'x', col: 0 }]) {
    await w.req(s.port, 'POST', '/api/fire', body);
    const probe = await w.fire(s.port, id, 0, 0);
    w.eq(probe.json && probe.json.gameOver, true, 'gameOver after an erroring request');
    const probe2 = await w.fire(s.port, id, 9, 9);
    w.eq(probe2.json && probe2.json.gameOver, true, 'gameOver after an erroring request (second probe)');
  }
});
async function errorCase(w, sendBody, status, expected, mk) {
  await withNew(w, async (s) => {
    const id = await w.newGame(s.port);
    const body = mk ? mk(id) : sendBody;
    const r = await w.req(s.port, 'POST', '/api/fire', body);
    w.eq([r.status, r.json], [status, expected], 'response to ' + (typeof body === 'string' ? body : JSON.stringify(body)));
  });
}
C['R-5.15'] = (w) => errorCase(w, { game: 'missing-game', row: 0, col: 0 }, 404, ERRORS.game);
C['R-5.16'] = (w) => errorCase(w, 'not-json', 400, ERRORS.json);
C['R-5.17'] = (w) => errorCase(w, 'null', 400, ERRORS.json);
C['R-5.18'] = (w) => errorCase(w, '[]', 400, ERRORS.json);
C['R-5.19'] = async (w) => { await errorCase(w, '1', 400, ERRORS.json); await errorCase(w, '"x"', 400, ERRORS.json); await errorCase(w, 'true', 400, ERRORS.json); };
C['R-5.20'] = (w) => errorCase(w, { row: 0, col: 0 }, 400, ERRORS.shot);
C['R-5.21'] = (w) => errorCase(w, null, 400, ERRORS.shot, (id) => ({ game: id, col: 0 }));
C['R-5.22'] = (w) => errorCase(w, null, 400, ERRORS.shot, (id) => ({ game: id, row: 0 }));
C['R-5.23'] = (w) => errorCase(w, { game: 1, row: 0, col: 0 }, 400, ERRORS.shot);
C['R-5.24'] = async (w) => {
  await errorCase(w, null, 400, ERRORS.shot, (id) => ({ game: id, row: 1.5, col: 0 }));
  await errorCase(w, null, 400, ERRORS.shot, (id) => ({ game: id, row: '1', col: 0 }));
};
C['R-5.25'] = async (w) => {
  await errorCase(w, null, 400, ERRORS.shot, (id) => ({ game: id, row: 0, col: 1.5 }));
  await errorCase(w, null, 400, ERRORS.shot, (id) => ({ game: id, row: 0, col: '1' }));
};
C['R-5.26'] = (w) => errorCase(w, null, 400, ERRORS.shot, (id) => ({ game: id, row: 10, col: 0 }));
C['R-5.27'] = (w) => errorCase(w, null, 400, ERRORS.shot, (id) => ({ game: id, row: -1, col: 0 }));
C['R-5.28'] = (w) => errorCase(w, null, 400, ERRORS.shot, (id) => ({ game: id, row: 0, col: 10 }));
C['R-5.29'] = (w) => errorCase(w, null, 400, ERRORS.shot, (id) => ({ game: id, row: 0, col: -1 }));
C['R-5.30'] = (w) => withNew(w, async (s) => {
  const id = await w.newGame(s.port);
  for (const [r, c] of [[9, 0], [0, 9], [9, 9], [9, 5], [5, 9]]) w.eq((await w.fire(s.port, id, r, c)).status, 200, 'fire at ' + r + ',' + c);
});
C['R-5.31'] = (w) => withNew(w, async (s) => {
  const id = await w.newGame(s.port);
  for (const [r, c] of [[0, 0], [0, 5], [5, 0], [0, 9], [9, 0]]) w.eq((await w.fire(s.port, id, r, c)).status, 200, 'fire at ' + r + ',' + c);
});
C['R-5.32'] = (w) => httpSweep(w, (sw) => {
  for (const r of [...sw.first, ...sw.second]) w.eq(Object.keys(r.json || {}).sort(), ['gameOver', 'result'], 'keys of a fire body');
});
C['R-5.33'] = (w) => httpSweep(w, (sw) => {
  for (const r of [...sw.first, ...sw.second]) w.check(!/\[|ship|cell|coord|row|col|label/i.test(r.text), 'fire body names ship coordinates: ' + r.text);
});
C['R-5.34'] = (w) => httpSweep(w, (sw) => {
  for (const r of [...sw.first, ...sw.second]) w.eq(r.status, 200, 'fire status');
});
C['R-5.35'] = (w) => httpSweep(w, (sw) => {
  for (const r of [...sw.first, ...sw.second]) w.check(/^application\/json/i.test(r.type), 'fire content type ' + r.type);
});
C['R-5.36'] = async (w) => {
  const g = freshGame(w);
  for (const [r, c] of [[10, 0], [-1, 0], [0, -1], [0, 10], [10, 10], [-3, 4], [4, 11], [1.5, 1]]) {
    w.eq(w.seededFire(g, r, c), undefined, 'fireShot with ' + r + ',' + c);
  }
  w.eq(w.seededFire(g, 0, 0), { result: 'hit', gameOver: false }, 'first shot at (0,0) after out-of-range shots');
  shootAll(w, g, w.ALL_SHIP_CELLS.slice(1));
  w.eq(w.seededFire(g, 10, 0), undefined, 'fireShot row 10 after the game is over');
  w.eq(w.seededFire(g, 8, 8), { result: 'miss', gameOver: true }, '(8,8) after the row 10 shot');
};

void modAll;
void badRequests;
module.exports = C;
