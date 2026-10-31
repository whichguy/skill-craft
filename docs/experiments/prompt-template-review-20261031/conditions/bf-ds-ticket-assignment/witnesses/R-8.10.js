'use strict';
// Witness R-8.10: Re-assigning the same agent enqueues nothing, even after the first notice was delivered.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService({ workerMs: 30 });
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const sent = await L.waitFor(async () => (await L.outbox(s.api)).sent.find((e) => e.type === 'ticket.assigned'), 4000);
  check(sent, 'the first notice was delivered');
  await L.assign(s.api, t.id, 'dana');
  await sleep(300);
  eq((await L.events(s.api, 'ticket.assigned')).length, 1, 'still one ticket.assigned event');
});
