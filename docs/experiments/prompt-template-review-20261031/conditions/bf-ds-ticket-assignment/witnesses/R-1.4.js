'use strict';
// Witness R-1.4: PATCH /tickets/:id returns a ticket carrying assignee (null, then the name).
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  let r = await s.api.patch('/tickets/' + t.id, { title: 'New title' });
  check(r.status === 200 && 'assignee' in r.body && r.body.assignee === null, 'PATCH response carries assignee: null');
  await L.assign(s.api, t.id, 'dana');
  r = await s.api.patch('/tickets/' + t.id, { priority: 'high' });
  eq(r.body.assignee, 'dana', 'PATCH response carries the name once assigned');
});
