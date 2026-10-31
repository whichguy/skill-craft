'use strict';
// Witness R-6.1: Assigning the current agent answers 200 with the unchanged ticket.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const before = (await s.api.get('/tickets/' + t.id)).body;
  await sleep(20);
  const r = await L.assign(s.api, t.id, 'dana');
  check(r.status === 200, 'same-agent assignment answers 200, got ' + r.status);
  eq(r.body, before, 'the ticket is unchanged');
});
