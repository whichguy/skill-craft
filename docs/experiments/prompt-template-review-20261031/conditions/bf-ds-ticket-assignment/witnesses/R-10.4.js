'use strict';
// Witness R-10.4: list --raw prints an empty fifth cell for an unassigned ticket.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const f = L.tmpfile('d.json');
  const s = await L.startService({ dataFile: f });
  const a = await L.ticket(s.api, { title: 'Alpha ticket', priority: 'urgent' });
  const b = await L.ticket(s.api, { title: 'Bravo ticket', priority: 'low' });
  const c = await L.ticket(s.api, { title: 'Charlie ticket', priority: 'normal' });
  await L.assign(s.api, a.id, 'dana');
  await L.assign(s.api, c.id, 'erin');
  await L.advance(s.api, c.id, 'in_progress');
  await s.stop();

  const out = L.cli(['list', '--raw'], f);
  check(out.status === 0, 'list --raw exits 0');
  const rows = Object.fromEntries(out.stdout.split('\n').filter(Boolean).map((l) => l.split('\t')).map((c) => [c[3], c]));

  const cells = rows['Bravo ticket'];
  check(cells && cells.length === 5 && cells[4] === '', 'unassigned raw line has an empty fifth cell, got ' + JSON.stringify(cells));
});
