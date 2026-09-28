'use strict';
// P2: complete:true — drive a tiny graph to completion. Does the terminal
// response still carry next_argv pointing at `dispatch.js next`?
const fs = require('node:fs');
const path = require('node:path');
const lib = require('./lib');

const log = [];
function record(label, value) { log.push({label, value}); console.log('== ' + label + ' =='); console.log(JSON.stringify(value, null, 2)); }

// Single-step graph so we reach complete:true in one round.
const singleGraph = {version: 1, steps: [{id: 'A', deps: [], contract: lib.contract('A')}]};
const {dir} = lib.initRun(singleGraph);
record('init dir', dir);

const {attempt, envelope} = lib.driveToReport(dir, 'parent', 'A', {status: 'SUCCEEDED'});
const settled = lib.settleFrom(dir, 'parent', attempt, envelope, {passed: true});
record('settle response (should show complete graph)', settled);

const nextResp = lib.cliOk('next', dir);
record('terminal next response', nextResp);

record('complete flag', nextResp.complete);
record('actions on terminal response', nextResp.actions);
record('next_argv on terminal response', nextResp.next_argv);
record('next_argv points at dispatch.js next?', JSON.stringify(nextResp.next_argv).includes('"next"') && nextResp.next_argv[nextResp.next_argv.length - 2] === 'next');

// Follow it one more time to see if it just loops on the same terminal state.
const followed = lib.cliOk(...['next', dir]);
record('following next_argv again (loop check)', followed);
record('same complete result on loop?', JSON.stringify(followed.progress) === JSON.stringify(nextResp.progress));

fs.writeFileSync(path.join(__dirname, 'p2_output.json'), JSON.stringify(log, null, 2));
console.log('P2 DONE');
