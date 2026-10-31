'use strict';
// Witness R-8.14: A failing delivery is retried and eventually marked dead.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const blocker = L.tmpfile('blocker');
  L.fs.writeFileSync(blocker, 'x');
  const s = await L.startService({ notifyFile: blocker + '/n.log', workerMs: 20 });
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const outcome = await L.waitFor(async () => {
    const o = await L.outbox(s.api);
    const sent = o.sent.find((e) => e.type === 'ticket.assigned');
    if (sent) return { bad: 'sent', event: sent };
    const dead = o.dead.find((e) => e.type === 'ticket.assigned');
    return dead ? { event: dead } : null;
  }, 22000, 100);
  check(outcome, 'the failing ticket.assigned event reached a final state');
  check(outcome && !outcome.bad, 'a failed delivery is not recorded as sent');
  check(outcome && outcome.event && outcome.event.status === 'dead' && outcome.event.attempts === 5 && outcome.event.lastError, 'event is dead after 5 attempts with lastError: ' + JSON.stringify(outcome && outcome.event && { s: outcome.event.status, a: outcome.event.attempts }));
});
