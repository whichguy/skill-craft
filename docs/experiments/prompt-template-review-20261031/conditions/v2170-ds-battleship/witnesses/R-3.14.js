'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(3) });
  try {
    const r = await L.getJson(s.port, '/api/new');
    check(r.status === 200 && r.json, 'no JSON from /api/new');
    for (const [k, v] of Object.entries(r.json)) check(typeof v === 'string' || typeof v === 'number', 'field ' + k + ' is a ' + typeof v + ' (possible ship data)');
    check(!/carrier|battleship|cruiser|submarine|destroyer|cells|fleet|"row"|"col"/i.test(r.text), 'body mentions ship data: ' + r.text.slice(0, 200));
  } finally { await s.close(); }
});
