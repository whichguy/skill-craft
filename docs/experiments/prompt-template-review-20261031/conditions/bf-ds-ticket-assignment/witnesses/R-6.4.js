'use strict';
// Witness R-6.4: Assigning the current agent leaves updated unchanged.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const a = await L.assign(s.api, t.id, 'dana');
  await sleep(30);
  const r = await L.assign(s.api, t.id, 'dana');
  eq(r.body.updated, a.body.updated, 'updated in the response');
  const g = await s.api.get('/tickets/' + t.id);
  eq(g.body.updated, a.body.updated, 'updated on GET');
});
