'use strict';

/**
 * How the command line (bin/tickets.js) prints tickets: a table for people, raw lines for scripts, and one ticket in
 * full with its history.
 */

/**
 * The columns of `list --raw`, tab-separated, in this order. scripts/weekly-report.js reads them by position
 * (README.md, "Command line").
 */
const RAW_COLUMNS = Object.freeze(['id', 'status', 'priority', 'title']);

/** One ticket as a line of `list --raw`. */
function rawLine(ticket) {
  return RAW_COLUMNS.map((column) => ticket[column]).join('\t');
}

const minute = (iso) => iso.slice(0, 16).replace('T', ' ');

/** The columns of the `list` table. */
const TABLE_COLUMNS = Object.freeze([
  { title: 'ID', value: (ticket) => ticket.id },
  { title: 'STATUS', value: (ticket) => ticket.status },
  { title: 'PRIORITY', value: (ticket) => ticket.priority },
  { title: 'REQUESTER', value: (ticket) => ticket.requester },
  { title: 'UPDATED', value: (ticket) => minute(ticket.updated) },
  { title: 'TITLE', value: (ticket) => ticket.title },
]);

/** Tickets as an aligned table with a header line. The last column is not padded. */
function table(tickets, columns = TABLE_COLUMNS) {
  const rows = tickets.map((ticket) => columns.map((column) => String(column.value(ticket))));
  const widths = columns.map((column, index) => Math.max(column.title.length, ...rows.map((row) => row[index].length)));
  const line = (cells) => cells.map((cell, index) => (index === cells.length - 1 ? cell : cell.padEnd(widths[index]))).join('  ');
  return [line(columns.map((column) => column.title)), ...rows.map(line)].join('\n');
}

/** What one change did, for a history line: "status open -> in_progress; priority normal -> high". */
function describeChanges(changes) {
  return Object.entries(changes)
    .map(([field, { from, to }]) => (from === null ? `${field} ${to}` : `${field} ${from} -> ${to}`))
    .join('; ');
}

/** One ticket in full, then its history. */
function details(ticket, history) {
  const fields = ['status', 'priority', 'requester', 'created', 'updated'];
  const width = Math.max(...fields.map((field) => field.length));
  const lines = [`${ticket.id}  ${ticket.title}`];
  for (const field of fields) lines.push(`  ${field.padEnd(width)}  ${ticket[field]}`);
  lines.push('', 'History');
  for (const entry of history) {
    lines.push(`  ${minute(entry.at)}  ${entry.actor}  ${entry.action}  ${describeChanges(entry.changes)}`);
  }
  return lines.join('\n');
}

module.exports = { RAW_COLUMNS, TABLE_COLUMNS, describeChanges, details, rawLine, table };
