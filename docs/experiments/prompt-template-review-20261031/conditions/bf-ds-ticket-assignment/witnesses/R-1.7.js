'use strict';
// Witness R-1.7: After an assignment GET /tickets/:id returns the agent name.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const r = await s.api.get('/tickets/' + t.id);
  eq(r.body.assignee, 'dana', 'GET /tickets/:id after assignment');
});
