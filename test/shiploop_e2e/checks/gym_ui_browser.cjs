'use strict';

// Share only Battleship's pinned-runtime discovery. Gym Aura parsing remains local.
const pinnedBrowserRuntime = require('./battleship_ui_browser.cjs');

const METHODS = new Set([
  'getMyMembership', 'saveMyMembership', 'setMyStatus', 'adminSave',
  'listMembers', 'member360', 'checkIn',
]);
const REQUIRED_MUTATION_METHODS = new Set([
  'saveMyMembership', 'setMyStatus', 'adminSave', 'checkIn',
]);
const STATUSES = new Set(['Active', 'Frozen', 'Cancelled']);
const PLANS = new Set(['Basic', 'Coached']);
const SAFE_STAGES = new Set([
  'authenticate', 'route', 'render', 'self-membership', 'admin-member',
  'coaching', 'status-refusal', 'basic-checkin', 'reload', 'controller', 'browser',
]);
const SAFE_REASONS = new Set([
  'route-invalid', 'aura-request-invalid', 'controller-method-invalid',
  'controller-params-invalid', 'controller-host-invalid', 'controller-id-invalid',
  'controller-response-missing', 'controller-response-id-mismatch',
  'controller-response-unsuccessful', 'controller-response-invalid',
  'ui-control-missing', 'ui-state-invalid', 'ui-check-failed',
]);
const SF_ID = /^[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?$/;
const ACTION_ID = /^[A-Za-z0-9._;:-]{1,128}$/;
const PREFIX_RE = /^[A-Za-z][A-Za-z0-9_]{0,39}$/;

function stageError(stage, reason) {
  const error = new Error('Gym UI check failed');
  error.stage = SAFE_STAGES.has(stage) ? stage : 'browser';
  error.reason = SAFE_REASONS.has(reason) ? reason : 'ui-check-failed';
  return error;
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function sortedKeys(value) {
  return Object.keys(value).sort();
}

function exactKeys(value, expected) {
  return isRecord(value) && JSON.stringify(sortedKeys(value)) === JSON.stringify([...expected].sort());
}

function parseRecord(value) {
  if (isRecord(value)) return value;
  if (typeof value !== 'string') return null;
  try {
    const parsed = JSON.parse(value);
    return isRecord(parsed) ? parsed : null;
  } catch (_) {
    return null;
  }
}

function decodeAuraActions(body, reason) {
  if (typeof body !== 'string' || !body) throw stageError('controller', reason);
  const source = body.replace(/^\uFEFF/, '').trim()
    .replace(/^\s*while\s*\(\s*1\s*\)\s*;\s*/, '')
    .replace(/^\)\]\}',?\s*/, '');
  let parsed = parseRecord(source);
  if (!parsed) {
    try {
      const form = new URLSearchParams(body);
      const messages = form.getAll('message');
      if (messages.length !== 1) throw stageError('controller', reason);
      parsed = parseRecord(messages[0]);
    } catch (error) {
      if (error && error.reason === reason) throw error;
      throw stageError('controller', reason);
    }
  }
  if (!parsed) throw stageError('controller', reason);
  if (!Array.isArray(parsed.actions)) parsed = parseRecord(parsed.message);
  if (!parsed || !Array.isArray(parsed.actions)) throw stageError('controller', reason);
  return parsed.actions;
}

function decodeRequestMessage(body) {
  return decodeAuraActions(body, 'aura-request-invalid');
}

function decodeResponseMessage(body) {
  return decodeAuraActions(body, 'controller-response-invalid');
}

function paramsAreValid(method, params) {
  if (!isRecord(params)) return false;
  const expected = {
    getMyMembership: [],
    saveMyMembership: ['email', 'fullName', 'goal', 'plan'],
    setMyStatus: ['status'],
    adminSave: ['email', 'fullName', 'goal', 'memberId', 'plan', 'status'],
    listMembers: [],
    member360: ['memberId'],
    checkIn: ['memberId'],
  }[method];
  if (!expected) return false;
  if (method === 'adminSave') {
    const withoutOptionalMemberId = expected.filter(key => key !== 'memberId');
    if (!exactKeys(params, expected) && !exactKeys(params, withoutOptionalMemberId)) return false;
  } else if (!exactKeys(params, expected)) return false;
  if (method === 'saveMyMembership') {
    return typeof params.fullName === 'string' && params.fullName.length > 0
      && typeof params.email === 'string' && params.email.endsWith('@example.invalid')
      && typeof params.goal === 'string' && params.goal.length > 0 && PLANS.has(params.plan);
  }
  if (method === 'setMyStatus') return STATUSES.has(params.status);
  if (method === 'adminSave') {
    return (!Object.prototype.hasOwnProperty.call(params, 'memberId')
        || params.memberId === null || params.memberId === '' || SF_ID.test(params.memberId))
      && typeof params.fullName === 'string' && params.fullName.length > 0
      && typeof params.email === 'string' && params.email.endsWith('@example.invalid')
      && typeof params.goal === 'string' && params.goal.length > 0
      && PLANS.has(params.plan) && STATUSES.has(params.status);
  }
  if (method === 'member360') return params.memberId === null || SF_ID.test(params.memberId);
  if (method === 'checkIn') return SF_ID.test(params.memberId);
  return true;
}

function parseAuraRequest(body, controllerClass) {
  if (typeof controllerClass !== 'string' || !/^[A-Za-z][A-Za-z0-9_]*$/.test(controllerClass)) {
    throw stageError('controller', 'controller-method-invalid');
  }
  const actions = decodeRequestMessage(body);
  const found = [];
  const requestIds = new Set();
  for (const action of actions) {
    if (!isRecord(action)) continue;
    const id = action.id;
    if (typeof id === 'string') {
      if (requestIds.has(id)) throw stageError('controller', 'controller-id-invalid');
      requestIds.add(id);
    }
    if (typeof action.descriptor !== 'string') continue;
    const direct = /^apex:\/\/([^/]+)\/ACTION\$([A-Za-z][A-Za-z0-9_]*)$/.exec(action.descriptor);
    const wrapped = /^(?:aura|apex):\/\/ApexActionController\/ACTION\$execute$/i.test(action.descriptor);
    let actionController;
    let method;
    let actionParams;
    if (direct) {
      actionController = direct[1];
      method = direct[2];
      actionParams = action.params;
    } else if (wrapped && isRecord(action.params)) {
      actionController = action.params.classname;
      method = action.params.method;
      actionParams = action.params.params;
    } else continue;
    if (actionController !== controllerClass) continue;
    if (!METHODS.has(method)) throw stageError('controller', 'controller-method-invalid');
    if (typeof id !== 'string' || !ACTION_ID.test(id)) throw stageError('controller', 'controller-id-invalid');
    const noArgRead = method === 'getMyMembership' || method === 'listMembers';
    const requestParams = noArgRead
        && (actionParams === undefined || actionParams === null) ? {} : actionParams;
    if (!paramsAreValid(method, requestParams)) throw stageError('controller', 'controller-params-invalid');
    const normalizedParams = method === 'adminSave'
      && !Object.prototype.hasOwnProperty.call(requestParams, 'memberId')
      ? { ...requestParams, memberId: null } : requestParams;
    found.push({ id, method, params: normalizedParams });
  }
  return found;
}

function parseAuraResponse(body, requested) {
  const responses = decodeResponseMessage(body);
  return requested.map(request => {
    const matches = responses.filter(response => isRecord(response) && response.id === request.id);
    if (matches.length !== 1) {
      throw stageError('controller', 'controller-response-id-mismatch');
    }
    const response = matches[0];
    if (!['SUCCESS', 'ERROR'].includes(response.state)) {
      throw stageError('controller', 'controller-response-unsuccessful');
    }
    return {
      id: response.id,
      state: response.state,
      value: response.state === 'SUCCESS' ? response.returnValue : undefined,
    };
  });
}

function normalizeReturnValue(value) {
  let result = value;
  for (let depth = 0; depth < 2 && typeof result === 'string'; depth += 1) {
    try { result = JSON.parse(result); } catch (_) { break; }
  }
  // ApexActionController wraps the Apex String; validate the DTO inside that envelope.
  if (isRecord(result) && Object.hasOwn(result, 'returnValue')
      && Object.keys(result).every(key => key === 'returnValue' || key === 'cacheable')) {
    result = result.returnValue;
    for (let depth = 0; depth < 2 && typeof result === 'string'; depth += 1) {
      try { result = JSON.parse(result); } catch (_) { break; }
    }
  }
  return result;
}

function normalizeDto(value) {
  const result = normalizeReturnValue(value);
  if (result === null) return null;
  if (!isRecord(result)) throw stageError('controller', 'controller-response-invalid');
  if (!SF_ID.test(result.id)
      || typeof result.fullName !== 'string' || !result.fullName
      || typeof result.email !== 'string' || !result.email
      || typeof result.goal !== 'string' || !result.goal
      || !STATUSES.has(result.status) || !PLANS.has(result.plan)) {
    throw stageError('controller', 'controller-response-invalid');
  }
  const visitCount = result.visitCount;
  if (!Number.isInteger(visitCount) || visitCount < 0) {
    throw stageError('controller', 'controller-response-invalid');
  }
  return {
    id: result.id,
    fullName: result.fullName,
    email: result.email,
    goal: result.goal,
    status: result.status,
    plan: result.plan,
    loginUserId: result.loginUserId,
    visitCount,
    visitId: result.visitId,
    coaching: result.coaching,
  };
}

function normalizeList(value) {
  const result = normalizeReturnValue(value);
  if (!Array.isArray(result)) throw stageError('controller', 'controller-response-invalid');
  return result.map(normalizeDto);
}

function normalizeHost(value) {
  if (typeof value !== 'string') return null;
  try {
    const parsed = new URL('https://' + value);
    if (parsed.username || parsed.password || parsed.port
        || parsed.pathname !== '/' || parsed.search || parsed.hash) return null;
    if (!parsed.hostname.endsWith('.lightning.force.com')) return null;
    return parsed.hostname.toLowerCase();
  } catch (_) {
    return null;
  }
}

function auraEndpointAllowed(urlText, expectedHost) {
  const host = normalizeHost(expectedHost);
  if (!host) return false;
  try {
    const url = new URL(urlText);
    return url.protocol === 'https:' && !url.port && url.hostname.toLowerCase() === host
      && url.pathname === '/aura';
  } catch (_) {
    return false;
  }
}

class GymAuraObserver {
  constructor(page, controllerClass, expectedHost) {
    this.page = page;
    this.controllerClass = controllerClass;
    this.expectedHost = normalizeHost(expectedHost);
    this.requestActions = new WeakMap();
    this.requestNumber = 0;
    this.calls = [];
    this.sequence = 0;
    this.failure = null;
  }

  attach() {
    if (!this.expectedHost) throw stageError('controller', 'controller-host-invalid');
    this.page.on('request', request => this._request(request));
    this.page.on('response', response => { this._response(response).catch(() => {
      this.failure = this.failure || stageError('controller', 'controller-response-invalid');
    }); });
  }

  _isAura(urlText) {
    try {
      const url = new URL(urlText);
      return url.pathname === '/aura';
    } catch (_) {
      return false;
    }
  }

  _request(request) {
    if (!this._isAura(request.url()) || request.method() !== 'POST') return;
    let actions;
    try {
      actions = parseAuraRequest(request.postData() || '', this.controllerClass);
    } catch (error) {
      if (error && error.reason === 'aura-request-invalid') return;
      this.failure = this.failure || error;
      return;
    }
    if (!actions.length) return;
    let url;
    try { url = new URL(request.url()); } catch (_) {
      this.failure = this.failure || stageError('controller', 'controller-host-invalid');
      return;
    }
    if (!auraEndpointAllowed(request.url(), this.expectedHost)) {
      this.failure = this.failure || stageError('controller', 'controller-host-invalid');
      return;
    }
    if (this.requestActions.has(request)) return;
    const requestNumber = ++this.requestNumber;
    this.requestActions.set(request, actions.map(action => ({
      ...action,
      request_number: requestNumber,
      params_verified: false,
      sequence: ++this.sequence,
      host: url.hostname.toLowerCase(),
      completed: false,
    })));
  }

  async _response(response) {
    if (!this._isAura(response.url())) return;
    let request;
    try { request = response.request(); } catch (_) { return; }
    const requestActions = this.requestActions.get(request);
    if (!requestActions) return;
    if (!auraEndpointAllowed(response.url(), this.expectedHost)) {
      throw stageError('controller', 'controller-host-invalid');
    }
    const outstanding = requestActions.filter(action => !action.completed);
    if (!outstanding.length) return;
    const body = await response.text();
    let actions;
    try { actions = decodeResponseMessage(body); } catch (_) {
      return;
    }
    const matched = actions.filter(item => isRecord(item)
      && outstanding.some(requestAction => requestAction.id === item.id));
    if (!matched.length) return;
    const requested = outstanding.filter(requestAction =>
      matched.some(responseAction => responseAction.id === requestAction.id));
    const normalizedActions = parseAuraResponse(JSON.stringify({ actions: matched }), requested);
    for (const [index, requestAction] of requested.entries()) {
      const normalized = normalizedActions[index];
      const value = normalized.state === 'SUCCESS'
        ? normalizeReturnValue(normalized.value)
        : undefined;
      this.calls.push({
        sequence: requestAction.sequence,
        request_number: requestAction.request_number,
        method: requestAction.method,
        request_id: requestAction.id,
        response_id: normalized.id,
        response_state: normalized.state,
        params: requestAction.params,
        params_verified: false,
        proof_required: false,
        value,
      });
      requestAction.completed = true;
    }
  }

  cursor() {
    return this.sequence;
  }

  async waitForCall(cursor, method, predicate, expectedState, timeoutMs = 30000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() <= deadline) {
      if (this.failure) throw this.failure;
      for (const call of [...this.calls].sort((left, right) => left.sequence - right.sequence)) {
        if (call.sequence <= cursor) continue;
        if (call.method !== method) continue;
        if (!predicate(call.params, call.value)) continue;
        if (call.response_state !== expectedState) {
          throw stageError('controller', 'controller-response-invalid');
        }
        call.params_verified = true;
        call.proof_required = true;
        return call;
      }
      await this.page.waitForTimeout(100);
    }
    throw stageError('controller', 'controller-response-missing');
  }

  async waitForMethod(method, predicate = () => true, expectedState = 'SUCCESS') {
    return this.waitForCall(0, method, predicate, expectedState);
  }

  assertSettled() {
    if (this.failure) throw this.failure;
    if (!this.calls.some(call => call.proof_required === true)) {
      throw stageError('controller', 'controller-response-missing');
    }
  }

  projection() {
    const result = [];
    for (const call of this.calls) {
      if (call.proof_required !== true) continue;
      const safe = {
        request_number: call.request_number,
        method: call.method,
        request_id: call.request_id,
        response_id: call.response_id,
        response_state: call.response_state,
        params_verified: call.params_verified === true,
      };
      if (call.params && typeof call.params.memberId === 'string' && SF_ID.test(call.params.memberId)) {
        safe.member_id = call.params.memberId;
      }
      if (call.params && STATUSES.has(call.params.status)) safe.status_value = call.params.status;
      if (call.params && PLANS.has(call.params.plan)) safe.plan_value = call.params.plan;
      if (call.method === 'adminSave') {
        safe.member_id = typeof call.params.memberId === 'string' && SF_ID.test(call.params.memberId)
          ? call.params.memberId : null;
        safe.status_value = call.params.status;
        safe.plan_value = call.params.plan;
      }
      if (call.response_state === 'SUCCESS'
          && call.method !== 'listMembers' && call.method !== 'getMyMembership') {
        const dto = normalizeDto(call.value);
        safe.result_member_id = dto.id;
        safe.result_status = dto.status;
        safe.result_plan = dto.plan;
        safe.result_visit_count = dto.visitCount;
        if (typeof dto.visitId === 'string' && SF_ID.test(dto.visitId)) safe.visit_id = dto.visitId;
      }
      result.push(safe);
    }
    return result;
  }
}

function choiceControlMode(tagName) {
  return String(tagName).toUpperCase() === 'SELECT' ? 'native-select' : 'lightning-combobox';
}

function playwrightModule() {
  return pinnedBrowserRuntime.playwrightModule();
}

function browserExecutable() {
  return pinnedBrowserRuntime.browserExecutable();
}

function safeController(controllerClass) {
  return typeof controllerClass === 'string' && /^[A-Za-z][A-Za-z0-9_]*$/.test(controllerClass);
}

async function waitVisible(locator, {
  timeoutMs = 15000, exactCount = true, stage = 'render', reason = 'ui-control-missing',
} = {}) {
  try {
    await locator.first().waitFor({ state: 'visible', timeout: timeoutMs });
    const count = await locator.count();
    if ((exactCount && count !== 1) || (!exactCount && count < 1)) {
      throw stageError(stage, reason);
    }
    return locator;
  } catch (error) {
    if (error && error.stage === stage && error.reason === reason) throw error;
    throw stageError(stage, reason);
  }
}

async function findControl(page, label, role) {
  const byRole = page.getByRole(role, { name: label, exact: true });
  try {
    return await waitVisible(byRole);
  } catch (error) {
    if (!error || error.reason !== 'ui-control-missing') throw error;
  }
  return waitVisible(page.getByLabel(label, { exact: true }));
}

async function fillField(page, label, value) {
  const locator = await findControl(page, label, 'textbox');
  await locator.fill(value);
}

async function chooseValue(page, label, value) {
  const locator = await findControl(page, label, 'combobox');
  const tagName = await locator.evaluate(element => element.tagName);
  if (choiceControlMode(tagName) === 'native-select') {
    await locator.selectOption({ label: value });
    return;
  }
  await locator.click();
  let option = page.getByRole('option', { name: value, exact: true });
  try {
    await waitVisible(option);
  } catch (error) {
    if (!error || error.reason !== 'ui-control-missing') throw error;
    option = await waitVisible(page.getByText(value, { exact: true }));
  }
  await option.click();
}

async function clickButton(page, label) {
  const button = page.getByRole('button', { name: label, exact: true });
  await (await waitVisible(button)).click();
}

async function requireText(page, text) {
  await waitVisible(page.getByText(text, { exact: true }), {
    exactCount: false, stage: 'render', reason: 'ui-state-invalid',
  });
}

async function requireRefusal(page) {
  await waitVisible(page.getByText(/^Check-in refused\b/), {
    exactCount: false, stage: 'status-refusal', reason: 'ui-state-invalid',
  });
}

async function takeShot(page, screenshots, name) {
  const file = screenshots && screenshots[name];
  if (typeof file !== 'string' || !file) throw stageError('browser', 'ui-check-failed');
  await page.screenshot({ path: file, fullPage: true });
}

function sameProfile(params, expected) {
  return params.fullName === expected.fullName
    && params.email === expected.email
    && params.goal === expected.goal
    && params.plan === expected.plan;
}

function responseDto(call) {
  return normalizeDto(call.value);
}

function responseList(call) {
  return normalizeList(call.value);
}

async function selectMember(page, name, verb = 'View member') {
  await clickButton(page, verb + ' ' + name);
}

async function verifyMember360(page, expected) {
  await requireText(page, 'Selected member: ' + expected.fullName);
  await requireText(page, 'Selected email: ' + expected.email);
  await requireText(page, 'Selected goal: ' + expected.goal);
  await requireText(page, 'Selected plan: ' + expected.plan);
  await requireText(page, 'Selected status: ' + expected.status);
  await requireText(page, 'Visit count: ' + String(expected.visitCount));
}

function shouldAssertCoachingText(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

async function fillAdmin(page, member, status) {
  await fillField(page, 'Admin full name', member.fullName);
  await fillField(page, 'Admin email', member.email);
  await fillField(page, 'Admin goal', member.goal);
  await chooseValue(page, 'Admin plan', member.plan);
  await chooseValue(page, 'Admin status', status);
}

async function createMember(page, observer, member, status) {
  await fillAdmin(page, member, status);
  const cursor = observer.cursor();
  await clickButton(page, 'Create member');
  const call = await observer.waitForCall(
    cursor, 'adminSave',
    params => params.memberId === null || params.memberId === '',
    'SUCCESS',
  );
  if (!sameProfile(call.params, member) || call.params.status !== status) {
    throw stageError('controller', 'controller-params-invalid');
  }
  const dto = responseDto(call);
  if (dto.fullName !== member.fullName || dto.email !== member.email || dto.goal !== member.goal
      || dto.status !== status || dto.plan !== member.plan || dto.visitCount !== 0) {
    throw stageError('controller', 'controller-response-invalid');
  }
  return dto.id;
}

async function saveAdminMember(page, observer, member, memberId, status) {
  await selectMember(page, member.fullName, 'Manage member');
  await fillAdmin(page, member, status);
  const cursor = observer.cursor();
  await clickButton(page, 'Save member');
  const call = await observer.waitForCall(
    cursor, 'adminSave',
    params => params.memberId === memberId,
    'SUCCESS',
  );
  if (!sameProfile(call.params, member) || call.params.status !== status) {
    throw stageError('controller', 'controller-params-invalid');
  }
  const dto = responseDto(call);
  if (dto.id !== memberId || dto.fullName !== member.fullName || dto.email !== member.email
      || dto.goal !== member.goal || dto.status !== status || dto.plan !== member.plan) {
    throw stageError('controller', 'controller-response-invalid');
  }
  return dto;
}

async function viewMember(page, member, memberId, expectedStatus, expectedCount) {
  await selectMember(page, member.fullName, 'View member');
  await verifyMember360(page, {
    ...member, status: expectedStatus, visitCount: expectedCount,
  });
  return {
    id: memberId,
    fullName: member.fullName,
    email: member.email,
    goal: member.goal,
    plan: member.plan,
    status: expectedStatus,
    visitCount: expectedCount,
  };
}

function controlValueMatches(actual, expected) {
  return typeof actual === 'string' && actual.trim() === expected;
}

async function visibleChoiceMatches(locator, expected) {
  const tagName = await locator.evaluate(element => element.tagName);
  if (choiceControlMode(tagName) === 'native-select') {
    return controlValueMatches(await locator.inputValue(), expected);
  }
  const rendered = (await locator.innerText()).trim();
  if (rendered) return controlValueMatches(rendered, expected);
  for (const attribute of ['aria-valuetext', 'title', 'value']) {
    const value = await locator.getAttribute(attribute);
    if (controlValueMatches(value, expected)) return true;
  }
  return false;
}

async function waitForSelfValue(page, locator, role, expected, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() <= deadline) {
    const matches = role === 'combobox'
      ? await visibleChoiceMatches(locator, expected)
      : controlValueMatches(await locator.inputValue(), expected);
    if (matches) return;
    await page.waitForTimeout(100);
  }
  throw stageError('render', 'ui-state-invalid');
}

async function verifySelfVisible(page, expected) {
  await requireText(page, 'My status: ' + expected.status);
  for (const [label, value] of [
    ['My full name', expected.fullName],
    ['My email', expected.email],
    ['My goal', expected.goal],
  ]) {
    const field = await findControl(page, label, 'textbox');
    await waitForSelfValue(page, field, 'textbox', value);
  }
  const plan = await findControl(page, 'My plan', 'combobox');
  await waitForSelfValue(page, plan, 'combobox', expected.plan);
}

async function readSelf(page, expected) {
  await page.reload({ waitUntil: 'domcontentloaded' });
  await verifySelfVisible(page, expected);
}

async function journey(request, page, observer) {
  const nonce = request.check_nonce;
  const selfFirst = request.synthetic.self_first;
  const selfFinal = request.synthetic.self_final;
  const coached = request.synthetic.coached;
  const basic = request.synthetic.basic;
  const initial = request.initial_self;

  if (initial !== null && (!isRecord(initial) || !SF_ID.test(initial.Id)
      || !STATUSES.has(initial.Status__c))) {
    throw stageError('self-membership', 'ui-state-invalid');
  }
  const initialStatus = initial ? initial.Status__c : null;

  await fillField(page, 'My full name', selfFirst.fullName);
  await fillField(page, 'My email', selfFirst.email);
  await fillField(page, 'My goal', selfFirst.goal);
  await chooseValue(page, 'My plan', selfFirst.plan);
  let cursor = observer.cursor();
  await clickButton(page, 'Save my membership');
  let call = await observer.waitForCall(
    cursor, 'saveMyMembership',
    params => sameProfile(params, selfFirst),
    'SUCCESS',
  );
  let selfDto = responseDto(call);
  if ((initial && selfDto.id !== initial.Id)
      || selfDto.fullName !== selfFirst.fullName || selfDto.email !== selfFirst.email
      || selfDto.goal !== selfFirst.goal || selfDto.plan !== selfFirst.plan
      || selfDto.status !== (initialStatus || 'Active')) {
    throw stageError('self-membership', 'controller-response-invalid');
  }
  const selfId = selfDto.id;
  const firstSaveStatus = initialStatus || 'Active';
  await requireText(page, 'My status: ' + firstSaveStatus);

  if (firstSaveStatus !== 'Active') {
    await saveAdminMember(page, observer, selfFirst, selfId, 'Active');
  }

  cursor = observer.cursor();
  await clickButton(page, 'Freeze my membership');
  call = await observer.waitForCall(
    cursor, 'setMyStatus', params => params.status === 'Frozen', 'SUCCESS',
  );
  selfDto = responseDto(call);
  if (selfDto.id !== selfId || selfDto.status !== 'Frozen') {
    throw stageError('self-membership', 'controller-response-invalid');
  }
  await requireText(page, 'My status: Frozen');

  await fillField(page, 'My full name', selfFinal.fullName);
  await fillField(page, 'My email', selfFinal.email);
  await fillField(page, 'My goal', selfFinal.goal);
  await chooseValue(page, 'My plan', selfFinal.plan);
  cursor = observer.cursor();
  await clickButton(page, 'Save my membership');
  call = await observer.waitForCall(
    cursor, 'saveMyMembership',
    params => sameProfile(params, selfFinal),
    'SUCCESS',
  );
  selfDto = responseDto(call);
  if (selfDto.id !== selfId || selfDto.fullName !== selfFinal.fullName
      || selfDto.email !== selfFinal.email || selfDto.goal !== selfFinal.goal
      || selfDto.status !== 'Frozen' || selfDto.plan !== selfFinal.plan) {
    throw stageError('self-membership', 'controller-response-invalid');
  }
  await requireText(page, 'My status: Frozen');
  await takeShot(page, request.screenshots, 'self-frozen');

  cursor = observer.cursor();
  await clickButton(page, 'Resume my membership');
  call = await observer.waitForCall(
    cursor, 'setMyStatus', params => params.status === 'Active', 'SUCCESS',
  );
  selfDto = responseDto(call);
  if (selfDto.id !== selfId || selfDto.status !== 'Active') {
    throw stageError('self-membership', 'controller-response-invalid');
  }
  await requireText(page, 'My status: Active');
  await takeShot(page, request.screenshots, 'self');

  await readSelf(page, {
    status: 'Active', fullName: selfFinal.fullName,
    email: selfFinal.email, goal: selfFinal.goal, plan: selfFinal.plan,
  });

  const coachedId = await createMember(page, observer, coached, 'Active');
  let coachedDto = await viewMember(page, coached, coachedId, 'Active', 0);
  cursor = observer.cursor();
  await clickButton(page, 'Check in selected member');
  const firstCheck = await observer.waitForCall(
    cursor, 'checkIn', params => params.memberId === coachedId, 'SUCCESS',
  );
  const firstDto = responseDto(firstCheck);
  if (firstDto.id !== coachedId || !SF_ID.test(firstDto.visitId)
      || firstDto.visitCount !== 1 || firstDto.status !== 'Active'
      || typeof firstDto.coaching !== 'string'
      || !firstDto.coaching.toLowerCase().includes(coached.goal.toLowerCase())) {
    throw stageError('coaching', 'controller-response-invalid');
  }
  if (!shouldAssertCoachingText(firstDto.coaching)) {
    throw stageError('coaching', 'controller-response-invalid');
  }
  await requireText(page, 'Coaching: ' + firstDto.coaching);
  cursor = observer.cursor();
  await clickButton(page, 'Check in selected member');
  const repeatCheck = await observer.waitForCall(
    cursor, 'checkIn', params => params.memberId === coachedId, 'SUCCESS',
  );
  const repeatDto = responseDto(repeatCheck);
  if (repeatDto.visitId !== firstDto.visitId || repeatDto.visitCount !== 1) {
    throw stageError('coaching', 'controller-response-invalid');
  }
  coachedDto = await viewMember(page, coached, coachedId, 'Active', 1);
  await takeShot(page, request.screenshots, 'coached');

  await saveAdminMember(page, observer, coached, coachedId, 'Frozen');
  cursor = observer.cursor();
  await clickButton(page, 'Check in selected member');
  const frozenFailure = await observer.waitForCall(
    cursor, 'checkIn', params => params.memberId === coachedId, 'ERROR',
  );
  if (frozenFailure.response_state !== 'ERROR') {
    throw stageError('status-refusal', 'controller-response-unsuccessful');
  }
  await requireRefusal(page);
  coachedDto = await viewMember(page, coached, coachedId, 'Frozen', 1);
  await takeShot(page, request.screenshots, 'coached-frozen');

  await saveAdminMember(page, observer, coached, coachedId, 'Cancelled');
  cursor = observer.cursor();
  await clickButton(page, 'Check in selected member');
  const cancelledFailure = await observer.waitForCall(
    cursor, 'checkIn', params => params.memberId === coachedId, 'ERROR',
  );
  if (cancelledFailure.response_state !== 'ERROR') {
    throw stageError('status-refusal', 'controller-response-unsuccessful');
  }
  await requireRefusal(page);
  coachedDto = await viewMember(page, coached, coachedId, 'Cancelled', 1);
  await takeShot(page, request.screenshots, 'coached-cancelled');

  const basicId = await createMember(page, observer, basic, 'Active');
  let basicDto = await viewMember(page, basic, basicId, 'Active', 0);
  cursor = observer.cursor();
  await clickButton(page, 'Check in selected member');
  const basicCheck = await observer.waitForCall(
    cursor, 'checkIn', params => params.memberId === basicId, 'SUCCESS',
  );
  basicDto = responseDto(basicCheck);
  if (basicDto.id !== basicId || !SF_ID.test(basicDto.visitId)
      || basicDto.visitCount !== 1 || basicDto.status !== 'Active'
      || typeof basicDto.coaching !== 'string'
      || !basicDto.coaching.toLowerCase().includes('independent training')) {
    throw stageError('basic-checkin', 'controller-response-invalid');
  }
  if (!shouldAssertCoachingText(basicDto.coaching)) {
    throw stageError('basic-checkin', 'controller-response-invalid');
  }
  await requireText(page, 'Coaching: ' + basicDto.coaching);
  await takeShot(page, request.screenshots, 'basic');

  await page.reload({ waitUntil: 'domcontentloaded' });
  coachedDto = await viewMember(page, coached, coachedId, 'Cancelled', 1);
  const basicReload = await viewMember(page, basic, basicId, 'Active', 1);
  await takeShot(page, request.screenshots, 'reload');

  observer.assertSettled();
  const calls = observer.projection();
  const counts = {
    checkInSuccess: calls.filter(item => item.method === 'checkIn' && item.response_state === 'SUCCESS').length,
    checkInError: calls.filter(item => item.method === 'checkIn' && item.response_state === 'ERROR').length,
  };
  if (counts.checkInSuccess < 3 || counts.checkInError < 2
      || ![...REQUIRED_MUTATION_METHODS].every(method =>
        calls.some(item => item.method === method && item.params_verified))) {
    throw stageError('controller', 'controller-proof-missing');
  }

  return {
    schema: 'shiploop-gym-ui-browser/1',
    route_host: new URL(page.url()).hostname.toLowerCase(),
    route_path: new URL(page.url()).pathname,
    browser_version: page.context().browser() ? page.context().browser().version() : '',
    journeys: {
      self: {
        member_id: selfId,
        initial_status: initial ? initial.Status__c : null,
        first_save_status: firstSaveStatus,
        frozen_status: 'Frozen',
        frozen_edit_status: 'Frozen',
        resume_status: 'Active',
        reloaded_status: 'Active',
        frozen_profile_edit_verified: true,
      },
      coached: {
        member_id: coachedId,
        plan_verified: coachedDto.plan === 'Coached',
        initial_visit_count: 0,
        first_visit_id: firstDto.visitId,
        repeat_visit_id: repeatDto.visitId,
        first_visit_count: firstDto.visitCount,
        repeat_visit_count: repeatDto.visitCount,
        coaching_contains_goal: firstDto.coaching.toLowerCase().includes(coached.goal.toLowerCase()),
        frozen_refused: true,
        cancelled_refused: true,
        visits_after_frozen_refusal: 1,
        visits_after_cancelled_refusal: 1,
        reloaded_status: coachedDto.status,
        reloaded_visit_count: coachedDto.visitCount,
      },
      basic: {
        member_id: basicId,
        plan_verified: basicReload.plan === 'Basic',
        visit_id: basicDto.visitId,
        visit_count: basicDto.visitCount,
        coaching_contains_independent_training:
          basicDto.coaching.toLowerCase().includes('independent training'),
        reloaded_status: basicReload.status,
        reloaded_visit_count: basicReload.visitCount,
      },
    },
    calls,
  };
}

async function main() {
  let browser;
  let stage = 'browser';
  try {
    let input = '';
    for await (const chunk of process.stdin) input += chunk;
    const request = JSON.parse(input);
    const expectedHost = request && normalizeHost(request.expected_lightning_host);
    if (!request || typeof request.login_url !== 'string'
        || !/^https:\/\//i.test(request.login_url)
        || !expectedHost || !safeController(request.controller_class)
        || !PREFIX_RE.test(request.prefix || '')
        || !request.synthetic || !request.screenshots) {
      throw stageError('authenticate', 'ui-check-failed');
    }
    const login = new URL(request.login_url);
    if (login.protocol !== 'https:') throw stageError('authenticate', 'ui-check-failed');
    const { chromium } = playwrightModule();
    const executablePath = browserExecutable();
    browser = await chromium.launch({
      headless: true,
      ...(executablePath ? { executablePath } : {}),
    });
    const context = await browser.newContext({ viewport: { width: 1365, height: 950 } });
    const page = await context.newPage();
    page.setDefaultTimeout(20000);
    const observer = new GymAuraObserver(page, request.controller_class, expectedHost);
    observer.attach();

    stage = 'authenticate';
    await page.goto(request.login_url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForURL(url => url.hostname.toLowerCase() === expectedHost
      && url.hostname.toLowerCase().endsWith('.lightning.force.com')
      && !url.pathname.includes('frontdoor'), { timeout: 60000 });
    stage = 'route';
    await page.goto('https://' + expectedHost + '/lightning/n/'
      + encodeURIComponent(request.prefix + '_Members'), {
      waitUntil: 'domcontentloaded', timeout: 60000,
    });
    const routed = new URL(page.url());
    if (routed.protocol !== 'https:' || routed.hostname.toLowerCase() !== expectedHost
        || routed.pathname !== '/lightning/n/' + request.prefix + '_Members') {
      throw stageError('route', 'route-invalid');
    }
    stage = 'self-membership';
    const observed = await journey(request, page, observer);
    stage = 'controller';
    if (new URL(page.url()).hostname.toLowerCase() !== expectedHost) {
      throw stageError('controller', 'controller-host-invalid');
    }
    await context.close();
    process.stdout.write(JSON.stringify(observed) + '\n');
  } catch (error) {
    const failure = {
      status: 'failed',
      stage: SAFE_STAGES.has(error && error.stage) ? error.stage : stage,
      reason: SAFE_REASONS.has(error && error.reason) ? error.reason : 'ui-check-failed',
    };
    process.stdout.write(JSON.stringify(failure) + '\n');
    process.exitCode = 1;
  } finally {
    if (browser) {
      try { await browser.close(); } catch (_) { /* omit browser close details */ }
    }
  }
}

module.exports = {
  METHODS, STATUSES, PLANS, SAFE_STAGES, SAFE_REASONS, SF_ID, ACTION_ID,
  parseAuraRequest, parseAuraResponse, paramsAreValid, normalizeReturnValue,
  normalizeDto, normalizeList, normalizeHost, auraEndpointAllowed, choiceControlMode, GymAuraObserver,
  waitVisible, requireRefusal, shouldAssertCoachingText, controlValueMatches, readSelf,
  playwrightModule, browserExecutable,
};

if (require.main === module) main();
