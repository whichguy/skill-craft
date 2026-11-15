'use strict';
// Private adequacy-calibration opt-in only. No resources or verdict handling.
const net = require('node:net');
const { isProxy } = require('node:util').types;
const listen = net.Server.prototype.listen;
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
net.Server.prototype.listen = function (...args) {
  // Only numeric zero and unambiguous omitted-host numeric overloads.
  if (args[0] === 0) {
    const tail = args.slice(1);
    const valid = tail.length === 0 ||
      (tail.length === 1 && typeof tail[0] === 'function') ||
      (tail.length === 1 && Number.isInteger(tail[0]) && tail[0] > 0) ||
      (tail.length === 2 && Number.isInteger(tail[0]) && tail[0] > 0 && typeof tail[1] === 'function');
    if (valid) args.splice(1, 0, '127.0.0.1');
  } else {
    const options = args[0];
    // A plain data record only: accessors, symbols, inherited keys and unknown
    // intent are delegated unchanged. In particular, no host/path/fd/handle,
    // ipv6Only/reusePort/signal/exclusive semantics are inferred.
    if (options && !isProxy(options) && Object.getPrototypeOf(options) === Object.prototype &&
        (args.length === 1 || (args.length === 2 && typeof args[1] === 'function'))) {
      const keys = Reflect.ownKeys(options);
      const safe = keys.every(key => (key === 'port' || key === 'backlog') &&
        own(Object.getOwnPropertyDescriptor(options, key), 'value') &&
        Object.getOwnPropertyDescriptor(options, key).enumerable);
      if (safe && own(options, 'port') && options.port === 0 &&
          (!own(options, 'backlog') || (Number.isInteger(options.backlog) && options.backlog > 0))) {
        args[0] = { ...options, host: '127.0.0.1' };
      }
    }
  }
  return listen.apply(this, args);
};
