'use strict';
// Witness R-5.8: A refused assignment adds no outbox event.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  for (const final of ['resolved', 'closed']) {
    const t = await L.ticket(s.api, { title: 'T ' + final });
    await L.assign(s.api, t.id, 'dana');
    await L.advance(s.api, t.id, final);
    const before = (await L.events(s.api)).length;
    const r = await L.assign(s.api, t.id, 'erin');
    check(r.status === 409, final + ' refuses');
    eq((await L.events(s.api)).length, before, final + ' outbox size unchanged');
  }
});
