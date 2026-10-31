'use strict';
// Witness R-8.13: The template renders a body naming the ticket (deliverable).
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const nf = L.tmpfile('n.log');
  const s = await L.startService({ notifyFile: nf, workerMs: 30 });
  const t = await L.ticket(s.api, { title: 'Broken monitor' });
  await L.assign(s.api, t.id, 'dana');
  const lines = () => (L.fs.existsSync(nf) ? L.fs.readFileSync(nf, 'utf8').split('\n').filter(Boolean).map((x) => JSON.parse(x)) : []);
  const line = await L.waitFor(() => lines().find((l) => l.to === 'dana'), 4000);
  check(line, 'the notice was delivered (not dead)');
  check(line && (line.body.includes(t.id) || line.body.includes('Broken monitor')), 'body names the ticket, got ' + (line && line.body));
});
