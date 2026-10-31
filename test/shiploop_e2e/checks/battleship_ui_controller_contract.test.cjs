'use strict';

const assert = require('node:assert/strict');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const browserPath = path.join(__dirname, 'battleship_ui_browser.cjs');
const originalLoad = Module._load;
Module._load = function loadWithCellContract(request, parent, isMain) {
  if (parent && parent.filename === browserPath && request === './battleship_ui_contract.cjs') {
    return { cellNamePattern: () => /./, cellName: () => '' };
  }
  return Reflect.apply(originalLoad, this, [request, parent, isMain]);
};
let adapter;
try { adapter = require(browserPath); }
finally { Module._load = originalLoad; }

const {
  chooseControllerShotMatch, createApexControllerObserver, matchActionResponses,
  parseAuraRequestActions, parseAuraResponseActions, validateControllerPair,
} = adapter;

function executeAction(id, method, row, column, extras = {}, controller = 'ApexController', descriptor = 'aura://ApexActionController/ACTION$execute') {
  return {
    id,
    descriptor,
    params: {
      classname: controller, method,
      params: row === undefined ? extras : { row, column, ...extras },
    },
  };
}

function lastShot(row, col, result, ship = null, size = null) {
  return { row, col, result, ship, size };
}

function game(lastShotValue, shots, shipsLeft, gameOver, extras = {}) {
  return { lastShot: lastShotValue, shots, shipsLeft, gameOver, fleet: ['SECRET_FLEET'], ...extras };
}

function returned(lastShotValue, shots, shipsLeft, gameOver, extras = {}) {
  return game(lastShotValue, shots, shipsLeft, gameOver, extras);
}

function mockAuraRequest(url, id = 'origin;a') {
  return {
    method: () => 'POST',
    url: () => url,
    postData: () => JSON.stringify({ actions: [{
      id, descriptor: 'apex://SLTestController/ACTION$fire', params: { game: 'PRIVATE_GAME', row: 2, col: 6 },
    }] }),
  };
}

test('parses direct Apex descriptors and form encoded Aura messages without retaining request data', () => {
  const body = new URLSearchParams({
    message: JSON.stringify({ actions: [{
      id: '21;a', descriptor: 'apex://ApexController/ACTION$fire',
      params: { row: 2, col: 7, token: 'SECRET_POST_TOKEN' },
    }] }),
    'aura.token': 'SECRET_AURA_TOKEN',
  }).toString();
  const actions = parseAuraRequestActions(body, 'ApexController');
  assert.deepEqual(actions, [{ id: '21;a', controller: 'ApexController', method: 'fire', row: 2, column: 7 }]);
  assert.doesNotMatch(JSON.stringify(actions), /SECRET|fleet|aura\.token|message=/i);
});

test('parses ApexActionController execute params and a batched reset action', () => {
  const actions = parseAuraRequestActions({ actions: [
    executeAction('31;a', 'fire', 1, 4, { ignored: 'SECRET_PARAM' }, 'SLBattleController',
      'apex://ApexActionController/ACTION$execute'),
    executeAction('32;a', 'newGame', undefined, undefined, { ignored: 'SECRET_PARAM' }, 'SLBattleController'),
  ] }, 'SLBattleController');
  assert.deepEqual(actions, [
    { id: '31;a', controller: 'SLBattleController', method: 'fire', row: 1, column: 4 },
    { id: '32;a', controller: 'SLBattleController', method: 'newGame', row: null, column: null },
  ]);
});

test('ignores malformed, irrelevant, and wrong-controller requests', () => {
  assert.deepEqual(parseAuraRequestActions('message=%7Bnot-json', 'ApexController'), []);
  assert.deepEqual(parseAuraRequestActions({ actions: [{ id: '41;a', descriptor: 'aura://serverService/ACTION$fetch', params: {} }] }, 'ApexController'), []);
  assert.deepEqual(parseAuraRequestActions({ actions: [{
    id: '42;a', descriptor: 'apex://OtherController/ACTION$fire', params: { row: 1, column: 2 },
  }] }, 'ApexController'), []);
  assert.deepEqual(parseAuraRequestActions({ actions: [executeAction('43;a', 'fire', '1', 2)] }, 'ApexController'), []);
});

test('collector accepts the expected HTTPS host on default port', () => {
  const observer = createApexControllerObserver({ on: () => {} }, 'SLTestController', 'expected.lightning.force.com');
  observer.onRequest(mockAuraRequest('https://expected.lightning.force.com/aura?cache=1'));
  assert.equal(observer.records.length, 1);
  assert.deepEqual({ id: observer.records[0].request_id, row: observer.records[0].row,
    column: observer.records[0].column }, { id: 'origin;a', row: 2, column: 6 });
});

test('collector ignores foreign host, HTTP, suffix spoof, and nondefault port requests', () => {
  const urls = [
    'https://other.example/aura',
    'http://expected.lightning.force.com/aura',
    'https://expected.lightning.force.com.attacker.example/aura',
    'https://expected.lightning.force.com:8443/aura',
  ];
  for (const url of urls) {
    const observer = createApexControllerObserver({ on: () => {} }, 'SLTestController', 'expected.lightning.force.com');
    observer.onRequest(mockAuraRequest(url));
    assert.equal(observer.records.length, 0, url);
  }
});

test('correlates batched responses by action ID and keeps only returned game counters', () => {
  const requests = parseAuraRequestActions({ actions: [
    { id: '51;a', descriptor: 'apex://ApexController/ACTION$fire', params: { row: 0, column: 0 } },
    { id: '52;a', descriptor: 'apex://ApexController/ACTION$fire', params: { row: 0, column: 1 } },
  ] }, 'ApexController');
  const responses = parseAuraResponseActions({ actions: [
    { id: '52;a', state: 'SUCCESS', returnValue: returned(lastShot(0, 1, 'miss'), 2, 5, false, { response_secret: 'SECRET_RESPONSE' }) },
    { id: '51;a', state: 'SUCCESS', returnValue: returned(lastShot(0, 0, 'hit'), 1, 5, false, { response_secret: 'SECRET_RESPONSE' }) },
  ] });
  const pairs = matchActionResponses(requests, responses, true);
  assert.equal(pairs[0].response_id, '51;a');
  assert.equal(pairs[0].returned.last_shot.result, 'hit');
  assert.equal(pairs[1].response_id, '52;a');
  assert.equal(pairs[1].returned.shots, 2);
  assert.doesNotMatch(JSON.stringify({ requests, responses, pairs }), /SECRET|fleet|response_secret/i);
});

test('accepts duplicate valid fire requests when one matched response agrees with the clicked shot', () => {
  const request = { id: '55;a', method: 'fire', row: 4, column: 8 };
  const response = parseAuraResponseActions({ actions: [{
    id: '55;a', state: 'SUCCESS', returnValue: returned(lastShot(4, 8, 'miss'), 12, 2, false),
  }] });
  const valid = matchActionResponses([request], response, true)[0];
  const duplicateValid = { ...valid, sequence: 2 };
  const decision = chooseControllerShotMatch([valid, duplicateValid],
    { row: 4, column: 8, lastShot: 'miss', shots: 12, shipsLeft: 2, gameOver: false });
  assert.equal(decision.matched, valid);
  assert.equal(decision.reason, null);
});

test('rejects a retry group when none of its fire responses validates', () => {
  const request = { id: '56;a', method: 'fire', row: 4, column: 8 };
  const response = parseAuraResponseActions({ actions: [{
    id: '56;a', state: 'SUCCESS', returnValue: returned(lastShot(4, 8, 'miss'), 11, 2, false),
  }] });
  const invalidCounters = matchActionResponses([request], response, true)[0];
  const invalidCoordinates = { ...invalidCounters,
    returned: { ...invalidCounters.returned, last_shot: lastShot(4, 7, 'miss') } };
  const decision = chooseControllerShotMatch([invalidCounters, invalidCoordinates],
    { row: 4, column: 8, lastShot: 'miss', shots: 12, shipsLeft: 2, gameOver: false });
  assert.equal(decision.matched, null);
  assert.equal(decision.reason, 'controller-counters-mismatch');
});

test('keeps duplicate response IDs in one envelope as ambiguous and unusable', () => {
  const request = { id: '57;a', method: 'fire', row: 4, column: 8 };
  const responses = parseAuraResponseActions({ actions: [
    { id: '57;a', state: 'SUCCESS', returnValue: returned(lastShot(4, 8, 'miss'), 12, 2, false) },
    { id: '57;a', state: 'SUCCESS', returnValue: returned(lastShot(4, 8, 'miss'), 12, 2, false) },
  ] });
  const pair = matchActionResponses([request], responses, true)[0];
  assert.equal(pair.response_id, null);
  assert.equal(validateControllerPair(pair,
    { row: 4, column: 8, lastShot: 'miss', shots: 12, shipsLeft: 2, gameOver: false }),
  'controller-response-id-mismatch');
});

test('rejects mismatched IDs, request coordinates, unsuccessful calls, and mismatched counters', () => {
  const request = { id: '61;a', method: 'fire', row: 3, column: 6 };
  const pair = (responseId, state, result, httpOk = true) => matchActionResponses([request],
    parseAuraResponseActions({ actions: [{ id: responseId, state, returnValue: result }] }), httpOk)[0];
  const expected = { row: 3, column: 6, lastShot: 'miss', shots: 9, shipsLeft: 4, gameOver: false };

  assert.equal(validateControllerPair(pair('wrong;a', 'SUCCESS', returned(lastShot(3, 6, 'miss'), 9, 4, false)), expected),
    'controller-response-id-mismatch');
  assert.equal(validateControllerPair(pair('61;a', 'ERROR', returned(lastShot(3, 6, 'miss'), 9, 4, false)), expected),
    'controller-response-unsuccessful');
  assert.equal(validateControllerPair(pair('61;a', 'SUCCESS', null), expected), 'controller-response-invalid');
  const goodPair = pair('61;a', 'SUCCESS', returned(lastShot(3, 6, 'miss'), 9, 4, false));
  assert.equal(validateControllerPair({ ...goodPair, row: 3, column: 5 }, expected), 'controller-coordinate-mismatch');
  assert.equal(validateControllerPair({ ...goodPair, returned: { ...goodPair.returned, shots: 8 } }, expected),
    'controller-counters-mismatch');
  assert.equal(validateControllerPair({ ...goodPair, http_ok: false }, expected), 'controller-response-unsuccessful');
});

test('accepts a successful reset response only when all initial-state fields match', () => {
  const resetRequest = { id: '71;a', method: 'newGame', row: null, column: null };
  const resetResponse = parseAuraResponseActions({ actions: [{
    id: '71;a', state: 'SUCCESS', returnValue: returned(null, 0, 5, false),
  }] });
  const resetPair = matchActionResponses([resetRequest], resetResponse, true)[0];
  assert.equal(validateControllerPair(resetPair, { initial: true }), null);
  assert.equal(validateControllerPair({ ...resetPair, returned: { ...resetPair.returned, game_over: true } },
    { initial: true }), 'controller-initial-state-mismatch');
});

test('accepts JSON-string, direct-object, and one-level ApexActionController wrapper game returns', () => {
  const state = game(lastShot(2, 7, 'sunk', 'destroyer', 2), 17, 0, true);
  const stringState = JSON.stringify(state);
  const responses = parseAuraResponseActions({ actions: [
    { id: '75;a', state: 'SUCCESS', returnValue: stringState },
    { id: '76;a', state: 'SUCCESS', returnValue: state },
    { id: '77;a', state: 'SUCCESS', returnValue: { returnValue: stringState, wrapper_secret: 'SECRET_WRAPPER' } },
  ] });
  assert.deepEqual(responses.map(response => response.returned.last_shot), [
    lastShot(2, 7, 'sunk', 'destroyer', 2),
    lastShot(2, 7, 'sunk', 'destroyer', 2),
    lastShot(2, 7, 'sunk', 'destroyer', 2),
  ]);
  assert.doesNotMatch(JSON.stringify(responses), /SECRET|fleet|wrapper_secret/i);
});

test('rejects invalid game and lastShot data types', () => {
  const invalidLastShot = parseAuraResponseActions({ actions: [{
    id: '78;a', state: 'SUCCESS', returnValue: JSON.stringify(game('miss', 1, 5, false)),
  }] })[0];
  const pair = matchActionResponses([{ id: '78;a', method: 'fire', row: 0, column: 0 }], [invalidLastShot])[0];
  assert.equal(validateControllerPair(pair,
    { row: 0, column: 0, lastShot: 'miss', shots: 1, shipsLeft: 5, gameOver: false }),
  'controller-response-invalid');
  assert.equal(parseAuraResponseActions({ actions: [{
    id: '79;a', state: 'SUCCESS', returnValue: 'not-json',
  }] })[0].returned, null);
});

test('rejects returned lastShot coordinates that differ from the clicked request coordinate', () => {
  const request = { id: '80;a', method: 'fire', row: 3, column: 6 };
  const response = parseAuraResponseActions({ actions: [{
    id: '80;a', state: 'SUCCESS', returnValue: returned(lastShot(3, 5, 'miss'), 9, 4, false),
  }] });
  const pair = matchActionResponses([request], response, true)[0];
  assert.equal(validateControllerPair(pair,
    { row: 3, column: 6, lastShot: 'miss', shots: 9, shipsLeft: 4, gameOver: false }),
  'controller-last-shot-coordinate-mismatch');
});

test('parses an XSSI-prefixed Aura response transiently and emits no raw body data', () => {
  const raw = 'while(1);' + JSON.stringify({ actions: [{
    id: '81;a', state: 'SUCCESS', returnValue: JSON.stringify(game(lastShot(9, 9, 'sunk', 'destroyer', 2), 17, 0, true,
      { private_note: 'SECRET_RAW_BODY' })),
  }] });
  const responses = parseAuraResponseActions(raw);
  assert.equal(responses[0].returned.last_shot.result, 'sunk');
  assert.doesNotMatch(JSON.stringify(responses), /SECRET|fleet|private_note|while\(1\)/i);
});

test('checks lastShot result and gameOver in addition to request identity and counters', () => {
  const request = { id: '81;a', method: 'fire', row: 9, column: 9 };
  const response = parseAuraResponseActions({ actions: [{
    id: '81;a', state: 'SUCCESS', returnValue: returned(lastShot(9, 9, 'sunk', 'destroyer', 2), 17, 0, true),
  }] });
  const pair = matchActionResponses([request], response, true)[0];
  const expected = { row: 9, column: 9, lastShot: 'sunk', shots: 17, shipsLeft: 0, gameOver: true };
  assert.equal(validateControllerPair(pair, expected), null);
  assert.equal(validateControllerPair({ ...pair, returned: { ...pair.returned, last_shot: lastShot(9, 9, 'hit') } }, expected),
    'controller-last-shot-mismatch');
  assert.equal(validateControllerPair({ ...pair, returned: { ...pair.returned, game_over: false } }, expected),
    'controller-game-over-mismatch');
});
