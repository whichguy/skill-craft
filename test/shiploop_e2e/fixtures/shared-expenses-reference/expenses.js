'use strict';

// The rules of the shared-expenses service, free of HTTP and storage.

const isName = (value) => typeof value === 'string' && value.length > 0;
const isWholeCents = (value) => Number.isSafeInteger(value) && value >= 0;

function validMembers(members) {
  return Array.isArray(members) && members.length >= 2 && members.every(isName) && new Set(members).size === members.length;
}

// What each member owes for one expense, or null when the split is not valid. An even split gives the cents left over,
// one each, to the members listed first.
function owedBy(members, cents, split, shares) {
  if (split === 'equal') {
    const base = Math.floor(cents / members.length);
    const extra = cents % members.length;
    return Object.fromEntries(members.map((name, index) => [name, base + (index < extra ? 1 : 0)]));
  }
  if (split === 'exact') {
    if (shares === null || typeof shares !== 'object' || Array.isArray(shares)) return null;
    const owed = {};
    let total = 0;
    for (const [name, amount] of Object.entries(shares)) {
      if (!members.includes(name) || !isWholeCents(amount)) return null;
      owed[name] = amount;
      total += amount;
    }
    return total === cents ? owed : null;
  }
  return null;
}

function balances(group) {
  const net = Object.fromEntries(group.members.map((name) => [name, 0]));
  for (const expense of group.expenses) {
    net[expense.payer] += expense.cents;
    for (const [name, amount] of Object.entries(expense.owed)) net[name] -= amount;
  }
  return net;
}

// The member who owes most pays the member who is owed most the smaller of the two amounts, until nothing is owed.
// Ties go to the member listed first.
function settlements(group) {
  const net = balances(group);
  const payments = [];
  for (;;) {
    let debtor = null;
    let creditor = null;
    for (const name of group.members) {
      if (net[name] < 0 && (debtor === null || net[name] < net[debtor])) debtor = name;
      if (net[name] > 0 && (creditor === null || net[name] > net[creditor])) creditor = name;
    }
    if (debtor === null || creditor === null) return payments;
    const cents = Math.min(-net[debtor], net[creditor]);
    payments.push({ from: debtor, to: creditor, cents });
    net[debtor] += cents;
    net[creditor] -= cents;
  }
}

module.exports = { balances, isName, owedBy, settlements, validMembers };
