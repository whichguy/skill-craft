'use strict';
// Witness R-2.1: PUT /tickets/:id/assignee answers 200 with the changed ticket.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const r = await L.assign(s.api, t.id, 'dana');
  check(r.status === 200, 'PUT answers 200, got ' + r.status);
  check(r.body && r.body.id === t.id && r.body.assignee === 'dana', 'the response body is the changed ticket (assignee dana)');
});
