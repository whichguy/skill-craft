'use strict';
// P1: BLOCKED routing. A worker reports a BLOCKED result for a task (e.g. an
// item is proven unachievable). What does the dispatcher's `next` response
// offer for that step afterward?
const fs = require('node:fs');
const path = require('node:path');
const lib = require('./lib');

const log = [];
function record(label, value) { log.push({label, value}); console.log('== ' + label + ' =='); console.log(JSON.stringify(value, null, 2)); }

const {dir} = lib.initRun();
record('init dir', dir);

const {attempt, envelope, reportResp} = lib.driveToReport(dir, 'parent', 'A', {status: 'BLOCKED', body: {actual: 'cannot proceed: contradicts another item'}});
record('report response (BLOCKED envelope)', reportResp);

// Settle: verifier independently reviews and rejects because the item is
// proven unachievable (per protocol.md: BLOCKED + proven-unachievable -> reject, not retry).
const settled = lib.settleFrom(dir, 'parent', attempt, envelope, {
  passed: false,
  reason: 'BLOCKED: definition_of_done item contradicts the ready contract; proven unachievable at this conflict point',
});
record('settle response', settled);

const nextResp = lib.cliOk('next', dir);
record('next response after BLOCKED+rejected settlement', nextResp);

const stepARow = nextResp.progress.failed.find(r => r.step === 'A') || nextResp.progress.blocked.find(r => r.step === 'A');
record('progress row for step A', stepARow);

const actionsForA = nextResp.actions.filter(a => a.step === 'A' || (a.steps && a.steps.includes('A')));
record('actions mentioning step A', actionsForA);

const allActionKinds = nextResp.actions.map(a => a.action);
record('all action kinds offered', allActionKinds);

fs.writeFileSync(path.join(__dirname, 'p1_output.json'), JSON.stringify(log, null, 2));
console.log('P1 DONE');
