'use strict';

const fs = require('node:fs');
const http = require('node:http');
const { balances, isName, owedBy, settlements, validMembers } = require('./expenses');

const DATA_FILE = process.env.DATA_FILE || 'data.json';
const PORT = Number(process.env.PORT) || 3000;

let groups = {};
try {
  groups = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}

// Written through on every change, so an acknowledged request survives a restart.
function save() {
  fs.writeFileSync(`${DATA_FILE}.tmp`, JSON.stringify(groups));
  fs.renameSync(`${DATA_FILE}.tmp`, DATA_FILE);
}

function createGroup(body) {
  if (!isName(body.id) || !validMembers(body.members)) return [400, { error: 'a group needs an id and at least two distinct member names' }];
  if (Object.hasOwn(groups, body.id)) return [409, { error: 'the group exists' }];
  groups[body.id] = { members: body.members, expenses: [] };
  save();
  return [201, { id: body.id }];
}

function addExpense(group, body) {
  const { payer, cents, split, shares } = body;
  if (!group.members.includes(payer) || !Number.isSafeInteger(cents) || cents <= 0) return [400, { error: 'invalid expense' }];
  const owed = owedBy(group.members, cents, split, shares);
  if (owed === null) return [400, { error: 'invalid split' }];
  group.expenses.push({ payer, cents, owed });
  save();
  return [201, { expense: group.expenses.length }];
}

function route(method, path, body) {
  const parts = path.split('/').filter(Boolean);
  if (parts[0] !== 'groups') return [404, { error: 'not found' }];
  if (parts.length === 1 && method === 'POST') return createGroup(body);
  const group = Object.hasOwn(groups, parts[1]) ? groups[parts[1]] : null;
  if (group === null) return [404, { error: 'unknown group' }];
  if (parts[2] === 'expenses' && method === 'POST') return addExpense(group, body);
  if (parts[2] === 'balances' && method === 'GET') return [200, balances(group)];
  if (parts[2] === 'settlements' && method === 'GET') return [200, settlements(group)];
  return [404, { error: 'not found' }];
}

function reply(res, status, payload) {
  res.writeHead(status, { 'content-type': 'application/json' });
  res.end(JSON.stringify(payload));
}

const server = http.createServer((req, res) => {
  let raw = '';
  req.on('data', (chunk) => { raw += chunk; });
  req.on('end', () => {
    let body = {};
    try {
      body = raw ? JSON.parse(raw) : {};
    } catch {
      return reply(res, 400, { error: 'invalid JSON' });
    }
    if (body === null || typeof body !== 'object' || Array.isArray(body)) body = {};
    const [status, payload] = route(req.method, new URL(req.url, 'http://localhost').pathname, body);
    return reply(res, status, payload);
  });
});

server.listen(PORT);
