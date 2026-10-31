'use strict';
// Witness R-8.3: The event carries the ticket id and its title.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api, { title: 'Broken monitor' });
  await L.assign(s.api, t.id, 'dana');
  const e = (await L.events(s.api)).find((x) => x.type === 'ticket.assigned');
  check(e && e.ticket === t.id, 'event carries the ticket id');
  check(e && e.data && e.data.title === 'Broken monitor', 'event carries the ticket title, got ' + JSON.stringify(e && e.data));
});
