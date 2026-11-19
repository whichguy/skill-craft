'use strict';

// Salesforce game interaction. The frontdoor URL is read
// from stdin and is never emitted, written, or included in an exception.
const fs = require('node:fs');
const path = require('node:path');
const uiContract = require('./battleship_ui_contract.cjs');

const SAFE_STAGES = new Set([
  'authenticate', 'route', 'render', 'fire-shot-count', 'fire-feedback',
  'play', 'game-over', 'reset', 'controller', 'browser',
]);
const SAFE_REASONS = new Set([
  'route-invalid', 'initial-board-invalid', 'shot-count-mismatch',
  'cell-state-mismatch', 'feedback-mismatch', 'ships-left-mismatch',
  'unfired-count-mismatch', 'premature-game-over', 'game-over-missing',
  'game-summary-mismatch', 'game-not-finished', 'reset-state-invalid', 'stale-game-over',
  'controller-config-invalid', 'controller-proof-missing', 'controller-new-game-missing',
  'controller-initial-state-mismatch', 'controller-fire-missing',
  'controller-response-missing', 'controller-response-id-mismatch',
  'controller-response-unsuccessful', 'controller-response-invalid',
  'controller-coordinate-mismatch', 'controller-last-shot-mismatch',
  'controller-last-shot-coordinate-mismatch', 'controller-counters-mismatch',
  'controller-game-over-mismatch', 'ui-check-failed',
]);
// Broad text scan only; the affirmative predicate below does not accept bare "winner".
const GAME_OVER_SCAN_PATTERN = /\bgame(?:\s+is)?\s+over\b|\byou\s+(?:win|won)\b|\bvictory\b|\bwinner\b/i;
const GAME_OVER_AFFIRMATIVE_PATTERN = /^(?:(?:the\s+)?game(?:\s+is)?\s+over|you\s+(?:win|won)|victory)$/i;
const GAME_OVER_SEGMENT_PATTERN = /[\r\n.!?;,:—–-]+/;
const SHOTS_PATTERN = /^Shots: (\d+)$/;
const SHIPS_PATTERN = /^Ships left: (\d+)$/;

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function safeControllerClass(value) {
  return typeof value === 'string' && /^[A-Za-z][A-Za-z0-9_.]{0,127}$/.test(value);
}

function normalizeExpectedHost(value) {
  if (typeof value !== 'string' || !value || value !== value.trim()) return null;
  try {
    const parsed = new URL(`https://${value}`);
    if (parsed.hostname.toLowerCase() !== value.toLowerCase() || parsed.port
        || parsed.pathname !== '/' || parsed.username || parsed.password) return null;
    return parsed.hostname.toLowerCase();
  } catch (_) { return null; }
}

function safeActionId(value) {
  return typeof value === 'string' && value.length <= 128 && /^[A-Za-z0-9._;:-]+$/.test(value);
}

function parseJson(value) {
  if (isRecord(value)) return value;
  if (typeof value !== 'string') return null;
  try {
    const parsed = JSON.parse(value);
    return isRecord(parsed) ? parsed : null;
  } catch (_) { return null; }
}

function auraEnvelope(value) {
  const text = typeof value === 'string' ? value.replace(/^\uFEFF/, '') : value;
  const stripped = typeof text === 'string' ? text.replace(/^\s*while\s*\(\s*1\s*\)\s*;\s*/, '') : text;
  let parsed = parseJson(stripped);
  if (!parsed && typeof value === 'string') {
    try {
      const message = new URLSearchParams(value).get('message');
      if (message !== null) parsed = parseJson(message);
    } catch (_) { /* malformed form body */ }
  }
  if (!parsed) return null;
  if (Array.isArray(parsed.actions)) return parsed;
  const message = typeof parsed.message === 'string' ? parseJson(parsed.message) : parsed.message;
  return isRecord(message) && Array.isArray(message.actions) ? message : null;
}

function actionArray(value) {
  const envelope = auraEnvelope(value);
  return envelope ? envelope.actions : [];
}

function actionCoordinates(params) {
  if (!isRecord(params)) return null;
  const row = params.row;
  const hasColumn = Object.hasOwn(params, 'column');
  const hasCol = Object.hasOwn(params, 'col');
  if (hasColumn && hasCol && params.column !== params.col) return null;
  const column = hasColumn ? params.column : params.col;
  if (!Number.isInteger(row) || !Number.isInteger(column)
      || row < 0 || row > 9 || column < 0 || column > 9) return null;
  return { row, column };
}

function parseAuraRequestActions(value, expectedController) {
  if (!safeControllerClass(expectedController)) return [];
  return actionArray(value).flatMap(action => {
    if (!isRecord(action) || !safeActionId(action.id) || typeof action.descriptor !== 'string') return [];
    let controller;
    let method;
    let params;
    const execute = /^(?:aura|apex):\/\/ApexActionController\/ACTION\$execute$/i.test(action.descriptor);
    const direct = /^apex:\/\/([^/]+)\/ACTION\$([A-Za-z][A-Za-z0-9_]*)$/i.exec(action.descriptor);
    if (execute && isRecord(action.params)) {
      controller = action.params.classname;
      method = action.params.method;
      params = action.params.params;
    } else if (direct) {
      controller = direct[1];
      method = direct[2];
      params = action.params;
    } else return [];
    if (controller !== expectedController || typeof method !== 'string') return [];
    const normalizedMethod = method.toLowerCase();
    if (!['fire', 'newgame', 'reset'].includes(normalizedMethod)) return [];
    if (normalizedMethod === 'fire') {
      const coordinates = actionCoordinates(params);
      if (!coordinates) return [];
      return [{ id: action.id, controller, method, ...coordinates }];
    }
    return [{ id: action.id, controller, method, row: null, column: null }];
  });
}

function parseGameJson(value) {
  if (typeof value !== 'string') return null;
  try {
    const parsed = JSON.parse(value);
    return isRecord(parsed) ? parsed : null;
  } catch (_) { return null; }
}

function normalizeLastShot(value) {
  if (value === null) return null;
  if (!isRecord(value) || !Number.isInteger(value.row) || value.row < 0 || value.row > 9
      || !Number.isInteger(value.col) || value.col < 0 || value.col > 9
      || !['hit', 'miss', 'sunk'].includes(value.result)
      || !Object.hasOwn(value, 'ship') || !Object.hasOwn(value, 'size')) return undefined;
  if (value.result === 'sunk') {
    const sizes = { carrier: 5, battleship: 4, cruiser: 3, submarine: 3, destroyer: 2 };
    if (typeof value.ship !== 'string' || !Object.hasOwn(sizes, value.ship)
        || value.size !== sizes[value.ship]) return undefined;
  } else if (value.ship !== null || value.size !== null) return undefined;
  return { row: value.row, col: value.col, result: value.result, ship: value.ship, size: value.size };
}

function unwrapGameValue(value) {
  let parsed = typeof value === 'string' ? parseGameJson(value) : value;
  if (isRecord(parsed) && !Object.hasOwn(parsed, 'shots')
      && typeof parsed.returnValue === 'string') {
    // ApexActionController may wrap the Apex String once in returnValue.
    parsed = parseGameJson(parsed.returnValue);
  }
  return parsed;
}

function normalizeGameState(value) {
  const game = unwrapGameValue(value);
  if (!isRecord(game) || !Object.hasOwn(game, 'lastShot')
      || !Object.hasOwn(game, 'shots') || !Object.hasOwn(game, 'shipsLeft')
      || !Object.hasOwn(game, 'gameOver')) return null;
  const lastShot = normalizeLastShot(game.lastShot);
  if (lastShot === undefined
      || !Number.isInteger(game.shots) || game.shots < 0 || game.shots > 100
      || !Number.isInteger(game.shipsLeft) || game.shipsLeft < 0 || game.shipsLeft > 5
      || typeof game.gameOver !== 'boolean') return null;
  return { last_shot: lastShot, shots: game.shots, ships_left: game.shipsLeft, game_over: game.gameOver };
}

function parseAuraResponseActions(value) {
  return actionArray(value).flatMap(action => {
    if (!isRecord(action) || !safeActionId(action.id)) return [];
    const state = typeof action.state === 'string' && ['SUCCESS', 'ERROR', 'INCOMPLETE'].includes(action.state)
      ? action.state : 'OTHER';
    return [{ id: action.id, state, returned: normalizeGameState(action.returnValue) }];
  });
}

function matchActionResponses(requestActions, responseActions, httpOk = true) {
  return requestActions.map(request => {
    const matches = responseActions.filter(response => response.id === request.id);
    const matched = matches.length === 1 ? matches[0] : null;
    return {
      method: request.method,
      request_id: request.id,
      row: request.row,
      column: request.column,
      response_id: matched ? matched.id : null,
      response_state: matched ? matched.state : 'ID_MISMATCH',
      http_ok: httpOk === true,
      returned: matched ? matched.returned : null,
    };
  });
}

function validateControllerPair(pair, expected) {
  if (pair.response_state === 'PENDING') return 'PENDING';
  if (!pair.response_id || pair.response_id !== pair.request_id) return 'controller-response-id-mismatch';
  if (pair.response_state === 'INVALID') return 'controller-response-invalid';
  if (pair.response_state !== 'SUCCESS' || !pair.http_ok) return 'controller-response-unsuccessful';
  if (!pair.returned) return 'controller-response-invalid';
  if (expected.initial === true) {
    if (!['newgame', 'reset'].includes(pair.method.toLowerCase())
        || pair.returned.last_shot !== null || pair.returned.shots !== 0
        || pair.returned.ships_left !== 5 || pair.returned.game_over !== false) {
      return 'controller-initial-state-mismatch';
    }
    return null;
  }
  if (pair.method.toLowerCase() !== 'fire') return 'controller-response-invalid';
  if (pair.row !== expected.row || pair.column !== expected.column) return 'controller-coordinate-mismatch';
  const lastShot = pair.returned.last_shot;
  if (!lastShot || lastShot.row !== expected.row || lastShot.col !== expected.column) {
    return 'controller-last-shot-coordinate-mismatch';
  }
  if (lastShot.result !== expected.lastShot) return 'controller-last-shot-mismatch';
  if (pair.returned.shots !== expected.shots || pair.returned.ships_left !== expected.shipsLeft) {
    return 'controller-counters-mismatch';
  }
  if (pair.returned.game_over !== expected.gameOver) return 'controller-game-over-mismatch';
  return null;
}

function chooseControllerShotMatch(candidates, expected) {
  const checked = candidates.map(pair => ({ pair, reason: validateControllerPair(pair, expected) }));
  const match = checked.find(item => item.reason === null);
  if (match) return { matched: match.pair, reason: null };
  const failure = checked.find(item => item.reason !== 'PENDING');
  return { matched: null, reason: failure ? failure.reason : (checked.length ? 'PENDING' : 'controller-fire-missing') };
}

function controllerObservation(pair, includeCoordinates = true) {
  const observation = {
    method: pair.method,
    request_id: pair.request_id,
    response_id: pair.response_id,
  };
  if (includeCoordinates) {
    observation.row = pair.row;
    observation.column = pair.column;
  }
  Object.assign(observation, pair.returned);
  return observation;
}

class ApexControllerObserver {
  constructor(page, controllerClass, timeoutMs = 20000, expectedHost) {
    this.page = page;
    this.controllerClass = controllerClass;
    this.timeoutMs = timeoutMs;
    this.expectedHost = normalizeExpectedHost(expectedHost);
    this.records = [];
    this.requestRecords = new WeakMap();
    this.initialCall = null;
  }

  attach() {
    if (!safeControllerClass(this.controllerClass) || !this.expectedHost) {
      throw stageError('controller', 'controller-config-invalid');
    }
    this.page.on('request', request => this.onRequest(request));
    this.page.on('response', response => { void this.onResponse(response); });
  }

  mark() { return this.records.length; }

  onRequest(request) {
    try {
      const url = new URL(request.url());
      if (url.protocol !== 'https:' || url.hostname.toLowerCase() !== this.expectedHost || url.port) return;
      if (request.method().toUpperCase() !== 'POST' || url.pathname !== '/aura') return;
      const actions = parseAuraRequestActions(request.postData(), this.controllerClass);
      if (!actions.length) return;
      const records = actions.map(action => {
        const record = {
          sequence: this.records.length,
          method: action.method,
          request_id: action.id,
          row: action.row,
          column: action.column,
          response_id: null,
          response_state: 'PENDING',
          http_ok: false,
          returned: null,
        };
        this.records.push(record);
        return record;
      });
      this.requestRecords.set(request, records);
    } catch (_) { /* network details never escape the adapter */ }
  }

  async onResponse(response) {
    try {
      const request = response.request();
      const records = this.requestRecords.get(request);
      if (!records) return;
      let responseActions;
      try { responseActions = parseAuraResponseActions(await response.text()); }
      catch (_) {
        for (const record of records) record.response_state = 'INVALID';
        return;
      }
      const pairs = matchActionResponses(records.map(record => ({
        id: record.request_id, method: record.method, row: record.row, column: record.column,
      })), responseActions, response.status() >= 200 && response.status() < 300);
      pairs.forEach((pair, index) => Object.assign(records[index], pair));
    } catch (_) { /* emit only a safe adapter reason when the caller checks the observation */ }
  }

  async waitForInitialState() {
    const deadline = Date.now() + this.timeoutMs;
    let lastFailure = 'controller-initial-state-mismatch';
    while (Date.now() < deadline) {
      const candidates = this.records.filter(record => ['newgame', 'reset'].includes(record.method.toLowerCase()));
      for (const candidate of candidates) {
        const reason = validateControllerPair(candidate, { initial: true });
        if (reason === null) {
          this.initialCall = controllerObservation(candidate, false);
          return this.initialCall;
        }
        if (reason !== 'PENDING') lastFailure = reason;
      }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw stageError('controller', this.records.some(record => ['newgame', 'reset'].includes(record.method.toLowerCase()))
      ? lastFailure : 'controller-new-game-missing');
  }

  async waitForShot(cursor, expected) {
    const deadline = Date.now() + this.timeoutMs;
    while (Date.now() < deadline) {
      const candidates = this.records.filter(record => record.sequence >= cursor && record.method.toLowerCase() === 'fire');
      const decision = chooseControllerShotMatch(candidates, expected);
      if (decision.matched) return controllerObservation(decision.matched);
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    const candidates = this.records.filter(record => record.sequence >= cursor && record.method.toLowerCase() === 'fire');
    const decision = chooseControllerShotMatch(candidates, expected);
    const reason = !candidates.length ? 'controller-fire-missing'
      : candidates.some(record => record.response_state === 'PENDING') ? 'controller-response-missing'
        : decision.reason || 'controller-response-invalid';
    throw stageError('controller', reason, expected);
  }
}

function createApexControllerObserver(page, controllerClass, expectedHost) {
  const observer = new ApexControllerObserver(page, controllerClass, 20000, expectedHost);
  observer.attach();
  return observer;
}

function hasGameOverMarker(text) {
  if (typeof text !== 'string') return false;
  // Accept Game over, You win/won, or Victory as a heading or clause ending at punctuation/end.
  return text.split(GAME_OVER_SEGMENT_PATTERN).some(segment => GAME_OVER_AFFIRMATIVE_PATTERN.test(segment.trim()));
}

function playwrightModule() {
  const nodePath = process.env.PLAYWRIGHT_NODE_PATH;
  if (nodePath) return require(nodePath);
  const explicit = process.env.PLAYWRIGHT_MODULE_PATH;
  if (explicit) return require(explicit);
  try { return require('playwright'); } catch (_) { /* use the installed runtime fallback below */ }
  const roots = [path.join(process.env.HOME || '', '.cache', 'codex-runtimes')];
  for (const root of roots) {
    try {
      for (const runtime of fs.readdirSync(root)) {
        const candidate = path.join(root, runtime, 'dependencies', 'node', 'node_modules', 'playwright');
        if (fs.existsSync(candidate)) return require(candidate);
      }
    } catch (_) { /* absent runtime cache */ }
  }
  throw new Error('Playwright is unavailable');
}

function browserExecutable() {
  if (process.env.BROWSER_EXECUTABLE_PATH) return process.env.BROWSER_EXECUTABLE_PATH;
  for (const candidate of [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  ]) if (fs.existsSync(candidate)) return candidate;
  return undefined; // Playwright may use its already-installed bundled browser.
}

function stageError(stage, reason = 'ui-check-failed', context = {}) {
  const error = new Error(`UI evaluation failed at ${stage}`);
  error.stage = SAFE_STAGES.has(stage) ? stage : 'browser';
  error.reason = SAFE_REASONS.has(reason) ? reason : 'ui-check-failed';
  for (const key of ['shot_index', 'row', 'column']) {
    if (Number.isInteger(context[key])) error[key] = context[key];
  }
  return error;
}

async function atStage(stage, work, context = {}) {
  try { return await work(); } catch (error) {
    if (error && SAFE_STAGES.has(error.stage) && SAFE_REASONS.has(error.reason)) throw error;
    throw stageError(stage, 'ui-check-failed', context);
  }
}

async function firstVisible(locator, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const count = await locator.count();
    for (let index = 0; index < count; index += 1) {
      const candidate = locator.nth(index);
      if (await candidate.isVisible()) return candidate;
    }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error('Expected visible UI element');
}

async function visibleText(page, text) {
  const match = await firstVisible(page.getByText(text, { exact: true }));
  return (await match.innerText()).trim();
}

async function visibleCounter(page, pattern) {
  const locator = page.getByText(pattern);
  const count = await locator.count();
  for (let index = 0; index < count; index += 1) {
    const candidate = locator.nth(index);
    if (!await candidate.isVisible()) continue;
    const match = pattern.exec((await candidate.innerText()).trim());
    if (match) return Number(match[1]);
  }
  return null;
}

async function waitForShotCompletion(page, shotIndex, row, column) {
  const context = { shot_index: shotIndex, row, column };
  const unfired = page.getByRole('button', {
    name: uiContract.cellName(row, column, 'unfired'), exact: true,
  });
  try {
    await Promise.all([
      page.getByText(`Shots: ${shotIndex}`, { exact: true }).waitFor({ state: 'visible' }),
      unfired.waitFor({ state: 'detached' }),
    ]);
  } catch (_) {
    throw stageError('play', 'shot-count-mismatch', context);
  }
  if (await visibleCounter(page, SHOTS_PATTERN) !== shotIndex) {
    throw stageError('play', 'shot-count-mismatch', context);
  }
}

async function waitForShipsLeft(page, expected, context) {
  try {
    await page.getByText(`Ships left: ${expected}`, { exact: true }).waitFor({ state: 'visible' });
  } catch (_) {
    throw stageError('play', 'ships-left-mismatch', context);
  }
  if (await visibleCounter(page, SHIPS_PATTERN) !== expected) {
    throw stageError('play', 'ships-left-mismatch', context);
  }
}

async function visibleGameOverMessages(page) {
  const matches = page.getByText(GAME_OVER_SCAN_PATTERN);
  const count = await matches.count();
  const texts = [];
  for (let index = 0; index < count; index += 1) {
    const candidate = matches.nth(index);
    if (!await candidate.isVisible()) continue;
    const text = (await candidate.innerText()).replace(/\s+/g, ' ').trim();
    if (!hasGameOverMarker(text)) continue;
    const hasMatchingDescendant = await candidate.evaluate((element, patterns) => {
      const marker = new RegExp(patterns.marker, 'i');
      const segments = new RegExp(patterns.segments);
      const hasMarker = value => typeof value === 'string'
        && value.split(segments).some(segment => marker.test(segment.trim()));
      const normalized = value => (value || '').replace(/\s+/g, ' ').trim();
      const containsMatch = root => {
        const children = Array.from(root.children || []);
        for (const child of children) {
          const style = getComputedStyle(child);
          const visible = style.display !== 'none' && style.visibility !== 'hidden'
            && child.getClientRects().length > 0;
          if (visible && hasMarker(normalized(child.innerText))) return true;
          if (child.shadowRoot && containsMatch(child.shadowRoot)) return true;
          if (containsMatch(child)) return true;
        }
        return false;
      };
      return containsMatch(element);
    }, { marker: GAME_OVER_AFFIRMATIVE_PATTERN.source, segments: GAME_OVER_SEGMENT_PATTERN.source });
    if (!hasMatchingDescendant) texts.push(text);
  }
  return new Set(texts);
}

function newMessages(current, baseline) {
  return [...current].filter(text => !baseline.has(text));
}

function sameMessages(left, right) {
  return left.size === right.size && [...left].every(text => right.has(text));
}

async function waitForNewGameOver(page, initialMessages, afterFourthSinkMessages, context) {
  const deadline = Date.now() + 10000;
  let current = await visibleGameOverMessages(page);
  while (Date.now() < deadline) {
    const unseenAtStart = newMessages(current, initialMessages);
    const unseenAfterFourth = newMessages(current, afterFourthSinkMessages);
    if (unseenAtStart.length && unseenAfterFourth.length) return current;
    await new Promise(resolve => setTimeout(resolve, 200));
    current = await visibleGameOverMessages(page);
  }
  throw stageError('game-over', 'game-over-missing', context);
}

async function waitForResetMessages(page, initialMessages) {
  const deadline = Date.now() + 10000;
  let current = await visibleGameOverMessages(page);
  while (Date.now() < deadline) {
    if (sameMessages(current, initialMessages)) return current;
    await new Promise(resolve => setTimeout(resolve, 200));
    current = await visibleGameOverMessages(page);
  }
  throw stageError('reset', 'stale-game-over');
}

async function waitForCellCount(locator, want) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    if (await locator.count() === want) return;
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error('Unexpected board cell count');
}

async function verifyCellNames(page, state) {
  let unique = 0;
  let matched = true;
  let allEnabled = true;
  for (let row = 0; row < 10; row += 1) {
    for (let column = 0; column < 10; column += 1) {
      const locator = page.getByRole('button', {
        name: uiContract.cellName(row, column, state), exact: true,
      });
      const count = await locator.count();
      if (count === 1) {
        unique += 1;
        allEnabled = allEnabled && await locator.isEnabled();
      }
      else matched = false;
    }
  }
  return { unique, matched: matched && unique === 100, allEnabled };
}

// The page must already be on the board route. Keeping this exercise separate
// lets a local page rehearse the same visible contract without Salesforce auth.
async function exerciseBoard(page, request, controllerObserver = null) {
  if (!request || typeof request.prefix !== 'string') throw stageError('route', 'route-invalid');
  const requireController = request.require_controller === true;
  if (requireController && !controllerObserver) throw stageError('controller', 'controller-proof-missing');
  if (requireController && (!safeControllerClass(request.controller_class)
      || controllerObserver.controllerClass !== request.controller_class
      || controllerObserver.expectedHost !== normalizeExpectedHost(request.expected_lightning_host))) {
    throw stageError('controller', 'controller-config-invalid');
  }
  const expectedPath = `/lightning/n/${encodeURIComponent(request.prefix + '_Board')}`;
  await atStage('route', async () => {
    const current = new URL(page.url());
    if ((request.expected_lightning_host && current.hostname !== request.expected_lightning_host)
        || current.pathname !== expectedPath) throw stageError('route', 'route-invalid');
  });

  const initial = await atStage('render', async () => {
    await firstVisible(page.getByRole('button', { name: 'New game', exact: true }));
    await visibleText(page, 'Shots: 0');
    await visibleText(page, 'Ships left: 5');
    const cells = page.getByRole('button', { name: uiContract.cellNamePattern() });
    await waitForCellCount(cells, 100);
    const grid = await verifyCellNames(page, 'unfired');
    const allEnabled = grid.allEnabled;
    const firstEnabled = await page.getByRole('button', {
      name: uiContract.cellName(0, 0, 'unfired'), exact: true,
    }).isEnabled();
    if (!grid.matched || await cells.count() !== 100 || !allEnabled || !firstEnabled) {
      throw stageError('render', 'initial-board-invalid');
    }
    return { grid, gameOverMessages: await visibleGameOverMessages(page) };
  });

  const initialControllerObservation = requireController
    ? await atStage('controller', () => controllerObserver.waitForInitialState()) : null;
  const initialGameOverMessages = initial.gameOverMessages;
  let afterFourthSinkMessages = null;
  let shipsLeft = 5;
  let sinkCount = 0;
  let hitOrSunkCount = 0;
  let finalUnfiredCount = 100;
  let finalGameOverMessages = null;
  const shotObservations = [];
  const controllerShotObservations = [];

  for (let row = 0; row < 10 && sinkCount < 5; row += 1) {
    for (let column = 0; column < 10 && sinkCount < 5; column += 1) {
      const shotIndex = shotObservations.length + 1;
      const shotContext = { shot_index: shotIndex, row, column };
      const beforeMessages = await atStage('game-over', () => visibleGameOverMessages(page), shotContext);
      if (newMessages(beforeMessages, initialGameOverMessages).length) {
        throw stageError('game-over', 'premature-game-over', shotContext);
      }

      const controllerCursor = requireController ? controllerObserver.mark() : null;
      const startedAt = Date.now();
      const result = await atStage('play', async () => {
        const unfiredCell = page.getByRole('button', {
          name: uiContract.cellName(row, column, 'unfired'), exact: true,
        });
        await unfiredCell.click(); // Playwright waits for real busy/disabled UI to become actionable.
        await waitForShotCompletion(page, shotIndex, row, column);

        let match;
        try {
          match = await firstVisible(page.getByText(/^Shot result: (hit|miss|sunk)$/i));
        } catch (_) {
          throw stageError('play', 'feedback-mismatch', shotContext);
        }
        const feedback = (await match.innerText()).trim().toLowerCase();
        const state = feedback.slice('Shot result: '.length);
        if (!['hit', 'miss', 'sunk'].includes(state)) {
          throw stageError('play', 'feedback-mismatch', shotContext);
        }
        const firedCell = page.getByRole('button', {
          name: uiContract.cellName(row, column, state), exact: true,
        });
        if (await firedCell.count() !== 1) throw stageError('play', 'cell-state-mismatch', shotContext);

        const nextShipsLeft = shipsLeft - (state === 'sunk' ? 1 : 0);
        await waitForShipsLeft(page, nextShipsLeft, shotContext);
        const unfiredCells = page.getByRole('button', {
          name: uiContract.cellNamePattern('unfired'),
        });
        const unfiredCount = await unfiredCells.count();
        if (unfiredCount !== 100 - shotIndex) {
          throw stageError('play', 'unfired-count-mismatch', shotContext);
        }
        return {
          state,
          shipsLeftAfter: nextShipsLeft,
          unfiredCount,
          firedCellDisabled: await firedCell.isDisabled(),
        };
      }, shotContext);

      if (requireController) {
        controllerShotObservations.push(await atStage('controller', () => controllerObserver.waitForShot(
          controllerCursor,
          { row, column, shots: shotIndex, shipsLeft: result.shipsLeftAfter,
            lastShot: result.state, gameOver: result.shipsLeftAfter === 0 },
        ), shotContext));
      }

      shipsLeft = result.shipsLeftAfter;
      if (result.state === 'sunk') sinkCount += 1;
      if (result.state !== 'miss') hitOrSunkCount += 1;
      finalUnfiredCount = result.unfiredCount;
      shotObservations.push({
        shot_index: shotIndex,
        row,
        column,
        duration_ms: Date.now() - startedAt,
        result: result.state,
        ships_left_after: shipsLeft,
        unfired_cells_after: result.unfiredCount,
        fired_cell_disabled: result.firedCellDisabled,
      });

      const currentMessages = await atStage('game-over', () => visibleGameOverMessages(page), shotContext);
      if (sinkCount < 5 && newMessages(currentMessages, initialGameOverMessages).length) {
        throw stageError('game-over', 'premature-game-over', shotContext);
      }
      if (sinkCount === 4) afterFourthSinkMessages = currentMessages;
      if (sinkCount === 5) {
        if (shipsLeft !== 0 || hitOrSunkCount !== 17) {
          throw stageError('play', 'game-summary-mismatch', shotContext);
        }
        if (!afterFourthSinkMessages) afterFourthSinkMessages = currentMessages;
        finalGameOverMessages = await waitForNewGameOver(
          page, initialGameOverMessages, afterFourthSinkMessages, shotContext,
        );
      }
    }
  }

  if (sinkCount !== 5 || shipsLeft !== 0 || hitOrSunkCount !== 17 || !finalGameOverMessages) {
    const last = shotObservations[shotObservations.length - 1];
    throw stageError(shotObservations.length === 100 ? 'game-over' : 'play',
      shotObservations.length === 100 ? 'game-not-finished' : 'game-summary-mismatch', {
      shot_index: shotObservations.length || 1,
      row: last ? last.row : 0,
      column: last ? last.column : 0,
    });
  }

  const fourthSinkNewMessages = newMessages(afterFourthSinkMessages, initialGameOverMessages);
  const finalNewMessages = newMessages(finalGameOverMessages, initialGameOverMessages)
    .filter(text => !afterFourthSinkMessages.has(text));
  if (fourthSinkNewMessages.length || !finalNewMessages.length) {
    const last = shotObservations[shotObservations.length - 1];
    throw stageError('game-over', fourthSinkNewMessages.length ? 'premature-game-over' : 'game-over-missing', {
      shot_index: shotObservations.length,
      row: last.row,
      column: last.column,
    });
  }
  const finalShot = shotObservations[shotObservations.length - 1];
  await atStage('game-over', async () => {
    if (request.game_over_screenshot) {
      await page.screenshot({ path: request.game_over_screenshot, fullPage: true });
    }
  }, { shot_index: finalShot.shot_index, row: finalShot.row, column: finalShot.column });

  const reset = await atStage('reset', async () => {
    await page.getByRole('button', { name: 'New game', exact: true }).click();
    await visibleText(page, 'Shots: 0');
    await visibleText(page, 'Ships left: 5');
    const cells = page.getByRole('button', { name: uiContract.cellNamePattern('unfired') });
    await waitForCellCount(cells, 100);
    const grid = await verifyCellNames(page, 'unfired');
    const allEnabled = grid.allEnabled;
    const firstEnabled = await page.getByRole('button', {
      name: uiContract.cellName(0, 0, 'unfired'), exact: true,
    }).isEnabled();
    if (!grid.matched || await cells.count() !== 100 || !allEnabled || !firstEnabled) {
      throw stageError('reset', 'reset-state-invalid');
    }
    const gameOverMessages = await waitForResetMessages(page, initialGameOverMessages);
    if (request.screenshot) await page.screenshot({ path: request.screenshot, fullPage: true });
    return { grid, firstEnabled, gameOverMessages };
  });
  const observedRoute = await atStage('route', async () => {
    const current = new URL(page.url());
    if ((request.expected_lightning_host && current.hostname !== request.expected_lightning_host)
        || current.pathname !== expectedPath) throw stageError('route', 'route-invalid');
    return { host: current.hostname, path: current.pathname };
  });

  return {
    route_host: observedRoute.host,
    route_path: observedRoute.path,
    initial_cells: 100,
    initial_unique_cells: initial.grid.unique,
    initial_all_enabled: true,
    initial_labels_matched: initial.grid.matched,
    initial_shots: 0,
    initial_ships: 5,
    shots_played: shotObservations.length,
    sink_count: sinkCount,
    hit_or_sunk_shots: hitOrSunkCount,
    final_ships_left: shipsLeft,
    final_unfired_cells: finalUnfiredCount,
    shot_observations: shotObservations,
    game_over_initial_message_count: initialGameOverMessages.size,
    game_over_after_fourth_sink_message_count: afterFourthSinkMessages.size,
    game_over_after_fourth_sink_new_message_count: fourthSinkNewMessages.length,
    game_over_final_message_count: finalGameOverMessages.size,
    game_over_final_new_message_count: finalNewMessages.length,
    game_over_new_message_observed: finalNewMessages.length > 0,
    game_over_after_reset_message_count: reset.gameOverMessages.size,
    game_over_after_reset_matches_initial: sameMessages(reset.gameOverMessages, initialGameOverMessages),
    reset_cells: 100,
    reset_unique_cells: reset.grid.unique,
    reset_all_enabled: true,
    reset_labels_matched: reset.grid.matched,
    reset_cell_enabled: reset.firstEnabled,
    reset_shots: 0,
    reset_ships: 5,
    controller_proof_scope: requireController ? 'apex-controller-and-dom' : 'dom-only',
    controller_proof: requireController ? {
      controller_class: controllerObserver.controllerClass,
      new_game: initialControllerObservation,
      shots: controllerShotObservations,
    } : null,
    browser_version: page.context().browser() ? page.context().browser().version() : '',
  };
}

async function main() {
  let browser;
  let stage = 'browser';
  try {
    let input = '';
    for await (const chunk of process.stdin) input += chunk;
    const request = JSON.parse(input);
    if (!request || typeof request.login_url !== 'string' || !/^https:\/\//i.test(request.login_url)
        || typeof request.expected_lightning_host !== 'string' || typeof request.prefix !== 'string') {
      throw stageError('authenticate');
    }
    if (!safeControllerClass(request.controller_class) || !normalizeExpectedHost(request.expected_lightning_host)) {
      throw stageError('controller', 'controller-config-invalid');
    }
    const { chromium } = playwrightModule();
    browser = await chromium.launch({ headless: true, ...(browserExecutable() ? { executablePath: browserExecutable() } : {}) });
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(20000);
    const controllerObserver = createApexControllerObserver(
      page, request.controller_class, request.expected_lightning_host,
    );

    stage = 'authenticate';
    await page.goto(request.login_url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForURL(url => url.hostname === request.expected_lightning_host
      && url.hostname.endsWith('.lightning.force.com') && !url.pathname.includes('frontdoor'), { timeout: 60000 });
    const host = new URL(page.url()).hostname;

    stage = 'route';
    await page.goto(`https://${host}/lightning/n/${encodeURIComponent(request.prefix + '_Board')}`, {
      waitUntil: 'domcontentloaded', timeout: 60000,
    });
    const observation = await exerciseBoard(page, { ...request, require_controller: true }, controllerObserver);
    observation.browser_version = browser.version();
    await context.close();
    process.stdout.write(JSON.stringify(observation) + '\n');
  } catch (error) {
    const reportedStage = SAFE_STAGES.has(error && error.stage) ? error.stage : stage;
    const reason = SAFE_REASONS.has(error && error.reason) ? error.reason : 'ui-check-failed';
    const failure = { status: 'failed', stage: reportedStage, reason };
    for (const key of ['shot_index', 'row', 'column']) {
      if (Number.isInteger(error && error[key])) failure[key] = error[key];
    }
    process.stdout.write(JSON.stringify(failure) + '\n');
    process.exitCode = 1;
  } finally {
    if (browser) {
      try { await browser.close(); } catch (_) { /* keep close errors out of diagnostics */ }
    }
  }
}

module.exports = {
  exerciseBoard, hasGameOverMarker, playwrightModule, browserExecutable, SAFE_STAGES, SAFE_REASONS,
  parseAuraRequestActions, parseAuraResponseActions, matchActionResponses,
  validateControllerPair, chooseControllerShotMatch, controllerObservation, createApexControllerObserver,
};
if (require.main === module) main();
