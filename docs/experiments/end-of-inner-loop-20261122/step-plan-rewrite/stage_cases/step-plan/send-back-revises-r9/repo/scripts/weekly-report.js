#!/usr/bin/env node
'use strict';

/**
 * The weekly ticket report the support leads read on Monday: how many tickets there are in each status and each
 * priority.
 *
 * It runs `bin/tickets.js list --raw`, so it reads the same data file (DATA_FILE, or --data FILE passed through), and
 * reads the columns by position: 1 id, 2 status, 3 priority, 4 title. --json prints the counts as JSON for the
 * dashboard.
 *
 *   DATA_FILE=data/tickets.json npm run report:weekly
 *   node scripts/weekly-report.js --data data/tickets.json --json
 */

const { execFileSync } = require('node:child_process');
const path = require('node:path');
const { PRIORITIES } = require('../src/tickets/priorities');
const { STATUSES } = require('../src/tickets/states');

const CLI = path.join(__dirname, '..', 'bin', 'tickets.js');

/** The lines of `tickets list --raw`. */
function rawLines(passThrough) {
  const output = execFileSync(process.execPath, [CLI, ...passThrough, 'list', '--raw'], { encoding: 'utf8' });
  return output.split('\n').filter((line) => line !== '');
}

/** Counts by status and by priority, from raw lines. */
function count(lines) {
  const byStatus = Object.fromEntries(STATUSES.map((status) => [status, 0]));
  const byPriority = Object.fromEntries(PRIORITIES.map((priority) => [priority, 0]));
  for (const line of lines) {
    const columns = line.split('\t');
    const status = columns[1];
    const priority = columns[2];
    if (Object.hasOwn(byStatus, status)) byStatus[status] += 1;
    if (Object.hasOwn(byPriority, priority)) byPriority[priority] += 1;
  }
  return { total: lines.length, byStatus, byPriority };
}

function render(report, date) {
  const lines = [`Ticket report for the week of ${date}`, '', 'By status'];
  for (const [status, n] of Object.entries(report.byStatus)) lines.push(`  ${status.padEnd(12)}${String(n).padStart(5)}`);
  lines.push('', 'By priority');
  for (const [priority, n] of Object.entries(report.byPriority)) lines.push(`  ${priority.padEnd(12)}${String(n).padStart(5)}`);
  lines.push('', `  ${'total'.padEnd(12)}${String(report.total).padStart(5)}`);
  return lines.join('\n');
}

function main(argv) {
  const json = argv.includes('--json');
  const passThrough = argv.filter((arg) => arg !== '--json');
  const report = count(rawLines(passThrough));
  process.stdout.write(json ? `${JSON.stringify(report)}\n` : `${render(report, new Date().toISOString().slice(0, 10))}\n`);
}

if (require.main === module) {
  try {
    main(process.argv.slice(2));
  } catch (error) {
    process.stderr.write(`weekly-report: ${error.message}\n`);
    process.exitCode = 1;
  }
}

module.exports = { count, render };
