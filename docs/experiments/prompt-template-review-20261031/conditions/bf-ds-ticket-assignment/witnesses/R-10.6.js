'use strict';
// Witness R-10.6: The weekly report still counts by status and priority with assigned tickets.
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

  const r = L.weekly(f);
  check(r.status === 0, 'weekly report exits 0: ' + r.stderr);
  const rep = JSON.parse(r.stdout);
  eq(rep.total, 3, 'total');
  eq(rep.byStatus.open, 2, 'open count');
  eq(rep.byStatus.in_progress, 1, 'in_progress count');
  eq([rep.byPriority.urgent, rep.byPriority.low, rep.byPriority.normal], [1, 1, 1], 'priority counts');
});
