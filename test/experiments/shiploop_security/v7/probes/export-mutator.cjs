'use strict';

const fs = require('node:fs');
const {isDeepStrictEqual} = require('node:util');

module.exports = function wrap(exported, mode, file, nonce) {
  const original = exported.exportTenantJobs;
  if (typeof original !== 'function') throw new TypeError('missing export target');
  const first = new Map();
  let calls = 0;
  const alternate = {
    blue: {id: 'gold-4', title: 'Gold review', state: 'open'},
    gold: {id: 'blue-2', title: 'Blue permit', state: 'ready'},
  };
  return {...exported, exportTenantJobs(tenant, ids) {
    const result = Reflect.apply(original, this, arguments);
    let replacement = result;
    // Use real fixture rows and the same array/record contract. The stale
    // variant preserves the first export and only changes a refreshed result.
    if (Array.isArray(ids) && ids.length && Array.isArray(result) &&
        Object.hasOwn(alternate, tenant)) {
      if (mode === 'wrong') {
        // Keep the observed state for nonempty results so this mutation
        // isolates row identity from the separate freshness mutation.
        const state = result[0]?.state;
        replacement = [{...alternate[tenant], ...(typeof state === 'string' ? {state} : {})}];
      }
      if (mode === 'stale') {
        const key = JSON.stringify([tenant, ids]);
        if (first.has(key)) replacement = structuredClone(first.get(key));
        else if (first.size < 256) first.set(key, structuredClone(result));
      }
    }
    if (++calls <= 256) {
      const changed = !isDeepStrictEqual(result, replacement);
      fs.appendFileSync(file, nonce + (changed ? ' changed\n' : ' same\n'), {mode: 0o600});
    }
    return replacement;
  }};
};
