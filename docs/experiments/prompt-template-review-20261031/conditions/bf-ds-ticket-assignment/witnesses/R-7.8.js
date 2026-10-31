'use strict';
// Witness R-7.8: The audit entry carries the time of the change.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await sleep(30);
  const r = await L.assign(s.api, t.id, 'dana');
  const e = (await L.auditOf(s.api, t.id)).find((x) => x.action === 'ticket.assigned');
  check(e && e.at === r.body.updated, 'entry.at equals the ticket updated time: ' + (e && e.at) + ' vs ' + r.body.updated);
  check(e && Date.parse(e.at) > Date.parse(t.created), 'entry.at is later than the creation time');
});
