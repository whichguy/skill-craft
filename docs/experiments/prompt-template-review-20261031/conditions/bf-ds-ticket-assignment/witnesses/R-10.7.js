'use strict';
// Witness R-10.7: show lists assignee among the ticket's fields.
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

  const out = L.cli(['show', a.id], f);
  check(out.status === 0, 'show exits 0');
  check(/^\s*assignee\s+dana\s*$/m.test(out.stdout), 'show prints an assignee field with dana, got:\n' + out.stdout);
});
