'use strict';
// Witness R-8.15: Returning to an agent whose earlier notice was delivered enqueues a new notice.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService({ workerMs: 30 });
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const first = await L.waitFor(async () => (await L.outbox(s.api)).sent.find((e) => e.to === 'dana' && e.type === 'ticket.assigned'), 4000);
  check(first, 'the first notice to dana was delivered');
  await L.assign(s.api, t.id, 'erin');
  await L.assign(s.api, t.id, 'dana');
  await sleep(300);
  const toDana = (await L.events(s.api, 'ticket.assigned')).filter((e) => e.to === 'dana');
  eq(toDana.length, 2, 'two notices to dana in total');
});
