'use strict';
// Witness R-1.3: Items from GET /tickets carry assignee (null when unassigned).
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  await L.ticket(s.api);
  await L.ticket(s.api, { title: 'Second' });
  const r = await s.api.get('/tickets');
  check(r.status === 200 && r.body.items.length === 2, 'two items');
  check(r.body.items.every((i) => 'assignee' in i && i.assignee === null), 'every listed item carries assignee: null');
});
