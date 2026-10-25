'use strict';
// P6b (adapted P6): init with the current `capacity` field; is a claim beyond it refused?
const lib = require('./lib');
const dir = lib.newRunDir();
const steps = []; for (let i = 0; i < 4; i++) steps.push({id: 'P' + i, deps: [], contract: lib.contract('P' + i)});
const view = lib.cliOk('init', dir, {owner: 'parent', graph: {version: 1, steps}, capacity: 1});
console.log('capacity', view.capacity, 'available', view.available_capacity, 'claim action steps', JSON.stringify(view.actions.find(a => a.action === 'claim').steps));
const two = lib.cli('claim', dir, {owner: 'parent', steps: ['P0', 'P1']});
console.log('claim 2 with capacity 1 ->', two.status, two.stderr.trim().slice(0, 200));
const one = lib.cli('claim', dir, {owner: 'parent', steps: ['P0']});
console.log('claim 1 ->', one.status);
const more = lib.cli('claim', dir, {owner: 'parent', steps: ['P1']});
console.log('claim another while 1 active ->', more.status, more.stderr.trim().slice(0, 200));
