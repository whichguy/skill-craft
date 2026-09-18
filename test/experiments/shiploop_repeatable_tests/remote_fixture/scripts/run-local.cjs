'use strict';

const { loadRuntime, plain } = require('../tests/local-runtime.cjs');

try {
  if (process.argv.length > 3) throw new Error('Usage: node scripts/run-local.cjs [full|smoke|JSON-selection]');
  const input = process.argv[2] || 'full';
  const selection = ['full', 'smoke'].includes(input) ? input : JSON.parse(input);
  const result = plain(loadRuntime().suite.runRepeatableTests(selection));
  console.log(JSON.stringify({ executionLocation: 'local-node-simulation', target: 'in-memory ScriptProperties fake', result }, null, 2));
  process.exitCode = result.summary.failed ? 1 : result.summary.blocked ? 2 : 0;
} catch (error) {
  console.error(`Local simulation error: ${error.message}`);
  process.exitCode = 1;
}
