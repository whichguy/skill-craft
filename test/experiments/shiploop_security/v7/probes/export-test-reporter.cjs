'use strict';

const path = require('node:path');

// Project structured Node events to fixed fields. No test names, messages,
// stack traces, assertion values or user stdout/stderr enter the receipt.
module.exports = async function* (source) {
  for await (const {type, data} of source) {
    const {file, name, nesting, details, skip, todo} = data;
    if (type === 'test:enqueue' && file && nesting === 0 &&
        typeof name === 'string' && path.resolve(name) === file) {
      yield JSON.stringify({type: 'file', file}) + '\n';
    }
    if (type === 'test:pass' && !skip && !todo && details?.type !== 'suite' &&
        file && (typeof name !== 'string' || path.resolve(name) !== file)) {
      yield JSON.stringify({type: 'test', file}) + '\n';
    }
    if (type === 'test:fail' && !skip && !todo) {
      const e = details?.error;
      let outcome = 'other';
      if (e?.code === 'ERR_TEST_FAILURE' && e.failureType === 'subtestsFailed') outcome = 'group';
      if (e?.code === 'ERR_TEST_FAILURE' && e.failureType === 'testCodeFailure' &&
          !('exitCode' in e) && !('signal' in e) &&
          e.cause?.code === 'ERR_ASSERTION' && e.cause.name === 'AssertionError') outcome = 'assertion';
      yield JSON.stringify({type: 'failure', file, outcome}) + '\n';
    }
    if (type === 'test:summary' && file === undefined) {
      yield JSON.stringify({type: 'summary', success: data.success, cancelled: data.counts?.cancelled}) + '\n';
    }
  }
};
