'use strict';

// Bounded Grok chat UI journey. The trusted frontdoor URL arrives on stdin and
// is never logged, returned, written, or included in an error.
const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline');
const { fileURLToPath } = require('node:url');
const pinnedBrowser = require('./battleship_ui_browser.cjs');

const CONTROLLER = 'SLGrokChatController';
const PREFIX = 'SLGrokChat';
const ROUTE = '/lightning/n/SLGrokChat_Chat';
const NAMED_CREDENTIAL = 'Grok_Chat_Model';
const MODEL = 'grok-4.7';
const METHODS = new Set([
  'getSetup', 'saveSetup', 'testConnection', 'newConversation',
  'getConversation', 'sendMessage', 'confirmAction', 'cancelAction', 'seedItems',
]);
const TOOL_NAMES = new Set([
  'get_context', 'describe_schema', 'find_items', 'read_item',
  'propose_create_item', 'propose_update_item',
]);
const SAFE_STAGES = new Set([
  'identity', 'source', 'deployment', 'authenticate', 'route', 'render',
  'setup-missing', 'setup-save', 'connection', 'seed', 'read-tool',
  'create-proposal', 'create-confirm', 'update-proposal', 'update-confirm',
  'cancel-proposal', 'cancel-confirm', 'stale-proposal', 'stale-confirm',
  'reload', 'viewport', 'keyboard', 'controller', 'database', 'observe', 'browser',
]);
const SAFE_REASONS = new Set([
  'invalid-options', 'duplicate-mode-option', 'mode-invalid', 'phase-invalid',
  'platform-unavailable', 'identity-mismatch', 'admin-required', 'source-invalid',
  'source-changed', 'source-stale', 'deployment-missing', 'deployment-failed',
  'browser-unavailable', 'browser-result-invalid', 'route-invalid', 'host-mismatch',
  'ui-control-missing', 'ui-state-invalid', 'keyboard-inaccessible', 'layout-overflow',
  'setup-not-missing', 'chat-attempted-before-setup', 'setup-save-missing',
  'setup-readback-mismatch', 'connection-failed', 'conversation-missing', 'seed-invalid',
  'read-tool-missing', 'fake-prose-without-tool', 'nonce-result-mismatch', 'unsafe-text',
  'proposal-missing', 'proposal-mismatch', 'preconfirm-write', 'write-missing',
  'extra-write', 'cancel-mismatch', 'stale-not-rejected', 'replay-mismatch',
  'reload-mismatch', 'controller-proof-missing', 'controller-action-invalid',
  'controller-response-id-mismatch', 'controller-response-invalid',
  'database-state-mismatch', 'screenshot-missing', 'browser-provider-call', 'evaluation-failed',
]);
const SF_ID_RE = /^[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?$/;
const ACTION_ID_RE = /^[A-Za-z0-9._;:-]{1,128}$/;
const FIELDS = new Set(['Name', 'Status__c', 'Notes__c']);
const SUCCESS_TOOL_STATES = new Set(['ok', 'success', 'completed', 'succeeded']);

function stageError(stage, reason) {
  const error = new Error('Grok chat UI check failed');
  error.stage = SAFE_STAGES.has(stage) ? stage : 'browser';
  error.reason = SAFE_REASONS.has(reason) ? reason : 'evaluation-failed';
  return error;
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function exactKeys(value, keys) {
  return isRecord(value) && JSON.stringify(Object.keys(value).sort())
    === JSON.stringify([...keys].sort());
}

function decodeAura(value, reason) {
  if (typeof value !== 'string' || !value) throw stageError('controller', reason);
  const source = value.replace(/^\uFEFF/, '').trim()
    .replace(/^\s*while\s*\(\s*1\s*\)\s*;\s*/, '')
    .replace(/^\)\]\}',?\s*/, '');
  let parsed;
  try { parsed = JSON.parse(source); } catch (_) { parsed = null; }
  if (!isRecord(parsed)) {
    try {
      const messages = new URLSearchParams(value).getAll('message');
      if (messages.length !== 1) throw stageError('controller', reason);
      parsed = JSON.parse(messages[0]);
    } catch (_) { throw stageError('controller', reason); }
  }
  if (!Array.isArray(parsed.actions)) {
    try { parsed = typeof parsed.message === 'string' ? JSON.parse(parsed.message) : parsed.message; }
    catch (_) { parsed = null; }
  }
  if (!isRecord(parsed) || !Array.isArray(parsed.actions)) throw stageError('controller', reason);
  return parsed.actions;
}

function requestMethod(action, controllerClass) {
  if (!isRecord(action) || typeof action.id !== 'string' || !ACTION_ID_RE.test(action.id)
      || typeof action.descriptor !== 'string') return null;
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
  } else return null;
  if (controller !== controllerClass || typeof method !== 'string' || !METHODS.has(method)) return null;
  if (params === undefined || params === null) params = {};
  if (!isRecord(params)) throw stageError('controller', 'controller-action-invalid');
  const expected = {
    getSetup: [], saveSetup: ['model', 'namedCredential'], testConnection: [], newConversation: [],
    getConversation: ['conversationId'], sendMessage: ['conversationId', 'message'],
    confirmAction: ['actionId'], cancelAction: ['actionId'], seedItems: [],
  }[method];
  if (!exactKeys(params, expected)) throw stageError('controller', 'controller-action-invalid');
  if (method === 'saveSetup'
      && (params.namedCredential !== 'Grok_Chat_Model' || params.model !== 'grok-4.7')) {
    throw stageError('controller', 'controller-action-invalid');
  }
  if ((method === 'getConversation' || method === 'sendMessage')
      && !SF_ID_RE.test(params.conversationId || '')) throw stageError('controller', 'controller-action-invalid');
  if (method === 'sendMessage' && (typeof params.message !== 'string' || !params.message.trim())) {
    throw stageError('controller', 'controller-action-invalid');
  }
  if ((method === 'confirmAction' || method === 'cancelAction')
      && !ACTION_ID_RE.test(params.actionId || '')) throw stageError('controller', 'controller-action-invalid');
  return { id: action.id, method, params };
}

function safeFieldMap(value) {
  if (!isRecord(value) || Object.keys(value).some(key => !FIELDS.has(key))) return null;
  const result = {};
  for (const [key, entry] of Object.entries(value)) {
    if (typeof entry !== 'string' && entry !== null) return null;
    if (key === 'Status__c' && entry !== null && !['Open', 'Done'].includes(entry)) return null;
    result[key] = entry;
  }
  return result;
}

function normalizeAction(value) {
  if (!isRecord(value) || typeof value.actionId !== 'string' || !ACTION_ID_RE.test(value.actionId)
      || !['proposed', 'applied', 'cancelled', 'stale', 'rejected', 'failed'].includes(value.status)
      || !['create', 'update'].includes(value.operation)) return null;
  const oldValues = value.oldValues === undefined || value.oldValues === null ? {} : safeFieldMap(value.oldValues);
  const newValues = safeFieldMap(value.newValues);
  if (!oldValues || !newValues) return null;
  const recordId = value.recordId === null ? null : value.recordId;
  if (recordId !== null && (typeof recordId !== 'string' || !SF_ID_RE.test(recordId))) return null;
  return { actionId: value.actionId, status: value.status, operation: value.operation,
    recordId, oldValues, newValues };
}

function parseOnceJsonString(value) {
  if (typeof value !== 'string' || !value) return null;
  try {
    const parsed = JSON.parse(value);
    return isRecord(parsed) ? parsed : null;
  } catch (_) { return null; }
}

function normalizeToolCall(value) {
  if (!isRecord(value) || !TOOL_NAMES.has(value.name)) return null;
  let args = value.arguments;
  if (typeof args === 'string') {
    try { args = JSON.parse(args); } catch (_) { return null; }
  }
  if (!isRecord(args)) return null;
  let result = value.result;
  if (typeof result === 'string') {
    try { result = JSON.parse(result); } catch (_) { /* plain text is not structured proof */ }
  }
  const status = typeof value.status === 'string' ? value.status.toLowerCase() : '';
  return { name: value.name, arguments: args, result, status };
}

function normalizeConversation(value) {
  if (!isRecord(value) || !SF_ID_RE.test(value.conversationId || '')
      || !Array.isArray(value.messages) || !Array.isArray(value.actions) || !Array.isArray(value.toolCalls)) return null;
  const messages = [];
  for (const message of value.messages) {
    if (!isRecord(message) || !['system', 'user', 'assistant', 'tool'].includes(message.role)
        || typeof message.content !== 'string') return null;
    messages.push({ role: message.role, content: message.content });
  }
  const actions = value.actions.map(normalizeAction);
  const toolCalls = value.toolCalls.map(normalizeToolCall);
  if (actions.some(item => item === null) || toolCalls.some(item => item === null)) return null;
  return { conversationId: value.conversationId, messages, actions, toolCalls,
    status: ['ready', 'working', 'error'].includes(value.status) ? value.status : null,
    code: typeof value.code === 'string' ? value.code : null };
}

function normalizeResult(method, rawValue) {
  const value = parseOnceJsonString(rawValue);
  if (!value) throw stageError('controller', 'controller-response-invalid');
  if (method === 'getSetup' || method === 'saveSetup') {
    if (!['missing', 'ready', 'error'].includes(value.status) || typeof value.canConfigure !== 'boolean'
        || !Object.hasOwn(value, 'namedCredential') || !Object.hasOwn(value, 'model')) {
      throw stageError('controller', 'controller-response-invalid');
    }
    return { status: value.status, canConfigure: value.canConfigure,
      namedCredential: value.namedCredential, model: value.model,
      code: typeof value.code === 'string' ? value.code : null };
  }
  if (method === 'testConnection') {
    if (!['ok', 'error'].includes(value.status)) throw stageError('controller', 'controller-response-invalid');
    return { status: value.status, code: typeof value.code === 'string' ? value.code : null,
      model: typeof value.model === 'string' ? value.model : null };
  }
  if (method === 'newConversation') {
    if (!SF_ID_RE.test(value.conversationId || '')) throw stageError('controller', 'controller-response-invalid');
    return { conversationId: value.conversationId };
  }
  if (method === 'getConversation' || method === 'sendMessage') {
    const conversation = normalizeConversation(value);
    if (!conversation) throw stageError('controller', 'controller-response-invalid');
    return conversation;
  }
  if (method === 'confirmAction') {
    if (!ACTION_ID_RE.test(value.actionId || '') || !['applied', 'stale', 'rejected', 'failed'].includes(value.status)
        || !['create', 'update'].includes(value.operation)
        || (value.recordId !== null && !SF_ID_RE.test(value.recordId || ''))) {
      throw stageError('controller', 'controller-response-invalid');
    }
    return { actionId: value.actionId, status: value.status,
      operation: value.operation, recordId: value.recordId };
  }
  if (method === 'cancelAction') {
    if (!ACTION_ID_RE.test(value.actionId || '') || !['cancelled', 'rejected'].includes(value.status)) {
      throw stageError('controller', 'controller-response-invalid');
    }
    return { actionId: value.actionId, status: value.status };
  }
  if (method === 'seedItems') {
    if (!Array.isArray(value.recordIds) || value.recordIds.some(id => !SF_ID_RE.test(id))) {
      throw stageError('controller', 'controller-response-invalid');
    }
    return { recordIds: value.recordIds };
  }
  throw stageError('controller', 'controller-response-invalid');
}

function parseAuraRequest(value, controllerClass) {
  const actions = decodeAura(value, 'controller-action-invalid');
  const found = [];
  const seen = new Set();
  for (const action of actions) {
    if (!isRecord(action)) continue;
    let descriptor = action.descriptor;
    let target = null;
    if (typeof descriptor === 'string') {
      const direct = /^apex:\/\/([^/]+)\/ACTION\$/.exec(descriptor);
      const wrapped = /^(?:aura|apex):\/\/ApexActionController\/ACTION\$execute$/i.test(descriptor);
      target = direct ? direct[1] : (wrapped && isRecord(action.params) ? action.params.classname : null);
    }
    if (target !== controllerClass) continue;
    const normalized = requestMethod(action, controllerClass);
    if (!normalized || seen.has(normalized.id)) throw stageError('controller', 'controller-action-invalid');
    seen.add(normalized.id);
    found.push(normalized);
  }
  return found;
}

function pairAuraActions(requests, responseBody) {
  const responses = decodeAura(responseBody, 'controller-response-invalid');
  return requests.map(request => {
    const matches = responses.filter(action => isRecord(action) && action.id === request.id);
    if (matches.length !== 1) throw stageError('controller', 'controller-response-id-mismatch');
    const response = matches[0];
    if (response.state !== 'SUCCESS' || typeof response.returnValue !== 'string') {
      throw stageError('controller', 'controller-response-invalid');
    }
    const result = normalizeResult(request.method, response.returnValue);
    if ((result.conversationId && request.params.conversationId
          && result.conversationId !== request.params.conversationId)
        || (result.actionId && request.params.actionId
          && result.actionId !== request.params.actionId)) {
      throw stageError('controller', 'controller-response-invalid');
    }
    return { request_id: request.id, response_id: response.id,
      response_state: response.state, result, json_string_decoded_once: true };
  });
}

class ApexObserver {
  constructor(page, expectedHost) {
    this.page = page;
    this.expectedHost = expectedHost;
    this.records = [];
    this.requestActions = new WeakMap();
    this.pending = new Set();
    this.failure = null;
    this.sequence = 0;
  }

  attach() {
    this.page.on('request', request => this.onRequest(request));
    this.page.on('response', response => {
      const job = this.onResponse(response).catch(error => {
        this.failure = this.failure || (error && error.stage
          ? error : stageError('controller', 'controller-response-invalid'));
      });
      this.pending.add(job);
      job.finally(() => this.pending.delete(job));
    });
  }

  onRequest(request) {
    let url;
    try { url = new URL(request.url()); } catch (_) { return; }
    if (url.pathname !== '/aura' || request.method().toUpperCase() !== 'POST') return;
    let actions;
    try { actions = parseAuraRequest(request.postData() || '', CONTROLLER); }
    catch (error) { this.failure = this.failure || error; return; }
    if (!actions.length) return;
    if (url.protocol !== 'https:' || url.hostname.toLowerCase() !== this.expectedHost || url.port) {
      this.failure = this.failure || stageError('controller', 'host-mismatch');
      return;
    }
    const records = actions.map(action => {
      const record = {
        sequence: ++this.sequence, method: action.method, request_id: action.id,
        params: action.params, params_valid: true, response_id: null,
        response_state: 'PENDING', result: null, json_string_decoded_once: false,
      };
      this.records.push(record);
      return record;
    });
    this.requestActions.set(request, records);
  }

  async onResponse(response) {
    let url;
    try { url = new URL(response.url()); } catch (_) { return; }
    if (url.pathname !== '/aura') return;
    let request;
    try { request = response.request(); } catch (_) { return; }
    const records = this.requestActions.get(request);
    if (!records) return;
    if (url.protocol !== 'https:' || url.hostname.toLowerCase() !== this.expectedHost || url.port) {
      throw stageError('controller', 'host-mismatch');
    }
    if (response.status() < 200 || response.status() >= 300) {
      this.failure = this.failure || stageError('controller', 'controller-response-invalid');
      return;
    }
    const pairs = pairAuraActions(records.map(record => ({ id: record.request_id,
      method: record.method, params: record.params })), await response.text());
    for (let index = 0; index < records.length; index += 1) {
      const record = records[index];
      const pair = pairs[index];
      record.response_id = pair.response_id;
      record.response_state = pair.response_state;
      record.http_ok = true;
      record.json_string_decoded_once = pair.json_string_decoded_once;
      record.result = pair.result;
    }
  }

  mark() { return this.records.length; }

  async waitFor(method, predicate = () => true, timeoutMs = 90000, startAt = 0) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() <= deadline) {
      if (this.failure) throw this.failure;
      const match = this.records.slice(startAt).find(record => record.method === method
        && record.response_state !== 'PENDING' && predicate(record));
      if (match) return match;
      await this.page.waitForTimeout(100);
    }
    throw stageError('controller', 'controller-proof-missing');
  }

  async settle() {
    await Promise.all([...this.pending]);
    if (this.failure) throw this.failure;
  }

  projection() {
    return this.records.map(record => {
      const result = record.result || {};
      const output = {
        method: record.method, request_id: record.request_id, response_id: record.response_id,
        response_state: record.response_state, params_valid: record.params_valid,
        json_string_decoded_once: record.json_string_decoded_once, http_ok: record.http_ok === true,
        ui_correlated: record.ui_correlated === true,
      };
      if (result.status) output.result_status = result.status;
      if (result.operation) output.result_operation = result.operation;
      if (result.recordId) output.result_record_id = result.recordId;
      if (result.conversationId) output.result_conversation_id = result.conversationId;
      if (result.actionId) output.action_id = result.actionId;
      return output;
    });
  }
}

function statusOf(result) {
  return result && isRecord(result) ? result.status : null;
}

function latestCall(observer, method, startAt = 0) {
  return observer.records.slice(startAt).find(record => record.method === method && record.response_state === 'SUCCESS');
}

async function region(page, name) {
  const locator = page.getByRole('region', { name, exact: true });
  await locator.first().waitFor({ state: 'visible', timeout: 45000 });
  return locator.first();
}

async function input(page, label) {
  const locator = page.getByLabel(label, { exact: true });
  await locator.first().waitFor({ state: 'visible', timeout: 30000 });
  return locator.first();
}

async function button(page, label) {
  const locator = page.getByRole('button', { name: label, exact: true });
  await locator.first().waitFor({ state: 'visible', timeout: 30000 });
  return locator.first();
}

async function click(page, label) {
  const control = await button(page, label);
  if (!await control.isEnabled()) throw stageError('render', 'ui-control-missing');
  await control.click({ timeout: 30000 });
}

async function writeMessage(page, observer, conversationId, message) {
  const cursor = observer.mark();
  const field = await input(page, 'Message');
  await field.fill(message);
  await click(page, 'Send');
  const call = await observer.waitFor('sendMessage', record =>
    record.params.conversationId === conversationId && record.params.message === message,
  150000, cursor);
  if (call.result.status !== 'ready') throw stageError('read-tool', 'ui-state-invalid');
  const conversation = call.result;
  const chatStatus = await (await region(page, 'Chat status')).innerText().catch(() => '');
  if (!/ready/i.test(chatStatus)) throw stageError('render', 'ui-state-invalid');
  return { call, conversation };
}

function findAction(conversation, operation, predicate) {
  return conversation.actions.find(action => action.operation === operation
    && action.status === 'proposed' && predicate(action)) || null;
}

async function proposalRegion(page, matchText) {
  const regions = page.getByRole('region', { name: 'Proposed change', exact: true });
  const count = await regions.count();
  for (let index = 0; index < count; index += 1) {
    const candidate = regions.nth(index);
    if (await candidate.isVisible() && (await candidate.innerText()).includes(matchText)) return candidate;
  }
  throw stageError('render', 'proposal-missing');
}

async function actionStatus(page, status) {
  const target = await region(page, 'Action status');
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    const text = (await target.innerText()).toLowerCase();
    if (text.includes(status)) return text;
    await page.waitForTimeout(150);
  }
  throw stageError('render', status === 'stale' ? 'stale-not-rejected' : 'ui-state-invalid');
}

function findItemResult(result, expectedId, expectedName, expectedNotes) {
  const calls = result.toolCalls || [];
  const find = calls.find(call => call.name === 'find_items' && SUCCESS_TOOL_STATES.has(call.status)
    && call.arguments.query === expectedName);
  const read = calls.find(call => call.name === 'read_item' && SUCCESS_TOOL_STATES.has(call.status)
    && call.arguments.recordId === expectedId);
  const findResult = find && find.result;
  const foundRecords = Array.isArray(findResult) ? findResult
    : (isRecord(findResult) && Array.isArray(findResult.items) ? findResult.items
      : (isRecord(findResult) && Array.isArray(findResult.records) ? findResult.records : []));
  const found = foundRecords.some(item => isRecord(item) && item.Id === expectedId && item.Name === expectedName);
  const record = read && (read.result && (read.result.record || read.result.item || read.result));
  const matches = isRecord(record) && record.Id === expectedId && record.Name === expectedName
    && record.Notes__c === expectedNotes;
  return { find: !!find && found, read: !!read, result: matches };
}

function hasToolCall(conversation, name, argsMatch) {
  return conversation.toolCalls.some(call => call.name === name
    && SUCCESS_TOOL_STATES.has(call.status) && argsMatch(call.arguments));
}

function noUnsafeMarkup(text, locator) {
  return Promise.all([
    locator.locator('img,iframe,object,embed,video,audio').count(),
    locator.evaluate(element => ({
      text: element.innerText || '',
      eventAttrs: (() => {
        function hasHandler(root) {
          for (const node of root.querySelectorAll('*')) {
            if ([...node.attributes].some(attr => /^on/i.test(attr.name))) return true;
            if (node.shadowRoot && hasHandler(node.shadowRoot)) return true;
          }
          return false;
        }
        return hasHandler(element);
      })(),
    })),
  ]).then(([activeCount, values]) => activeCount === 0 && !values.eventAttrs
    && typeof text === 'string' && values.text.includes(text));
}

async function screenshot(page, request, name) {
  const target = request.screenshots && request.screenshots[name];
  if (typeof target !== 'string' || !path.isAbsolute(target)) throw stageError('browser', 'screenshot-missing');
  await page.screenshot({ path: target, fullPage: true, animations: 'disabled' });
  await fs.promises.chmod(target, 0o600);
}

async function checkLayout(page, width, height) {
  await page.setViewportSize({ width, height });
  await page.waitForTimeout(150);
  const conversation = await region(page, 'Conversation');
  const setup = await region(page, 'Setup status');
  const measure = async locator => locator.evaluate(element => {
    const rect = element.getBoundingClientRect();
    return { left: rect.left, right: rect.right, width: rect.width,
      clientWidth: element.clientWidth, scrollWidth: element.scrollWidth };
  });
  const [chatBox, setupBox] = await Promise.all([measure(conversation), measure(setup)]);
  return [chatBox, setupBox].every(box => box.left >= -1 && box.right <= width + 1
    && box.width <= width + 1 && box.scrollWidth <= box.clientWidth + 2);
}

async function deepFocusedLabel(page) {
  return page.evaluate(() => {
    function active(root) {
      const item = root.activeElement;
      if (!item) return null;
      if (item.shadowRoot && item.shadowRoot.activeElement) return active(item.shadowRoot);
      const labels = item.labels ? [...item.labels].map(label => label.innerText).join(' ') : '';
      return { aria: item.getAttribute('aria-label') || '', label: labels.trim(), tag: item.tagName };
    }
    return active(document);
  });
}

async function keyboardCheck(page) {
  const setup = await button(page, 'Setup');
  await setup.focus();
  await page.keyboard.press('Enter');
  await input(page, 'Named credential');
  let found = false;
  for (let index = 0; index < 10; index += 1) {
    await page.keyboard.press('Tab');
    const focused = await deepFocusedLabel(page);
    if (focused && /Named credential|Model|Message/.test(`${focused.aria} ${focused.label}`)) {
      found = true;
      break;
    }
  }
  if (!found) throw stageError('keyboard', 'keyboard-inaccessible');
  return true;
}

function expectedHost(request) {
  const expectedHost = request.expected_lightning_host.toLowerCase();
  if (!/^[a-z0-9.-]+\.lightning\.force\.com$/.test(expectedHost)) {
    throw stageError('identity', 'identity-mismatch');
  }
  return expectedHost;
}

async function signInVisible(page) {
  const candidates = [
    page.getByRole('heading', { name: /log ?in to salesforce|sign in to salesforce/i }),
    page.locator('input[type="password"]'),
    page.locator('input[name="un"],input[autocomplete="username"]'),
  ];
  for (const candidate of candidates) {
    try { if (await candidate.first().isVisible()) return true; } catch (_) { /* not a sign-in view */ }
  }
  return false;
}

function knownSignInLocation(url, host) {
  if (url.protocol !== 'https:') return false;
  const expectedMyDomain = host.replace(/\.lightning\.force\.com$/i, '.my.salesforce.com');
  const currentHost = url.hostname.toLowerCase();
  const loginServices = ['login.salesforce.com', 'test.salesforce.com'].includes(currentHost);
  const loginPath = /\/login|\/secur\/frontdoor\.jsp/i.test(url.pathname);
  return ((currentHost === expectedMyDomain || loginServices) && (url.pathname === '/' || loginPath))
    || (currentHost === host && loginPath);
}

function validateFrontdoor(request) {
  if (typeof request.login_url !== 'string') throw stageError('authenticate', 'identity-mismatch');
  const login = new URL(request.login_url);
  const expected = expectedHost(request);
  if (login.protocol !== 'https:' || login.username || login.password
      || !login.hostname.toLowerCase().endsWith('.my.salesforce.com')
      || !/^\/secur\/frontdoor\.jsp$/.test(login.pathname)) {
    throw stageError('authenticate', 'identity-mismatch');
  }
  const expectedFromAuth = login.hostname.toLowerCase().replace(/\.my\.salesforce\.com$/, '.lightning.force.com');
  if (expectedFromAuth !== expected) throw stageError('authenticate', 'identity-mismatch');
}

async function createSession(request, observer) {
  const host = expectedHost(request);
  const { chromium } = pinnedBrowser.playwrightModule();
  const executablePath = pinnedBrowser.browserExecutable();
  const browser = await chromium.launch({
    headless: true,
    ...(executablePath ? { executablePath } : {}),
    args: ['--password-store=basic', '--use-mock-keychain', '--disable-features=DialMediaRouteProvider'],
  });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  let providerCalls = 0;
  page.on('request', req => {
    try {
      const url = new URL(req.url());
      if (url.hostname === 'api.x.ai' || url.hostname.endsWith('.x.ai')) providerCalls += 1;
    } catch (_) { /* malformed request URLs are not evidence */ }
  });
  observer.page = page;
  observer.attach();
  try {
    await page.goto(`https://${host}${ROUTE}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    const current = new URL(page.url());
    const routeMatches = current.protocol === 'https:' && current.hostname.toLowerCase() === host
      && current.pathname === ROUTE;
    let setupVisible = false;
    let loginVisible = false;
    if (routeMatches) {
      const setupRegion = page.getByRole('region', { name: 'Setup status', exact: true });
      const deadline = Date.now() + 15000;
      while (Date.now() < deadline && !setupVisible && !loginVisible) {
        try { setupVisible = await setupRegion.first().isVisible(); } catch (_) { /* wait for render */ }
        if (!setupVisible) loginVisible = await signInVisible(page);
        if (!setupVisible && !loginVisible) await page.waitForTimeout(100);
      }
    } else {
      loginVisible = await signInVisible(page);
    }
    const currentLocation = new URL(page.url());
    const authRequired = knownSignInLocation(currentLocation, host)
      || (loginVisible && currentLocation.hostname.toLowerCase() === host);
    if (!routeMatches && !authRequired) {
      const routeHost = currentLocation.hostname.toLowerCase();
      throw stageError('route', routeHost === host ? 'route-invalid' : 'host-mismatch');
    }
    if (routeMatches && !setupVisible && !authRequired) throw stageError('route', 'route-invalid');
    return { browser, context, page, providerCalls: () => providerCalls,
      expectedHost: host, authRequired, authenticated: !authRequired,
      uiAttemptedFirst: true };
  } catch (error) {
    try { await browser.close(); } catch (_) { /* discard close diagnostics */ }
    throw error && error.stage ? error : stageError('route', 'evaluation-failed');
  }
}

async function authenticateSession(request, session) {
  validateFrontdoor(request);
  if (!session.authRequired || session.authenticated) throw stageError('authenticate', 'identity-mismatch');
  const { page, expectedHost: host } = session;
  await page.goto(request.login_url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForURL(url => url.protocol === 'https:'
    && url.hostname.toLowerCase() === host
    && url.hostname.toLowerCase().endsWith('.lightning.force.com')
    && !url.pathname.includes('frontdoor'), { timeout: 60000 });
  await page.goto(`https://${host}${ROUTE}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  const routed = new URL(page.url());
  if (routed.protocol !== 'https:' || routed.hostname.toLowerCase() !== host || routed.pathname !== ROUTE) {
    throw stageError('route', 'route-invalid');
  }
  await region(page, 'Setup status');
  session.authenticated = true;
  return true;
}

function routeProjection(page, request) {
  const url = new URL(page.url());
  return { route_host: url.hostname.toLowerCase(), route_path: url.pathname,
    browser_version: request.browser_version || null };
}

function publicProjection(observer, page, request, result = {}) {
  const route = routeProjection(page, request);
  return { status: 'ok', ...result, route_host: route.route_host, route_path: route.route_path,
    browser_version: page.context().browser().version(), controller_calls: observer.projection() };
}

function attemptProjection(session, observer, request) {
  return { status: 'ok', schema: 'shiploop-grok-chat-full-ui-observation/1',
    mode: request.mode, phase: request.phase, source_head: request.source_head,
    candidate_metadata_sha256: request.candidate_metadata_sha256,
    ui_attempted_first: session.uiAttemptedFirst === true,
    auth_required: session.authRequired === true,
    route_host: session.expectedHost, route_path: ROUTE,
    browser_version: session.browser.version(), controller_calls: observer.projection() };
}

async function expectConversation(observer, conversationId, startAt = 0, predicate = () => true) {
  const call = await observer.waitFor('getConversation', item =>
    item.params.conversationId === conversationId && item.result.conversationId === conversationId
      && predicate(item.result), 45000, startAt);
  if (!call) throw stageError('reload', 'conversation-missing');
  return call.result;
}

async function waitSetupStatus(page, status) {
  const setup = await region(page, 'Setup status');
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {
    const text = (await setup.innerText()).toLowerCase();
    if (text.includes(status)) return text;
    await page.waitForTimeout(150);
  }
  throw stageError('render', status === 'missing' ? 'setup-not-missing' : 'ui-state-invalid');
}

async function runStep(request, session, observer) {
  const { page } = session;
  const step = request.step;
  const common = { schema: 'shiploop-grok-chat-full-ui-observation/1', mode: request.mode,
    phase: request.phase, source_head: request.source_head,
    candidate_metadata_sha256: request.candidate_metadata_sha256 };

  if (step === 'observe') {
    const setupText = await (await region(page, 'Setup status')).innerText();
    const result = await observer.waitFor('getSetup', () => true, 45000, 0);
    const visibleState = /\bmissing\b/i.test(setupText) ? 'missing'
      : /\bready\b/i.test(setupText) ? 'ready' : /\berror\b/i.test(setupText) ? 'error' : 'invalid';
    if (visibleState !== result.result.status) throw stageError('observe', 'ui-state-invalid');
    await screenshot(page, request, 'setup-desktop');
    return publicProjection(observer, page, request, { ...common,
      observed_setup_status: result.result.status,
      screenshots: 1 });
  }

  const runId = request.run_id;
  const conversationId = request.conversation_id;
  const screenshots = request.screenshots;
  if (step === 'setup') {
    const setupCursor = observer.mark();
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
    await region(page, 'Setup status');
    const initialCall = await observer.waitFor('getSetup', () => true, 45000, setupCursor);
    if (!initialCall || initialCall.result.status !== 'missing') throw stageError('setup-missing', 'setup-not-missing');
    await waitSetupStatus(page, 'missing');
    await screenshot(page, request, 'setup-missing');
    const preSetup = observer.records.slice(setupCursor).filter(record => record.sequence <= initialCall.sequence);
    if (preSetup.some(record => ['testConnection', 'newConversation', 'sendMessage'].includes(record.method))) {
      throw stageError('setup-missing', 'chat-attempted-before-setup');
    }
    const keyboardOk = await keyboardCheck(page);
    await (await input(page, 'Named credential')).fill(request.named_credential);
    await (await input(page, 'Model')).fill(request.model);
    const saveCursor = observer.mark();
    if (observer.records.slice(setupCursor, saveCursor).some(record =>
      ['testConnection', 'newConversation', 'sendMessage'].includes(record.method))) {
      throw stageError('setup-missing', 'chat-attempted-before-setup');
    }
    const save = await button(page, 'Save setup');
    await save.focus();
    await page.keyboard.press('Enter');
    const saved = await observer.waitFor('saveSetup', record =>
      record.result.status === 'ready' && record.params.namedCredential === request.named_credential
        && record.params.model === request.model, 60000, saveCursor);
    await waitSetupStatus(page, 'ready');
    await screenshot(page, request, 'setup-desktop');
    const connectionCursor = observer.mark();
    await click(page, 'Test connection');
    const connection = await observer.waitFor('testConnection', record => record.result.status === 'ok', 120000, connectionCursor);
    const recheckCursor = observer.mark();
    await click(page, 'Recheck setup');
    const recheck = await observer.waitFor('getSetup', record => record.result.status === 'ready', 45000, recheckCursor);
    const newCursor = observer.mark();
    await click(page, 'New conversation');
    const newConversation = await observer.waitFor('newConversation', record => !!record.result.conversationId, 45000, newCursor);
    await region(page, 'Conversation');
    const desktopLayoutOk = await checkLayout(page, 1280, 900);
    const narrowLayoutOk = await checkLayout(page, 390, 844);
    await screenshot(page, request, 'setup-narrow');
    await page.setViewportSize({ width: 1280, height: 900 });
    await observer.settle();
    return publicProjection(observer, page, request, { ...common,
      setup_missing_without_chat_attempt: true,
      connection_ok: connection.result.status === 'ok', recheck_ready: recheck.result.status === 'ready',
      new_conversation: true, conversation_id: newConversation.result.conversationId,
      desktop_layout_ok: desktopLayoutOk,
      narrow_layout_ok: narrowLayoutOk, keyboard_ok: keyboardOk,
      saved_setup_status: saved.result.status, screenshots: 2,
      provider_calls: session.providerCalls(), run_id: runId });
  }

  if (step === 'seed') {
    const seedCursor = observer.mark();
    await click(page, 'Seed demo items');
    const seeded = await observer.waitFor('seedItems', record => record.result.recordIds.length > 0, 45000, seedCursor);
    return publicProjection(observer, page, request, { ...common, seed_record_ids: seeded.result.recordIds });
  }

  const current = await expectConversation(observer, conversationId);
  const makeMessage = async content => writeMessage(page, observer, conversationId, content);
  if (step === 'read-tool') {
    const readPrompt = `Find the demo item named ${request.selected_name}, read it, and tell me its Notes__c value exactly.`;
    const read = await makeMessage(readPrompt);
    const resultProof = findItemResult(read.conversation, request.selected_record_id,
      request.selected_name, request.note_payload);
    const conversationRegion = await region(page, 'Conversation');
    const conversationText = await conversationRegion.innerText();
    const textPresent = conversationText.includes(request.nonce);
    const markupTextSafe = await noUnsafeMarkup(request.note_payload, conversationRegion);
    const persisted = read.conversation.conversationId === conversationId
      && read.conversation.messages.some(message => message.role === 'assistant' && message.content.includes(request.nonce))
      && read.conversation.toolCalls.some(call => call.name === 'read_item');
    const promptExcludedNonce = !read.call.params.message.includes(request.nonce)
      && !read.call.params.message.includes(request.note_payload);
    read.call.ui_correlated = resultProof.find && resultProof.read && resultProof.result && textPresent;
    const desktopLayoutOk = await checkLayout(page, 1280, 900);
    await screenshot(page, request, 'pending-desktop');
    await page.setViewportSize({ width: 390, height: 844 });
    const narrowLayoutOk = await checkLayout(page, 390, 844);
    await screenshot(page, request, 'chat-narrow');
    await observer.settle();
    return publicProjection(observer, page, request, { ...common,
      read_tool_proof: { find_items: resultProof.find, read_item: resultProof.read,
        result_matches_nonce: resultProof.result, assistant_used_result: textPresent && persisted,
        conversation_persisted: persisted, prompt_excluded_nonce: promptExcludedNonce,
        unsafe_markup_is_text: markupTextSafe },
      desktop_layout_ok: desktopLayoutOk, narrow_layout_ok: narrowLayoutOk,
      safe_text_ok: markupTextSafe, conversation_id: current.conversationId,
      provider_calls: session.providerCalls(), screenshots: 2 });
  }

  if (step === 'create-proposal') {
    const content = `Create one work item named ${request.create_name}, with Status__c Open and Notes__c ${request.create_notes}. Show the exact proposal and wait for my confirmation.`;
    const sent = await makeMessage(content);
    const toolProposal = hasToolCall(sent.conversation, 'propose_create_item', args =>
      exactKeys(args, ['fields']) && isRecord(args.fields)
      && args.fields.Name === request.create_name && args.fields.Status__c === 'Open'
      && args.fields.Notes__c === request.create_notes && Object.keys(args.fields).length === 3);
    if (!toolProposal) throw stageError('create-proposal', 'proposal-mismatch');
    const action = findAction(sent.conversation, 'create', entry => entry.recordId === null
      && entry.newValues.Name === request.create_name && entry.newValues.Status__c === 'Open'
      && entry.newValues.Notes__c === request.create_notes && Object.keys(entry.newValues).length === 3);
    if (!action) throw stageError('create-proposal', 'proposal-mismatch');
    const proposed = await proposalRegion(page, request.create_name);
    const visible = await proposed.innerText();
    if (!/\bcreate\b/i.test(visible) || !visible.includes(request.create_name)
        || !visible.includes(request.create_notes) || !visible.includes('Open')) {
      throw stageError('create-proposal', 'proposal-mismatch');
    }
    sent.call.ui_correlated = true;
    await page.setViewportSize({ width: 1280, height: 900 });
    await screenshot(page, request, 'pending-desktop');
    await observer.settle();
    return publicProjection(observer, page, request, { ...common,
      proposal_exact: true, action_id: action.actionId, conversation_id: conversationId,
      provider_calls: session.providerCalls() });
  }

  if (step === 'create-confirm') {
    const proposal = await proposalRegion(page, request.create_name);
    if (!proposal) throw stageError(step, 'proposal-missing');
    const confirmCursor = observer.mark();
    const confirm = proposal.getByRole('button', { name: 'Confirm', exact: true });
    await confirm.first().waitFor({ state: 'visible' });
    // Retry through the public button. A disabled/removed control proves that the UI
    // prevented the duplicate; an enabled control may deliver a second request.
    await confirm.first().click();
    let duplicateAttempted = true;
    try {
      await confirm.first().click({ timeout: 1500 });
    } catch (_) {
      const remainsAvailable = await confirm.first().isVisible().catch(() => false)
        && await confirm.first().isEnabled().catch(() => false);
      if (remainsAvailable) throw stageError(step, 'ui-control-missing');
    }
    const applied = await observer.waitFor('confirmAction', record =>
      record.params.actionId === request.create_action_id && record.result.status === 'applied', 90000, confirmCursor);
    applied.ui_correlated = true;
    await actionStatus(page, 'applied');
    const reloadCursor = observer.mark();
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
    await region(page, 'Conversation');
    const reopened = await expectConversation(observer, conversationId, reloadCursor,
      value => value.actions.some(action => action.actionId === request.create_action_id && action.status === 'applied'));
    const actionAfterReload = reopened.actions.find(action => action.actionId === request.create_action_id);
    const statusPersisted = actionAfterReload && actionAfterReload.status === 'applied';
    await observer.settle();
    const confirmCalls = observer.records.slice(confirmCursor).filter(record => record.method === 'confirmAction'
      && record.params.actionId === request.create_action_id && record.response_state === 'SUCCESS');
    for (const record of confirmCalls) record.ui_correlated = true;
    const duplicateSafe = duplicateAttempted
      && (confirmCalls.length === 1 || confirmCalls.length === 2)
      && confirmCalls.every(record => ['applied', 'rejected'].includes(record.result.status));
    await observer.settle();
    return publicProjection(observer, page, request, { ...common,
      one_write: applied.result.status === 'applied', duplicate_safe: duplicateSafe,
      duplicate_attempted: duplicateAttempted, duplicate_delivery_count: confirmCalls.length,
      reload_history_persisted: statusPersisted, action_id: request.create_action_id,
      conversation_id: conversationId, provider_calls: session.providerCalls() });
  }

  if (step === 'update-proposal') {
    const content = `Update the demo item named ${request.selected_name} so Status__c is Done. Leave all other fields unchanged and wait for confirmation.`;
    const sent = await makeMessage(content);
    const toolProposal = hasToolCall(sent.conversation, 'propose_update_item', args =>
      exactKeys(args, ['recordId', 'fields']) && args.recordId === request.selected_record_id
      && exactKeys(args.fields, ['Status__c']) && args.fields.Status__c === 'Done');
    if (!toolProposal) throw stageError(step, 'proposal-mismatch');
    const action = findAction(sent.conversation, 'update', entry => entry.recordId === request.selected_record_id
      && Object.keys(entry.newValues).length === 1 && entry.newValues.Status__c === 'Done'
      && entry.oldValues.Status__c === 'Open');
    if (!action) throw stageError(step, 'proposal-mismatch');
    const proposed = await proposalRegion(page, request.selected_name);
    const visible = await proposed.innerText();
    if (!/\bupdate\b/i.test(visible) || !visible.includes('Open') || !visible.includes('Done')) {
      throw stageError(step, 'proposal-mismatch');
    }
    sent.call.ui_correlated = true;
    return publicProjection(observer, page, request, { ...common, proposal_exact: true,
      action_id: action.actionId, conversation_id: conversationId, provider_calls: session.providerCalls() });
  }

  if (step === 'update-confirm') {
    const proposed = await proposalRegion(page, request.selected_name);
    const cursor = observer.mark();
    await proposed.getByRole('button', { name: 'Confirm', exact: true }).click();
    const applied = await observer.waitFor('confirmAction', record =>
      record.params.actionId === request.update_action_id && record.result.status === 'applied', 90000, cursor);
    applied.ui_correlated = true;
    await actionStatus(page, 'applied');
    return publicProjection(observer, page, request, { ...common, one_write: applied.result.status === 'applied',
      action_id: request.update_action_id, conversation_id: conversationId, provider_calls: session.providerCalls() });
  }

  if (step === 'cancel-proposal') {
    const content = `Create one work item named ${request.cancel_name}, with Status__c Open and Notes__c ${request.cancel_notes}. Wait for confirmation.`;
    const sent = await makeMessage(content);
    const toolProposal = hasToolCall(sent.conversation, 'propose_create_item', args =>
      exactKeys(args, ['fields']) && isRecord(args.fields)
      && args.fields.Name === request.cancel_name && args.fields.Status__c === 'Open'
      && args.fields.Notes__c === request.cancel_notes && Object.keys(args.fields).length === 3);
    if (!toolProposal) throw stageError(step, 'proposal-mismatch');
    const action = findAction(sent.conversation, 'create', entry => entry.recordId === null
      && entry.newValues.Name === request.cancel_name && entry.newValues.Status__c === 'Open'
      && entry.newValues.Notes__c === request.cancel_notes && Object.keys(entry.newValues).length === 3);
    if (!action) throw stageError(step, 'proposal-mismatch');
    const proposed = await proposalRegion(page, request.cancel_name);
    const visible = await proposed.innerText();
    if (!visible.includes(request.cancel_notes) || !visible.includes('Open')) throw stageError(step, 'proposal-mismatch');
    sent.call.ui_correlated = true;
    return publicProjection(observer, page, request, { ...common, proposal_exact: true,
      action_id: action.actionId, conversation_id: conversationId, provider_calls: session.providerCalls() });
  }

  if (step === 'cancel-confirm') {
    const proposed = await proposalRegion(page, request.cancel_name);
    const cursor = observer.mark();
    await proposed.getByRole('button', { name: 'Cancel', exact: true }).click();
    const cancelled = await observer.waitFor('cancelAction', record =>
      record.params.actionId === request.cancel_action_id && record.result.status === 'cancelled', 90000, cursor);
    cancelled.ui_correlated = true;
    await actionStatus(page, 'cancelled');
    const reloadCursor = observer.mark();
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
    await region(page, 'Conversation');
    const reloaded = await expectConversation(observer, conversationId, reloadCursor,
      value => value.actions.some(action => action.actionId === request.cancel_action_id && action.status === 'cancelled'));
    const history = reloaded.actions.find(action => action.actionId === request.cancel_action_id);
    return publicProjection(observer, page, request, { ...common,
      cancelled_absent: cancelled.result.status === 'cancelled' && history && history.status === 'cancelled',
      action_id: request.cancel_action_id, conversation_id: conversationId,
      provider_calls: session.providerCalls() });
  }

  if (step === 'stale-proposal') {
    const content = `Update the demo item named ${request.selected_name} Notes__c to ${request.stale_notes}. Do not change any other field and wait for confirmation.`;
    const sent = await makeMessage(content);
    const toolProposal = hasToolCall(sent.conversation, 'propose_update_item', args =>
      exactKeys(args, ['recordId', 'fields']) && args.recordId === request.selected_record_id
      && exactKeys(args.fields, ['Notes__c']) && args.fields.Notes__c === request.stale_notes);
    if (!toolProposal) throw stageError(step, 'proposal-mismatch');
    const action = findAction(sent.conversation, 'update', entry => entry.recordId === request.selected_record_id
      && Object.keys(entry.newValues).length === 1 && entry.newValues.Notes__c === request.stale_notes
      && entry.oldValues.Notes__c === request.note_payload);
    if (!action) throw stageError(step, 'proposal-mismatch');
    const proposed = await proposalRegion(page, request.selected_name);
    const visible = await proposed.innerText();
    if (!visible.includes(request.nonce) || !visible.includes(request.stale_notes)) {
      throw stageError(step, 'proposal-mismatch');
    }
    sent.call.ui_correlated = true;
    return publicProjection(observer, page, request, { ...common, proposal_exact: true,
      action_id: action.actionId, conversation_id: conversationId, provider_calls: session.providerCalls() });
  }

  if (step === 'stale-confirm') {
    const proposed = await proposalRegion(page, request.selected_name);
    const cursor = observer.mark();
    await proposed.getByRole('button', { name: 'Confirm', exact: true }).click();
    const stale = await observer.waitFor('confirmAction', record =>
      record.params.actionId === request.stale_action_id && record.result.status === 'stale', 90000, cursor);
    stale.ui_correlated = true;
    await actionStatus(page, 'stale');
    const reloadCursor = observer.mark();
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
    await region(page, 'Conversation');
    const reopened = await expectConversation(observer, conversationId, reloadCursor,
      value => value.actions.some(action => action.actionId === request.stale_action_id && action.status === 'stale'));
    const history = reopened.actions.find(action => action.actionId === request.stale_action_id);
    const statusPersisted = history && history.status === 'stale';
    const narrowLayoutOk = await checkLayout(page, 390, 844);
    await screenshot(page, request, 'chat-narrow');
    await observer.settle();
    return publicProjection(observer, page, request, { ...common,
      stale_rejected: stale.result.status === 'stale', reload_history_persisted: statusPersisted,
      narrow_layout_ok: narrowLayoutOk, action_id: request.stale_action_id,
      conversation_id: conversationId, provider_calls: session.providerCalls() });
  }

  throw stageError('browser', 'invalid-options');
}

function validateRequest(request) {
  if (!isRecord(request) || !['observe', 'run'].includes(request.mode)
      || !['builder', 'final'].includes(request.phase)
      || !['attempt', 'authenticate', 'observe', 'setup', 'seed', 'read-tool', 'create-proposal', 'create-confirm',
        'update-proposal', 'update-confirm', 'cancel-proposal', 'cancel-confirm',
        'stale-proposal', 'stale-confirm'].includes(request.step)
      || typeof request.ipc_id !== 'string' || !/^\d+$/.test(request.ipc_id)
      || request.controller_class !== CONTROLLER || request.prefix !== PREFIX
      || request.step === 'authenticate' && typeof request.login_url !== 'string'
      || request.step !== 'authenticate' && request.login_url !== undefined
      || request.mode === 'observe' && !['attempt', 'authenticate', 'observe'].includes(request.step)
      || request.mode === 'run' && request.step === 'observe'
      || typeof request.expected_lightning_host !== 'string'
      || !/^[a-z0-9.-]+\.lightning\.force\.com$/i.test(request.expected_lightning_host)
      || typeof request.source_head !== 'string' || typeof request.candidate_metadata_sha256 !== 'string'
      || !request.screenshots || typeof request.screenshots !== 'object') {
    throw stageError('browser', 'invalid-options');
  }
  const root = process.env.E2E_PLATFORM_DIR;
  if (!root) throw stageError('browser', 'platform-unavailable');
  for (const target of Object.values(request.screenshots)) {
    if (typeof target !== 'string' || !path.isAbsolute(target)
        || !path.resolve(target).startsWith(path.resolve(root) + path.sep)) {
      throw stageError('browser', 'screenshot-missing');
    }
  }
  const requiredByStep = {
    setup: ['named_credential', 'model', 'run_id'],
    seed: ['run_id'],
    'read-tool': ['conversation_id', 'selected_record_id', 'selected_name', 'nonce', 'note_payload'],
    'create-proposal': ['conversation_id', 'selected_record_id', 'selected_name', 'nonce', 'note_payload', 'create_name', 'create_notes'],
    'create-confirm': ['conversation_id', 'create_name', 'create_action_id'],
    'update-proposal': ['conversation_id', 'selected_record_id', 'selected_name', 'nonce', 'note_payload'],
    'update-confirm': ['conversation_id', 'selected_record_id', 'selected_name', 'update_action_id'],
    'cancel-proposal': ['conversation_id', 'selected_record_id', 'selected_name', 'nonce', 'note_payload', 'cancel_name', 'cancel_notes'],
    'cancel-confirm': ['conversation_id', 'cancel_name', 'cancel_action_id'],
    'stale-proposal': ['conversation_id', 'selected_record_id', 'selected_name', 'nonce', 'note_payload', 'stale_notes'],
    'stale-confirm': ['conversation_id', 'selected_record_id', 'selected_name', 'nonce', 'note_payload',
      'stale_notes', 'external_notes', 'stale_action_id', 'create_action_id', 'update_action_id', 'cancel_action_id'],
  }[request.step] || [];
  if (requiredByStep.some(key => request[key] === undefined || request[key] === null)) {
    throw stageError('browser', 'invalid-options');
  }
  if (request.step === 'setup' && (request.named_credential !== NAMED_CREDENTIAL || request.model !== MODEL)) {
    throw stageError('browser', 'invalid-options');
  }
  if (request.mode === 'run' && !['attempt', 'authenticate'].includes(request.step)
      && !/^[a-f0-9]{12}$/.test(request.run_id)) {
    throw stageError('browser', 'invalid-options');
  }
  if (request.step === 'create-proposal'
      && (request.create_name !== `Grok Demo Create ${request.run_id}`
        || request.create_notes !== `Synthetic create note ${request.run_id}`)) {
    throw stageError('browser', 'invalid-options');
  }
  if (request.step === 'cancel-proposal'
      && (request.cancel_name !== `Grok Demo Cancel ${request.run_id}`
        || request.cancel_notes !== `Synthetic cancelled note ${request.run_id}`)) {
    throw stageError('browser', 'invalid-options');
  }
  if (request.step !== 'attempt' && request.step !== 'authenticate'
      && (!/^[a-f0-9]{40,64}$/.test(request.source_head)
        || !/^[a-f0-9]{64}$/.test(request.candidate_metadata_sha256))) {
    throw stageError('source', 'source-invalid');
  }
  if (request.step === 'attempt' && (!/^[a-f0-9]{40,64}$/.test(request.source_head)
      || !/^[a-f0-9]{64}$/.test(request.candidate_metadata_sha256))) {
    throw stageError('source', 'source-invalid');
  }
  return request;
}

async function main() {
  let session;
  let observer;
  const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
  try {
    for await (const line of input) {
      if (!line.trim()) continue;
      let request;
      let stage = 'browser';
      try {
        const parsed = JSON.parse(line);
        if (isRecord(parsed) && parsed.close === true) break;
        request = validateRequest(parsed);
        if (!session) {
          if (request.step !== 'attempt') throw stageError('browser', 'invalid-options');
          observer = new ApexObserver(null, request.expected_lightning_host);
          stage = 'route';
          session = await createSession(request, observer);
          session.uiAttemptedFirst = true;
          session.binding = {
            phase: request.phase, source_head: request.source_head,
            candidate_metadata_sha256: request.candidate_metadata_sha256,
            expected_lightning_host: request.expected_lightning_host,
          };
        } else if (session.binding.phase !== request.phase
            || session.binding.source_head !== request.source_head
            || session.binding.candidate_metadata_sha256 !== request.candidate_metadata_sha256
            || session.binding.expected_lightning_host !== request.expected_lightning_host) {
          throw stageError('source', 'source-changed');
        }
        stage = request.step;
        let result;
        if (request.step === 'attempt') {
          result = attemptProjection(session, observer, request);
        } else if (request.step === 'authenticate') {
          await authenticateSession(request, session);
          await observer.settle();
          result = publicProjection(observer, session.page, request,
            { schema: 'shiploop-grok-chat-full-ui-observation/1', mode: request.mode,
              phase: request.phase, source_head: request.source_head,
              candidate_metadata_sha256: request.candidate_metadata_sha256,
              ui_attempted_first: session.uiAttemptedFirst, authenticated: true });
        } else {
          if (session.authRequired && !session.authenticated) {
            throw stageError('authenticate', 'identity-mismatch');
          }
          result = await runStep(request, session, observer);
        }
        if (session.providerCalls() > 0) throw stageError('controller', 'browser-provider-call');
        await observer.settle();
        process.stdout.write(JSON.stringify({ ...result, ipc_id: request.ipc_id }) + '\n');
      } catch (error) {
        process.stdout.write(JSON.stringify({
          status: 'failed', ipc_id: request && request.ipc_id,
          stage: SAFE_STAGES.has(error && error.stage) ? error.stage : stage,
          reason: SAFE_REASONS.has(error && error.reason) ? error.reason : 'evaluation-failed',
        }) + '\n');
        process.exitCode = 1;
        break;
      }
    }
  } finally {
    input.close();
    if (session && session.context) {
      try { await session.context.close(); } catch (_) { /* omit browser close failures */ }
    }
    if (session && session.browser) {
      try { await session.browser.close(); } catch (_) { /* omit browser close failures */ }
    }
  }
}

async function inspectFixture(url, viewport = { width: 1280, height: 900 }) {
  const fixtureRoot = path.resolve(__dirname, '../../fixtures/grok-chat-full-ui/dom');
  const fixturePath = path.resolve(fileURLToPath(new URL(url)));
  const validViewport = (viewport.width === 1280 && viewport.height === 900)
    || (viewport.width === 390 && viewport.height === 844);
  if (!fixturePath.startsWith(fixtureRoot + path.sep) || !validViewport
      || fs.lstatSync(fixturePath).isSymbolicLink() || !fs.statSync(fixturePath).isFile()) {
    throw stageError('browser', 'invalid-options');
  }
  const { chromium } = pinnedBrowser.playwrightModule();
  const executablePath = pinnedBrowser.browserExecutable();
  const browser = await chromium.launch({ headless: true,
    ...(executablePath ? { executablePath } : {}),
    args: ['--password-store=basic', '--use-mock-keychain', '--disable-features=DialMediaRouteProvider'] });
  try {
    const page = await browser.newPage({ viewport });
    await page.goto(url, { waitUntil: 'domcontentloaded' });
    const controls = {};
    for (const label of ['Named credential', 'Model', 'Message']) {
      controls[label] = await page.getByLabel(label, { exact: true }).count();
    }
    for (const label of ['Save setup', 'Test connection', 'Recheck setup', 'Setup', 'New conversation',
      'Send', 'Confirm', 'Cancel', 'Seed demo items']) {
      controls[label] = await page.getByRole('button', { name: label, exact: true }).count();
    }
    controls.setupStatusRegion = await page.getByRole('region', { name: 'Setup status', exact: true }).count();
    controls.conversationRegion = await page.getByRole('region', { name: 'Conversation', exact: true }).count();
    controls.chatStatusRegion = await page.getByRole('region', { name: 'Chat status', exact: true }).count();
    controls.proposedChangeRegion = await page.getByRole('region', { name: 'Proposed change', exact: true }).count();
    controls.actionStatusRegion = await page.getByRole('region', { name: 'Action status', exact: true }).count();
    return controls;
  } finally { await browser.close(); }
}

module.exports = {
  METHODS, SAFE_STAGES, SAFE_REASONS, decodeAura, parseAuraRequest, pairAuraActions, parseOnceJsonString,
  normalizeResult, normalizeConversation, ApexObserver, validateRequest, inspectFixture,
};

if (require.main === module) main();
