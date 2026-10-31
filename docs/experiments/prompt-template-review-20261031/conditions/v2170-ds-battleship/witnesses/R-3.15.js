'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(11) });
  try {
    const fleet = L.fleetOf(11);
    const g = await L.getJson(s.port, '/api/new');
    check(g.status === 200, '/api/new failed');
    const r = await L.getJson(s.port, '/');
    check(!/carrier|submarine|destroyer|data-ship|ship-cell|occupied/i.test(r.text), 'the page names ships');
    for (const ship of fleet) for (const c of ship.cells) {
      const pats = ['"row":' + c.row + ',"col":' + c.col, '"col":' + c.col + ',"row":' + c.row, 'row: ' + c.row + ', col: ' + c.col, '[' + c.row + ',' + c.col + ']', '[' + c.row + ', ' + c.col + ']'];
      for (const p of pats) check(!r.text.includes(p), 'the page embeds ship cell ' + p);
    }
  } finally { await s.close(); }
});
