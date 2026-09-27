'use strict';
const lib = require('./lib');
const {dir, view} = lib.initRun();
console.log('init view:', JSON.stringify(view, null, 2).slice(0, 800));
const {attempt, envelope, reportResp} = lib.driveToReport(dir, 'parent', 'A');
console.log('report response:', JSON.stringify(reportResp, null, 2).slice(0, 1200));
const settled = lib.settleFrom(dir, 'parent', attempt, envelope);
console.log('settled outcome:', settled.outcome);
console.log('SMOKE OK');
