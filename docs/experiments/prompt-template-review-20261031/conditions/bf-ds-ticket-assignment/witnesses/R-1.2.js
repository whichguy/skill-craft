'use strict';
// Witness R-1.2: GET /tickets/:id of an unassigned ticket carries assignee: null.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const r = await s.api.get('/tickets/' + t.id);
  check(r.status === 200 && 'assignee' in r.body && r.body.assignee === null, 'GET /tickets/:id carries assignee: null');
});
