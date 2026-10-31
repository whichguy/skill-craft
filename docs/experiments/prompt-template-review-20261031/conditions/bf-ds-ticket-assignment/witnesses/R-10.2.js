'use strict';
// Witness R-10.2: The list table shows - for an unassigned ticket.
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

  const out = L.cli(['list'], f);
  check(out.status === 0, 'list exits 0');
  const lines = out.stdout.split('\n').filter(Boolean);
  const header = lines[0];
  const start = header.indexOf('ASSIGNEE');
  check(start >= 0, 'the header has an ASSIGNEE column: ' + header);
  const next = header.indexOf('REQUESTER');
  const cell = (title) => lines.find((l) => l.includes(title)).slice(start, next).trim();

  eq(cell('Bravo ticket'), '-', 'ASSIGNEE cell of the unassigned ticket');
});
