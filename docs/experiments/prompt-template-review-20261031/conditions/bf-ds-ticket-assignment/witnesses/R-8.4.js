'use strict';
// Witness R-8.4: A notice pending for A does not swallow B's notice.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  await L.assign(s.api, t.id, 'erin');
  const e = (await L.events(s.api)).filter((x) => x.type === 'ticket.assigned');
  eq(e.map((x) => x.to).sort(), ['dana', 'erin'], 'a notice for each agent');
});
