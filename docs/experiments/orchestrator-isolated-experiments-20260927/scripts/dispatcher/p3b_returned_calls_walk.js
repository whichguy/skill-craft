'use strict';
// P3b (adapted P3 for the current API): walk A, C, B -> completion following ONLY
// the calls the dispatcher returns (action.call / action.calls / packet report call).
// Count calls whose op+argv came from a response vs. calls the caller composed.
const fs = require('fs'); const path = require('path'); const lib = require('./lib'); const {spawnSync} = require('child_process');
const {dir, view} = lib.initRun();
const log = []; let returned = 0, composed = 1 /* init */; const opsSeen = []; const placeholderFields = new Set();
const isPh = v => typeof v === 'string' && /^<.*>$/.test(v);
function fill(input, ctx, parentKey) {
  if (isPh(input)) { placeholderFields.add((parentKey||'?') + '[]'); return ctx.byKey(parentKey + '[]', input); }
  if (Array.isArray(input)) return input.map(v => fill(v, ctx, parentKey));
  if (input && typeof input === 'object' && 'sha256' in input && (isPh(input.path) || isPh(input.sha256))) {
    placeholderFields.add((parentKey||'?') + '.{path,sha256}'); return lib.evidence({checked: true, field: parentKey});
  }
  if (input && typeof input === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(input)) {
      if (typeof v === 'string' && /^<omit/.test(v)) { placeholderFields.add(k + ' (omit)'); continue; }
      if (typeof v === 'string' && /^<.*>$/.test(v)) { placeholderFields.add(k); out[k] = ctx.byKey(k, v); continue; }
      out[k] = fill(v, ctx, k);
    }
    return out;
  }
  return input;
}
const ctx = {
  byKey(k, v) {
    if (k === 'workspace') { const w = path.join(lib.ROOT, 'ws-' + Math.random().toString(36).slice(2)); fs.mkdirSync(w); return w; }
    if (k === 'write_scope' || k === 'write_scope[]') return k.endsWith('[]') ? 'result.txt' : ['result.txt'];
    if (k === 'resources') return [];
    if (k === 'ready_evidence' || k === 'evidence') return lib.evidence({checked: true});
    if (k === 'handle') return 'fixture-handle-' + Math.random().toString(36).slice(2);
    if (k === 'passed') return true;
    if (k === 'reason') return 'fixture inspection passed';
    if (k === 'status') return 'SUCCEEDED';
    return v; // unknown: leave so the dispatcher refuses visibly
  },
  value(v) { return v; },
};
function run(call, label) {
  let argv = [...call.argv]; let input;
  if (call.input !== undefined) {
    input = fill(call.input, ctx);
    const file = call.input_path || lib.save({});
    fs.writeFileSync(file, JSON.stringify(input));
    argv.push(file);
  }
  const op = call.argv[2];
  opsSeen.push(label + ':' + op);
  returned++;
  const c = spawnSync(argv[0], argv.slice(1), {cwd: lib.CWD, encoding: 'utf8'});
  if (c.status !== 0) { console.log('FAIL', op, c.stderr.slice(0, 600)); console.log(JSON.stringify(input).slice(0, 600)); process.exit(1); }
  return JSON.parse(c.stdout);
}
let resp = view; let guard = 0; const packets = {}; const reported = new Set();
function worker(pk) { // the native worker: write the artifact, fill its envelope, run report_argv as given
  fs.writeFileSync(pk.outputs.artifact, JSON.stringify({actual: 42}));
  const env = {...pk.report_envelope, status: 'SUCCEEDED', evidence: {path: pk.outputs.artifact, sha256: lib.digest(fs.readFileSync(pk.outputs.artifact))}};
  fs.writeFileSync(pk.outputs.envelope, JSON.stringify(env));
  opsSeen.push('worker:report'); returned++;
  const c = spawnSync(pk.report_argv[0], pk.report_argv.slice(1), {cwd: lib.CWD, encoding: 'utf8'});
  if (c.status !== 0) { console.log('REPORT FAIL', c.stderr); process.exit(1); }
}
function follow(r, label) { // run a response's own follow-on call chain (start -> launched)
  while (r && r.call && !r.actions) { if (r.packet) packets[r.attempt || r.packet.attempt] = r.packet; r = run(r.call, label + '>' + r.call.argv[2]); }
  if (r && r.packet) packets[r.packet.attempt] = r.packet;
  return r;
}
while (!resp.complete && guard++ < 80) {
  const a = (resp.actions || [])[0];
  if (!a) { console.log('NO ACTIONS', JSON.stringify(resp).slice(0, 600)); break; }
  log.push(a.action);
  if (a.action === 'collect' && packets[a.attempt] && !reported.has(a.attempt)) { reported.add(a.attempt); worker(packets[a.attempt]); }
  const calls = a.call ? [a.call] : (a.calls || []);
  let last;
  for (const c of calls) last = follow(run(c, a.action), a.action);
  resp = last && last.actions ? last : run({argv: (last && last.next_argv) || resp.next_argv}, 'next');
}
console.log(JSON.stringify({complete: resp.complete, actions_taken: log, ops: opsSeen, calls_from_returned_argv: returned, calls_composed_by_caller: composed, placeholder_fields_filled: [...placeholderFields], terminal_next_argv: resp.next_argv}, null, 2));
