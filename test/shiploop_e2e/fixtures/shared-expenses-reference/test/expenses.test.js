'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { balances, owedBy, settlements, validMembers } = require('../expenses');

test('an even split gives the cents left over to the members listed first', () => {
  assert.deepEqual(owedBy(['ann', 'bob', 'cy'], 101, 'equal'), { ann: 34, bob: 34, cy: 33 });
});

test('shares must add up to the amount', () => {
  assert.equal(owedBy(['ann', 'bob'], 100, 'exact', { ann: 60, bob: 50 }), null);
  assert.deepEqual(owedBy(['ann', 'bob'], 100, 'exact', { bob: 100 }), { bob: 100 });
});

test('a group needs two distinct non-empty names', () => {
  assert.equal(validMembers(['ann']), false);
  assert.equal(validMembers(['ann', 'ann']), false);
  assert.equal(validMembers(['ann', 'bob']), true);
});

test('balances add up to zero and settlements clear them', () => {
  const group = { members: ['ann', 'bob', 'cy'], expenses: [
    { payer: 'ann', cents: 100, owed: owedBy(['ann', 'bob', 'cy'], 100, 'equal') },
    { payer: 'bob', cents: 50, owed: { ann: 10, bob: 20, cy: 20 } },
  ] };
  assert.deepEqual(balances(group), { ann: 56, bob: -3, cy: -53 });
  assert.deepEqual(settlements(group), [{ from: 'cy', to: 'ann', cents: 53 }, { from: 'bob', to: 'ann', cents: 3 }]);
});
