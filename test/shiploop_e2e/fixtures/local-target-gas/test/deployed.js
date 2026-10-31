'use strict';
// Load server files from the deployment into one shared global scope, the way Apps Script runs them, and return that
// scope: the functions the files declare are its properties.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const vm = require('node:vm');
const target = process.env.LOCAL_TARGET || path.join(os.tmpdir(), 'local-target-gas');
module.exports = function deployed(...names) {
  const scope = vm.createContext({});
  for (const name of names) vm.runInContext(fs.readFileSync(path.join(target, name), 'utf8'), scope, { filename: name });
  return scope;
};
