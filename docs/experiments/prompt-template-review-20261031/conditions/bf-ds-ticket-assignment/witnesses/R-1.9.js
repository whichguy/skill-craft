'use strict';
// Witness R-1.9: After assign then unassign GET /tickets/:id returns null.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  await L.assign(s.api, t.id, null);
  const r = await s.api.get('/tickets/' + t.id);
  check(r.body.assignee === null, 'GET /tickets/:id after unassignment is null, got ' + JSON.stringify(r.body.assignee));
});
