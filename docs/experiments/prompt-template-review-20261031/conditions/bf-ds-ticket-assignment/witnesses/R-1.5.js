'use strict';
// Witness R-1.5: POST /tickets/:id/transition returns a ticket carrying assignee.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  let r = await s.api.post('/tickets/' + t.id + '/transition', { to: 'in_progress' });
  check(r.status === 200 && 'assignee' in r.body && r.body.assignee === null, 'transition response carries assignee: null');
  await L.assign(s.api, t.id, 'dana');
  r = await s.api.post('/tickets/' + t.id + '/transition', { to: 'resolved' });
  eq(r.body.assignee, 'dana', 'transition response carries the name once assigned');
});
