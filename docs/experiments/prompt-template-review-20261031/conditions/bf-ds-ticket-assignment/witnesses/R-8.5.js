'use strict';
// Witness R-8.5: A->B->A adds no third event while A's notice is pending.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  await L.assign(s.api, t.id, 'erin');
  await L.assign(s.api, t.id, 'dana');
  const e = (await L.events(s.api)).filter((x) => x.type === 'ticket.assigned');
  eq(e.map((x) => x.to).sort(), ['dana', 'erin'], 'exactly one notice per agent');
});
