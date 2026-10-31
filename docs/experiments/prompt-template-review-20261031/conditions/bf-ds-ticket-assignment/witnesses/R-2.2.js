'use strict';
// Witness R-2.2: After the PUT, GET /tickets/:id agrees (the store changed).
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const r = await L.assign(s.api, t.id, 'dana');
  check(r.status === 200, 'PUT answers 200');
  const g = await s.api.get('/tickets/' + t.id);
  eq(g.body.assignee, 'dana', 'GET after PUT');
});
