'use strict';
// Witness R-8.2: The event is addressed to the agent.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const e = (await L.events(s.api)).filter((x) => x.type === 'ticket.assigned');
  eq(e.map((x) => x.to), ['dana'], 'event addressee');
});
