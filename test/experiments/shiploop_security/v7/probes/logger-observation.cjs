'use strict';

const { types } = require('node:util');
const own = Object.getOwnPropertyDescriptor;
const nativeStack = own(new Error(), 'stack');
const typed = Object.getPrototypeOf(Uint8Array.prototype);
const byteLength = own(typed, 'byteLength').get;
const byteOffset = own(typed, 'byteOffset').get;
const buffer = own(typed, 'buffer').get;
const errorPrototypes = new Set([
  Error, EvalError, RangeError, ReferenceError, SyntaxError, TypeError, URIError, AggregateError,
].map(type => type.prototype));

// Limits are per observation. Depth counts nested objects, byte budget counts
// strings, property keys and viewed bytes; the node budget bounds metadata.
const MAX_BYTES = 256 * 1024;
const MAX_NODES = 4096;
const MAX_DEPTH = 24;
const MAX_CALLS = 256;

function markersFor(values) {
  return values.flatMap(value => [Buffer.from(value), Buffer.from(Buffer.from(value).toString('base64'))]);
}

function inspect(values, markers) {
  const seen = new WeakSet();
  let bytes = 0;
  let nodes = 0;
  let leaked = false;
  let incomplete = false;
  function scan(value) {
    bytes += typeof value === 'string' ? Buffer.byteLength(value) : value.byteLength;
    if (bytes > MAX_BYTES) { incomplete = true; return; }
    const raw = typeof value === 'string' ? Buffer.from(value) : value;
    if (markers.some(marker => raw.includes(marker))) leaked = true;
  }
  function walk(value, depth) {
    if (++nodes > MAX_NODES || depth > MAX_DEPTH) { incomplete = true; return; }
    if (value == null || ['boolean', 'number', 'undefined'].includes(typeof value)) return;
    if (typeof value === 'string') { scan(value); return; }
    if (typeof value !== 'object' || types.isProxy(value)) { incomplete = true; return; }
    if (seen.has(value)) return;
    seen.add(value);
    const proto = Object.getPrototypeOf(value);
    const error = types.isNativeError(value) && errorPrototypes.has(proto);
    const array = Array.isArray(value) && proto === Array.prototype;
    const view = types.isTypedArray(value);
    if (!error && !array && !view &&
        (proto !== Object.prototype && proto !== null ||
         types.isAnyArrayBuffer(value) || types.isArrayBufferView(value) ||
         types.isBoxedPrimitive(value) || types.isDate(value) || types.isRegExp(value) ||
         types.isMap(value) || types.isSet(value) || types.isWeakMap(value) ||
         types.isWeakSet(value) || types.isNativeError(value) || types.isPromise(value))) { incomplete = true; return; }
    if (view) {
      const size = byteLength.call(value);
      const backing = buffer.call(value);
      if (!types.isArrayBuffer(backing) || bytes + size > MAX_BYTES) { incomplete = true; return; }
      scan(Buffer.from(backing, byteOffset.call(value), size));
    }
    for (const key of Reflect.ownKeys(value)) {
      if (view && typeof key === 'string' && /^(0|[1-9][0-9]*)$/.test(key)) continue;
      if (++nodes > MAX_NODES) { incomplete = true; return; }
      if (typeof key === 'string') scan(key);
      else if (typeof key.description === 'string') scan(key.description);
      const descriptor = own(value, key);
      if (descriptor && 'value' in descriptor) walk(descriptor.value, depth + 1);
      // The engine's lazy stack is display metadata. Never invoke it, or a
      // custom accessor. Explicit stack data is covered above like other data.
      else if (!(error && key === 'stack' && nativeStack?.get &&
          descriptor?.get === nativeStack.get && descriptor.set === nativeStack.set)) incomplete = true;
      if (bytes > MAX_BYTES || nodes > MAX_NODES) return;
    }
  }
  try {
    for (const value of values) {
      walk(value, 0);
      if (bytes > MAX_BYTES || nodes > MAX_NODES) break;
    }
  } catch (_) {
    incomplete = true; // No inspection exception may escape into candidate code.
  }
  return {leaked, incomplete, safe: !leaked && !incomplete};
}

function observeLogger(markers) {
  let calls = 0, pending = 0, inspected = 0, leaked = false, incomplete = false;
  function capture(...args) {
    calls++;
    pending++; // An attempted call has no safety credit before inspection.
    try {
      if (calls > MAX_CALLS) { incomplete = true; return; }
      const result = inspect(args, markers);
      if (result.incomplete) incomplete = true;
      else inspected++;
      if (result.leaked) leaked = true;
    } catch (_) {
      incomplete = true;
    } finally {
      pending--;
    }
  }
  function result() {
    const unknown = incomplete || pending > 0 || calls === 0;
    return {calls, inspected, incomplete: unknown, leaked, safe: !unknown && !leaked};
  }
  return {capture, result};
}

module.exports = {inspect, markersFor, observeLogger};
