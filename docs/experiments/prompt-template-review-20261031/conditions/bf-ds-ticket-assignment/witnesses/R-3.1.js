'use strict';
// Witness R-3.1: {assignee:null} answers 200 with the ticket whose assignee is null.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const r = await L.assign(s.api, t.id, null);
  check(r.status === 200, 'unassign answers 200, got ' + r.status);
  check(r.body && r.body.id === t.id && r.body.assignee === null, 'the response is the ticket with assignee null, got ' + JSON.stringify(r.body && r.body.assignee));
});
