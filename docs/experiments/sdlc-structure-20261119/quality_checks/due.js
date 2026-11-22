'use strict';
// Runs the judges' functional check for the ticket case against one product tree:
// what the command line shows for a ticket a 1.4.0 file holds without a due time, against what the service gives it.
const fs = require('node:fs'); const os = require('node:os'); const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { start, req } = require('./lib');
(async () => {
  const [base, dir] = process.argv.slice(2); const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'qd-')); const out = {};
  const file = path.join(tmp, 'data.json');
  let s = await start(base, 'src/server.js', { DATA_FILE: file });
  if (!s.started) { console.log(JSON.stringify({ error: 'base did not start', out: s.out().slice(0, 300) })); return; }
  const made = await req(s.port, 'POST', '/tickets', { title: 'Printer on fire', priority: 'high', requester: 'ann@example.com' });
  out.base_create = made.status; const id = (made.body.ticket || made.body).id; const created = (made.body.ticket || made.body).createdAt || (made.body.ticket || made.body).created;
  await s.stop();
  out.file_has_due_before = /"due"/.test(fs.readFileSync(file, 'utf8'));
  const env = { PATH: process.env.PATH, HOME: process.env.HOME, DUE_TIMES: 'on', DUE_HOURS_HIGH: '10' };
  const cli = spawnSync(process.execPath, ['bin/tickets.js', '--data', file, 'show', id], { cwd: dir, env, encoding: 'utf8' });
  out.cli_exit = cli.status; out.cli_due_line = (cli.stdout + cli.stderr).split('\n').filter((l) => /due/i.test(l)).join(' | ').slice(0, 200);
  out.file_has_due_after_cli = /"due"/.test(fs.readFileSync(file, 'utf8'));
  const copy = path.join(tmp, 'copy.json'); fs.copyFileSync(file, copy);
  s = await start(dir, 'src/server.js', { DATA_FILE: copy, DUE_TIMES: 'on', DUE_HOURS_HIGH: '10' });
  if (!s.started) { out.service = 'did not start: ' + s.out().slice(0, 200); console.log(JSON.stringify(out)); return; }
  const got = await req(s.port, 'GET', `/tickets/${id}`);
  const t = got.body.ticket || got.body; out.created = created || t.createdAt || t.created; out.service_due = t.due;
  await s.stop();
  const c = Date.parse(out.created);
  out.service_hours = (Date.parse(out.service_due) - c) / 3600000;
  const m = /(\d{4}-\d\d-\d\dT[\d:.]+Z)/.exec(out.cli_due_line || '');
  out.cli_hours = m ? (Date.parse(m[1]) - c) / 3600000 : null;
  console.log(JSON.stringify(out));
})();
