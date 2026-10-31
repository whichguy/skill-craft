'use strict';
// Witness R-2.3: The ticket's updated moves to the change time.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await sleep(30);
  const r = await L.assign(s.api, t.id, 'dana');
  check(r.status === 200 && Date.parse(r.body.updated) > Date.parse(t.updated), 'updated moved forward: ' + t.updated + ' -> ' + (r.body && r.body.updated));
  const g = await s.api.get('/tickets/' + t.id);
  eq(g.body.updated, r.body.updated, 'GET agrees on updated');
});
