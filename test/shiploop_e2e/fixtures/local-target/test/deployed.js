'use strict';
// Load a module from the deployed target, the way the target's own tests see it.
const path = require('node:path');
const os = require('node:os');
const target = process.env.LOCAL_TARGET || path.join(os.tmpdir(), 'local-target');
module.exports = function deployed(name) { return require(path.join(target, 'src', name)); };
