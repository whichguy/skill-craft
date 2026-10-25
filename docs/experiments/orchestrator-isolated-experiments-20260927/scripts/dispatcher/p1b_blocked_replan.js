'use strict';
// P1b (adapted P1): settle the BLOCKED attempt with verification.disposition "replan"
// (the field the current retry instruction names). Does next route to replan, and are retry/claim refused?
const lib = require('./lib');
const {dir} = lib.initRun();
const {attempt, envelope} = lib.driveToReport(dir, 'parent', 'A', {status: 'BLOCKED', body: {actual: 'cannot proceed'}});
const rec = lib.cliOk('receipt', dir, {attempt});
const settled = lib.cli('settle', dir, {owner: 'parent', attempt, verification: {receipt_sha256: rec.sha256, passed: false, reason: 'BLOCKED: proven unachievable', evidence: lib.evidence({passed: false}), disposition: 'replan'}});
console.log('settle status', settled.status, settled.status ? settled.stderr : '');
const n = lib.cliOk('next', dir);
console.log('action kinds', JSON.stringify(n.actions.map(a => a.action)));
console.log('replan action', JSON.stringify(n.actions.find(a => a.action === 'replan'), (k, v) => k === 'instruction' ? String(v).slice(0, 300) : v));
console.log('snapshot.replan', JSON.stringify(n.replan));
const r = lib.cli('retry', dir, {owner: 'parent', attempt, confirmed_stopped: true, reason: 'try again'});
console.log('retry after replan:', r.status, r.stderr.trim().slice(0, 250));
const c = lib.cli('claim', dir, {owner: 'parent', steps: ['C']});
console.log('claim C after replan:', c.status, c.stderr.trim().slice(0, 250));
