'use strict';
// Witness R-1.8: After an assignment the item in GET /tickets returns the agent name.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const r = await s.api.get('/tickets');
  const item = r.body.items.find((i) => i.id === t.id);
  eq(item && item.assignee, 'dana', 'GET /tickets item after assignment');
});
