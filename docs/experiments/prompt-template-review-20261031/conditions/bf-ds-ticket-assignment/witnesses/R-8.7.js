'use strict';
// Witness R-8.7: The delivered NOTIFY_FILE line names type ticket.assigned, to and the ticket id.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const nf = L.tmpfile('n.log');
  const s = await L.startService({ notifyFile: nf, workerMs: 30 });
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const lines = () => (L.fs.existsSync(nf) ? L.fs.readFileSync(nf, 'utf8').split('\n').filter(Boolean).map((x) => JSON.parse(x)) : []);
  const line = await L.waitFor(() => lines().find((l) => l.to === 'dana'), 4000);
  check(line, 'a notice to dana was delivered');
  check(line && line.type === 'ticket.assigned', 'line type is ticket.assigned, got ' + (line && line.type));
  check(line && line.to === 'dana', 'line.to is dana');
  check(line && line.ticket === t.id, 'line.ticket is the ticket id');
});
