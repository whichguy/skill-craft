'use strict';

// Local simulation only. This does not implement or contact Apps Script.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function createProperties(initial = {}, fault = () => {}) {
  const values = new Map(Object.entries(initial));
  const calls = [];
  const invoke = (operation, key, value) => {
    calls.push({ operation, key, value });
    fault({ operation, key, value, values });
  };
  const service = {
    getProperty(key) {
      invoke('getProperty', key);
      return values.has(key) ? values.get(key) : null;
    },
    setProperty(key, value) {
      invoke('setProperty', key, value);
      values.set(key, String(value));
      return service;
    },
    deleteProperty(key) {
      invoke('deleteProperty', key);
      values.delete(key);
      return service;
    },
    getProperties() {
      invoke('getProperties');
      return Object.fromEntries(values);
    },
  };
  return { service, values, calls };
}

let nextUuid = 0;
function loadRuntime(options = {}) {
  const properties = options.properties || createProperties();
  const cache = new Map();
  const globals = {
    PropertiesService: { getScriptProperties: () => properties.service },
    Utilities: { getUuid: () => `local-sim-${++nextUuid}` },
    ...options.globals,
  };
  function load(name) {
    if (cache.has(name)) return cache.get(name).exports;
    if (!['common-js/total-cents', 'common-js/remote-repeatable-tests'].includes(name)) {
      throw new Error(`Unexpected local module: ${name}`);
    }
    const module = { exports: {} };
    cache.set(name, module);
    const context = vm.createContext({
      ...globals,
      require: load,
      __getCurrentModule: () => module,
      __defineModule__: (factory) => factory(module, module.exports),
    });
    const filename = path.join(__dirname, '..', `${name}.gs`);
    new vm.Script(fs.readFileSync(filename, 'utf8'), { filename }).runInContext(context);
    return module.exports;
  }
  return { suite: load('common-js/remote-repeatable-tests'), fixture: load('common-js/total-cents'), properties };
}

const plain = (value) => JSON.parse(JSON.stringify(value));
module.exports = { createProperties, loadRuntime, plain };
