'use strict';

/*
 * T1 dispatcher scenarios (plan phase 1). Spec:
 * test/orchestrator_scenarios/specs/dispatcher-scenarios.md; IDs [C1].. and
 * the seeded sweep [R1].. Each scenario runs normally and with context loss;
 * both must satisfy the oracle and accept the same steps (I7). Scenarios run in
 * parallel child processes. SCENARIO_SEEDS overrides the sweep ("1-40").
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const { spawn } = require('node:child_process');
const cli = require('./orchestrator_scenarios/dispatcher-cli');
const harness = require('./orchestrator_scenarios/harness');

function seeds() {
  const [low, high] = (process.env.SCENARIO_SEEDS || '1-4').split('-').map(Number);
  return Array.from({ length: (high || low) - low + 1 }, (_, index) => low + index);
}

function scenarios() {
  return [...harness.loadScenarios(), ...seeds().map((seed) => harness.seededScenario(seed))];
}

// Child: run one scenario both ways and print one PASS/FAIL line.
function runOne(id) {
  const scenario = scenarios().find((item) => item.id === id);
  const root = cli.makeRoot('dispatcher-scenario-' + id + '-');
  const name = '[' + id + '] ' + scenario.name;
  try {
    const normal = harness.runScenario(root, scenario);
    const amnesia = harness.runScenario(root, scenario, { amnesia: true });
    // I7: losing context reaches the same accepted steps and replan outcome.
    assert.deepEqual({ accepted: amnesia.accepted, replan: amnesia.replan },
      { accepted: normal.accepted, replan: normal.replan }, 'I7: the context-loss run ended differently');
    console.log('PASS ' + name + ' (' + normal.calls + ' calls; ' + amnesia.calls + ' with ' + amnesia.lost + ' context losses)');
    fs.rmSync(root, { recursive: true, force: true });
  } catch (error) {
    console.log('FAIL ' + name + ' (fixtures: ' + root + ')\n' + (error.stack || error));
    process.exitCode = 1;
  }
}

async function runAll() {
  const queue = scenarios().map((item) => item.id);
  const jobs = Math.max(2, Math.min(8, os.availableParallelism() - 1));
  let failed = 0;
  const worker = async () => {
    while (queue.length) {
      const id = queue.shift();
      const result = await cli.runAsync([process.execPath, __filename, id]);
      process.stdout.write(result.stdout + result.stderr);
      if (result.status !== 0) failed += 1;
    }
  };
  await Promise.all(Array.from({ length: jobs }, worker));
  if (failed) {
    console.log(failed + ' scenario(s) failed');
    process.exitCode = 1;
  }
}

if (process.argv[2]) runOne(process.argv[2]);
else runAll();
