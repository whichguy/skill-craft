#!/usr/bin/env node
'use strict';

/**
 * The operators' command line. It reads the service's data file, DATA_FILE or --data FILE, and never writes it.
 *
 *   tickets list [--status S] [--priority P] [--raw]
 *   tickets show <id>
 *
 * README.md, "Command line", has examples. Exit codes: 0 done, 1 no such ticket, 2 usage or data file problem.
 */

const { systemClock } = require('../src/clock');
const { AppError } = require('../src/errors');
const { details, rawLine, table } = require('../src/format');
const { DataFileError, createPersistence } = require('../src/persistence');
const { TicketStore } = require('../src/store');
const { parseListQuery } = require('../src/tickets/query');

const USAGE = [
  'usage: tickets [--data FILE] list [--status STATUS] [--priority PRIORITY] [--raw]',
  '       tickets [--data FILE] show ID',
].join('\n');

class UsageError extends Error {}

function parseArgs(argv, env) {
  const options = { data: env.DATA_FILE || null, raw: false, help: false, query: new URLSearchParams(), words: [] };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--raw') options.raw = true;
    else if (arg === '-h' || arg === '--help') options.help = true;
    else if (arg === '--data' || arg === '--status' || arg === '--priority') {
      const value = argv[index + 1];
      if (value === undefined) throw new UsageError(`${arg} needs a value`);
      index += 1;
      if (arg === '--data') options.data = value;
      else options.query.set(arg.slice(2), value);
    } else if (arg.startsWith('-')) throw new UsageError(`unknown option ${arg}`);
    else options.words.push(arg);
  }
  return options;
}

/** A read-only store over the data file: no persistence, so nothing the command line does is saved. */
function openStore(file) {
  if (!file) throw new UsageError('no data file: set DATA_FILE or pass --data FILE');
  const state = createPersistence(file).load();
  if (state === null) throw new UsageError(`${file} does not exist`);
  return new TicketStore({ clock: systemClock, state });
}

/** Every ticket that passes `filters`, in id order, page by page. */
function allTickets(store, filters) {
  const tickets = [];
  let after = null;
  for (;;) {
    const page = store.list({ filters, limit: 100, after });
    tickets.push(...page.items);
    if (!page.next) return tickets;
    after = page.items[page.items.length - 1].id;
  }
}

function list(store, options, out) {
  const { filters } = parseListQuery(options.query);
  const tickets = allTickets(store, filters);
  if (options.raw) {
    for (const ticket of tickets) out.write(`${rawLine(ticket)}\n`);
  } else if (tickets.length === 0) {
    out.write('no tickets\n');
  } else {
    out.write(`${table(tickets)}\n`);
  }
  return 0;
}

function show(store, options, out) {
  const [id] = options.words.slice(1);
  if (!id) throw new UsageError('show needs a ticket id');
  out.write(`${details(store.get(id), store.history(id))}\n`);
  return 0;
}

const COMMANDS = { list, show };

/** Run the command line with `argv` (without node and the script); returns the exit code. */
function main(argv, { env = process.env, out = process.stdout, err = process.stderr } = {}) {
  try {
    const options = parseArgs(argv, env);
    const command = COMMANDS[options.words[0]];
    if (options.help) {
      out.write(`${USAGE}\n`);
      return 0;
    }
    if (!command) throw new UsageError(options.words[0] ? `unknown command ${options.words[0]}` : 'no command given');
    return command(openStore(options.data), options, out);
  } catch (error) {
    if (error instanceof UsageError) {
      err.write(`tickets: ${error.message}\n${USAGE}\n`);
      return 2;
    }
    if (error instanceof DataFileError) {
      err.write(`tickets: ${error.message}\n`);
      return 2;
    }
    if (error instanceof AppError) {
      err.write(`tickets: ${error.message}\n`);
      return error.code === 'not_found' ? 1 : 2;
    }
    throw error;
  }
}

if (require.main === module) {
  process.exitCode = main(process.argv.slice(2));
}

module.exports = { main, parseArgs };
