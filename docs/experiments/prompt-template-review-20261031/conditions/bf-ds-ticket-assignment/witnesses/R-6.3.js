'use strict';
// Witness R-6.3: Assigning the current agent enqueues no notification.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const before = await L.outbox(s.api);
  const r = await L.assign(s.api, t.id, 'dana');
  check(r.status === 200, 'answers 200');
  eq(await L.outbox(s.api), before, 'outbox unchanged');
});
