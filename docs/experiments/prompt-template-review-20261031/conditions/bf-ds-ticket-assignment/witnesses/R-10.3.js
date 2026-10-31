'use strict';
// Witness R-10.3: list --raw appends the agent name as the fifth column.
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

  eq(rows['Alpha ticket'] && rows['Alpha ticket'][4], 'dana', 'fifth column of the assigned ticket');
  eq(rows['Charlie ticket'] && rows['Charlie ticket'][4], 'erin', 'fifth column of the second assigned ticket');
});
