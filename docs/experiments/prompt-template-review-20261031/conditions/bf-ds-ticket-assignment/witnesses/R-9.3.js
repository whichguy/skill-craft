'use strict';
// Witness R-9.3: A valid agent with no tickets lists nothing.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const a = await L.ticket(s.api, { title: 'A' });
  await L.ticket(s.api, { title: 'B' });
  await L.assign(s.api, a.id, 'dana');
  const r = await s.api.get('/tickets?assignee=zed');
  check(r.status === 200, 'answers 200');
  eq(r.body.items.length, 0, 'no items for an agent with no tickets');
});
