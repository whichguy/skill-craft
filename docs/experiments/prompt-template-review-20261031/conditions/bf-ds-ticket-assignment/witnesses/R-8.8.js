'use strict';
// Witness R-8.8: The notice is delivered exactly once.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const nf = L.tmpfile('n.log');
  const s = await L.startService({ notifyFile: nf, workerMs: 30 });
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const lines = () => (L.fs.existsSync(nf) ? L.fs.readFileSync(nf, 'utf8').split('\n').filter(Boolean).map((x) => JSON.parse(x)) : []);
  await L.waitFor(() => lines().find((l) => l.to === 'dana'), 4000);
  await sleep(500);
  eq(lines().filter((l) => l.to === 'dana').length, 1, 'lines delivered to dana');
  const sent = (await L.outbox(s.api)).sent.filter((e) => e.to === 'dana');
  eq(sent.length, 1, 'one sent event');
});
