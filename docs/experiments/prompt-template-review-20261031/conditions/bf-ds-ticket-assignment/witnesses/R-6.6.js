'use strict';
// Witness R-6.6: Unassigning an unassigned ticket leaves updated unchanged.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await sleep(30);
  const r = await L.assign(s.api, t.id, null);
  check(r.status === 200, 'answers 200');
  eq(r.body.updated, t.updated, 'updated in the response');
  const g = await s.api.get('/tickets/' + t.id);
  eq(g.body.updated, t.updated, 'updated on GET');
});
