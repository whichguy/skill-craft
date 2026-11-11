'use strict';

// Bounded Grok chat UI journey. The trusted frontdoor URL arrives on stdin and
// is never logged, returned, written, or included in an error.
const fs = require('node:fs');
const { createHash } = require('node:crypto');
const path = require('node:path');
const readline = require('node:readline');
const { fileURLToPath } = require('node:url');
const { isDeepStrictEqual } = require('node:util');
const pinnedBrowser = require('./battleship_ui_browser.cjs');

const CONTROLLER = 'SLGrokChatController';
const PREFIX = 'SLGrokChat';
const ROUTE = '/lightning/n/SLGrokChat_Chat';
const APP_ROOT = 'c-sl-grok-chat-app:visible';
const TEXT_FIELDS = ['Named credential', 'Model', 'Message'];
const NATIVE_TEXT_FIELD = 'textarea, input:not([type]), input:is([type="text" i], [type="search" i], '
  + '[type="email" i], [type="tel" i], [type="url" i], [type="password" i])';
const NAMED_CREDENTIAL = 'Grok_Chat_Model';
const MODEL = 'grok-4.7';
const METHODS = new Set([
  'getSetup', 'saveSetup', 'testConnection', 'newConversation',
  'getConversation', 'sendMessage', 'confirmAction', 'cancelAction', 'seedItems',
]);
const SPLIT_METHODS = new Set(['beginMessage', 'executePendingMessage']);
const TURN_METHODS = new Set(['sendMessage', ...SPLIT_METHODS]);
const CHAT_ATTEMPTS = new Set([
  'testConnection', 'newConversation', ...TURN_METHODS,
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
const SERVER_REQUEST_ID_RE = /^[A-Za-z0-9_-]{1,84}$/;
const FIELDS = new Set(['Name', 'Status__c', 'Notes__c']);
const SUCCESS_TOOL_STATES = new Set(['ok', 'success', 'completed', 'succeeded']);
const CARD = 'article, li, fieldset, [role="article"], [role="listitem"], [role="group"]';
const PROPOSAL_TEXT_BOUNDARY = 'article, li, [role="article"], [role="listitem"], [aria-label="Action status"]';
const MESSAGE_METADATA = 'time[datetime], [aria-label="Message metadata"]';

function digest(text) {
  return createHash('sha256').update(text).digest('hex');
}

function serverRequestId(headers) {
  // Retain only Salesforce's bounded correlation ID, never response headers.
  // The operator joins this to the native ApexLog ID (observed as TID:<id>).
  const value = headers && headers['x-sfdc-request-id'];
  if (typeof value !== 'string' || !SERVER_REQUEST_ID_RE.test(value)
      || headers['x-request-id'] !== undefined && headers['x-request-id'] !== value) {
    throw stageError('controller', 'controller-proof-missing');
  }
  return value;
}

function nonemptyString(value) {
  return typeof value === 'string' && !!value.trim();
}

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
  if (controller !== controllerClass || (!METHODS.has(method) && !SPLIT_METHODS.has(method))) return null;
  if (params === undefined || params === null) params = {};
  if (!isRecord(params)) throw stageError('controller', 'controller-action-invalid');
  const expected = {
    getSetup: [], saveSetup: ['model', 'namedCredential'], testConnection: [], newConversation: [],
    getConversation: ['conversationId'], sendMessage: ['conversationId', 'message'],
    beginMessage: ['conversationId', 'message', 'clientRequestId'],
    executePendingMessage: ['conversationId', 'turnToken'],
    confirmAction: ['actionId'], cancelAction: ['actionId'], seedItems: [],
  }[method];
  if (!exactKeys(params, expected)) throw stageError('controller', 'controller-action-invalid');
  if (method === 'saveSetup'
      && (params.namedCredential !== 'Grok_Chat_Model' || params.model !== 'grok-4.7')) {
    throw stageError('controller', 'controller-action-invalid');
  }
  if ((method === 'getConversation' || TURN_METHODS.has(method))
      && (typeof params.conversationId !== 'string' || !SF_ID_RE.test(params.conversationId))) {
    throw stageError('controller', 'controller-action-invalid');
  }
  if ((method === 'sendMessage' || method === 'beginMessage') && !nonemptyString(params.message)
      || method === 'beginMessage' && !nonemptyString(params.clientRequestId)
      || method === 'executePendingMessage' && !nonemptyString(params.turnToken)) {
    throw stageError('controller', 'controller-action-invalid');
  }
  if ((method === 'confirmAction' || method === 'cancelAction')
      && !ACTION_ID_RE.test(params.actionId || '')) throw stageError('controller', 'controller-action-invalid');
  return { id: action.id, method, params, transport: execute ? 'lwc' : 'direct' };
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
  if (!isRecord(value) || typeof value.conversationId !== 'string' || !SF_ID_RE.test(value.conversationId)
      || !Array.isArray(value.messages) || !Array.isArray(value.actions) || !Array.isArray(value.toolCalls)) return null;
  const messages = [];
  for (const message of value.messages) {
    if (!isRecord(message) || !['system', 'developer', 'user', 'assistant', 'tool'].includes(message.role)
        || typeof message.content !== 'string') return null;
    messages.push({ role: message.role, content: message.content });
  }
  const actions = value.actions.map(normalizeAction);
  const toolCalls = value.toolCalls.map(normalizeToolCall);
  if (actions.some(item => item === null) || toolCalls.some(item => item === null)) return null;
  return { conversationId: value.conversationId, messages, actions, toolCalls, hasPending: value.pending != null,
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
  if (method === 'getConversation' || TURN_METHODS.has(method)) {
    const conversation = normalizeConversation(value);
    if (!conversation) throw stageError('controller', 'controller-response-invalid');
    if (method === 'beginMessage') {
      const pending = value.pending;
      if (conversation.status !== 'working' || !isRecord(pending) || !nonemptyString(pending.token)
          || Object.hasOwn(value, 'turnToken') && value.turnToken !== pending.token
          || Object.hasOwn(value, 'turnStatus') && value.turnStatus !== 'working'
          || Object.hasOwn(pending, 'status') && pending.status !== 'working') {
        throw stageError('controller', 'controller-response-invalid');
      }
      // The capability exists only in the in-flight Aura payload. Keep digests
      // even in the observer so a projection cannot retain the raw token.
      conversation.pendingTokenDigest = digest(pending.token);
      for (const name of ['requestId', 'message', 'messageHash']) {
        if (Object.hasOwn(pending, name)) conversation[name] = pending[name];
      }
    } else if (TURN_METHODS.has(method)
        && (conversation.hasPending || Object.hasOwn(value, 'turnStatus') && value.turnStatus !== 'completed')) {
      throw stageError('controller', 'controller-response-invalid');
    }
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

function parseAuraRequest(value, controllerClass, trackSplit = true) {
  const actions = decodeAura(value, 'controller-action-invalid');
  const found = [];
  const seen = new Set();
  const counts = new Map();
  for (const action of actions) {
    if (isRecord(action) && typeof action.id === 'string') counts.set(action.id, (counts.get(action.id) || 0) + 1);
  }
  for (const action of actions) {
    if (!isRecord(action)) continue;
    let descriptor = action.descriptor;
    let target = null;
    let method = null;
    if (typeof descriptor === 'string') {
      const direct = /^apex:\/\/([^/]+)\/ACTION\$/i.exec(descriptor);
      const wrapped = /^(?:aura|apex):\/\/ApexActionController\/ACTION\$execute$/i.test(descriptor);
      target = direct ? direct[1] : (wrapped && isRecord(action.params) ? action.params.classname : null);
      method = direct ? descriptor.slice(direct[0].length)
        : (wrapped && isRecord(action.params) ? action.params.method : null);
    }
    if (target !== controllerClass) continue;
    // Other supporting RPCs may share a batch. Only the documented split
    // transport is eligible for a Send proof.
    if (typeof method === 'string' && /^[A-Za-z][A-Za-z0-9_]*$/.test(method)
        && !METHODS.has(method) && !(trackSplit && SPLIT_METHODS.has(method))) continue;
    const normalized = requestMethod(action, controllerClass);
    if (!normalized || seen.has(normalized.id) || counts.get(normalized.id) !== 1) {
      throw stageError('controller', 'controller-action-invalid');
    }
    seen.add(normalized.id);
    found.push(normalized);
  }
  return found;
}

function chatAttempts(value) {
  return decodeAura(value, 'controller-action-invalid').flatMap(action => {
    if (!isRecord(action) || typeof action.descriptor !== 'string') return [];
    const direct = /^apex:\/\/([^/]+)\/ACTION\$([A-Za-z][A-Za-z0-9_]*)$/i.exec(action.descriptor);
    const wrapped = /^(?:aura|apex):\/\/ApexActionController\/ACTION\$execute$/i.test(action.descriptor);
    const method = direct && direct[1] === CONTROLLER ? direct[2] : wrapped && isRecord(action.params)
      && action.params.classname === CONTROLLER ? action.params.method : null;
    return CHAT_ATTEMPTS.has(method) ? [method] : [];
  });
}

function assertNoChatBeforeSetup(observer, cursor) {
  if (observer.chatRequests.length !== cursor) {
    throw stageError('setup-missing', 'chat-attempted-before-setup');
  }
}

// Only checker-created errors may contribute a diagnostic code. Provider or
// browser Error properties are untrusted text, just like their messages.
const DIAGNOSTIC_METADATA = new WeakMap();

function safeErrorCode(error, key, allowed, fallback) {
  try {
    const value = error == null ? undefined : error[key];
    return allowed.has(value) ? value : fallback;
  } catch (_) { return fallback; }
}

function diagnosticError(reason, branch) {
  const error = stageError('controller', reason);
  DIAGNOSTIC_METADATA.set(error, { branch });
  return error;
}

function pairAuraActions(requests, responseBody) {
  let responses;
  try { responses = decodeAura(responseBody, 'controller-response-invalid'); }
  catch (_) { throw diagnosticError('controller-response-invalid', 'response-body-decode'); }
  return requests.map((request, index) => {
    try {
      const matches = responses.filter(action => isRecord(action) && action.id === request.id);
      if (matches.length !== 1) throw diagnosticError('controller-response-id-mismatch', 'response-pairing');
      const response = matches[0];
      let rawValue = response.returnValue;
      if (request.transport === 'lwc') {
        // Salesforce wraps LWC ApexActionController results once at the transport
        // layer. The application still returns one JSON String, never an object.
        if (!isRecord(rawValue) || !exactKeys(rawValue, ['returnValue', 'cacheable'])
            || typeof rawValue.cacheable !== 'boolean') {
          throw diagnosticError('controller-response-invalid', 'response-wrapper');
        }
        rawValue = rawValue.returnValue;
      }
      if (response.state !== 'SUCCESS') throw diagnosticError('controller-response-invalid', 'response-state');
      if (typeof rawValue !== 'string') throw diagnosticError('controller-response-invalid', 'response-value-type');
      let result;
      try { result = normalizeResult(request.method, rawValue); }
      catch (_) { throw diagnosticError('controller-response-invalid', 'response-schema'); }
      if ((result.conversationId && request.params.conversationId
            && result.conversationId !== request.params.conversationId)
          || (result.actionId && request.params.actionId
            && result.actionId !== request.params.actionId)) {
        throw diagnosticError('controller-response-invalid', 'response-identity');
      }
      return { request_id: request.id, response_id: response.id,
        response_state: response.state, result, json_string_decoded_once: true };
    } catch (error) {
      // Only our pairing predicates prove an action index. Never read provider
      // error properties, including getters or a forged recordIndex.
      const metadata = DIAGNOSTIC_METADATA.get(error);
      if (metadata) metadata.recordIndex = index;
      throw error;
    }
  });
}

class ApexObserver {
  constructor(page, expectedHost, { trackSplit = false } = {}) {
    this.page = page;
    this.expectedHost = expectedHost;
    // Exploration and setup-only calibration still track every pre-save chat
    // attempt. A full run additionally parses every split RPC for acceptance.
    this.trackSplit = trackSplit;
    this.records = [];
    this.chatRequests = [];
    this.requestActions = new WeakMap();
    this.pending = new Set();
    this.unresolvedRequests = new Set();
    this.responseCompleted = new WeakSet();
    this.failure = null;
    this.firstFailure = null;
    this.step = 'attempt';
    this.sequence = 0;
    this.batch = 0;
  }

  attach() {
    this.page.on('request', request => this.onRequest(request));
    this.page.on('requestfinished', request => this.onLifecycle(request, false));
    this.page.on('requestfailed', request => this.onLifecycle(request, true));
    this.page.on('response', response => {
      const job = this.onResponse(response).catch(error => {
        this.retainFailure(error, 'response-lifecycle');
      });
      this.pending.add(job);
      job.finally(() => this.pending.delete(job));
    });
  }

  retainFailure(error, branch, record, records = []) {
    // The first rejection owns attribution, even if another batch fails while
    // pending response jobs drain. Never replace the sticky acceptance failure.
    this.failure = this.failure || stageError(
      safeErrorCode(error, 'stage', SAFE_STAGES, 'controller'),
      safeErrorCode(error, 'reason', SAFE_REASONS, 'controller-response-invalid'));
    if (this.firstFailure) return;
    this.firstFailure = { step: this.step, branch: DIAGNOSTIC_METADATA.get(error)?.branch || branch };
    if (this.ipcId) this.firstFailure.ipc_id = this.ipcId;
    if (records.length) Object.assign(this.firstFailure, {
      batch: records[0].batch, request_count: records.length,
      ...(records[0].http_status ? { http_status: records[0].http_status } : {}),
    });
    if (record) Object.assign(this.firstFailure, {
      method: record.method, request_sequence: record.sequence, request_id: record.request_id,
      ...(record.http_status ? { http_status: record.http_status } : {}),
    });
  }

  onLifecycle(request, failed) {
    const records = this.requestActions.get(request);
    if (!records) return;
    for (const record of records) record.request_lifecycle = failed ? 'failed' : 'finished';
    if (failed || this.responseCompleted.has(request)) this.unresolvedRequests.delete(request);
    if (failed) {
      // Match only a known cancellation code. Arbitrary network error text may
      // contain URLs or credentials and must never enter a receipt.
      const cancelled = request.failure()?.errorText === 'net::ERR_ABORTED';
      this.retainFailure(stageError('controller', 'controller-response-invalid'),
        cancelled ? 'request-cancelled' : 'request-network-failure',
        records.length === 1 ? records[0] : null, records);
    }
  }

  onRequest(request) {
    let url;
    try { url = new URL(request.url()); } catch (_) { return; }
    if (url.pathname !== '/aura' || request.method().toUpperCase() !== 'POST') return;
    let actions;
    try {
      const body = request.postData() || '';
      this.chatRequests.push(...chatAttempts(body).map(method => ({
        // Playwright populates timing after request dispatch. Read its current
        // browser timestamp at the gate rather than freezing an initial zero.
        method, startedAt: () => typeof request.timing === 'function' ? request.timing().startTime : null,
      })));
      actions = parseAuraRequest(body, CONTROLLER, this.trackSplit);
    }
    catch (error) { this.retainFailure(error, 'request-validation'); return; }
    if (!actions.length) return;
    if (url.protocol !== 'https:' || url.hostname.toLowerCase() !== this.expectedHost || url.port) {
      this.retainFailure(stageError('controller', 'host-mismatch'), 'request-host');
      return;
    }
    const batch = ++this.batch;
    const records = actions.map(action => {
      const { turnToken, ...params } = action.params;
      const record = {
        sequence: ++this.sequence, method: action.method, request_id: action.id,
        params, transport: action.transport, params_valid: true, response_id: null,
        response_state: 'PENDING', result: null, json_string_decoded_once: false,
        batch, request_lifecycle: 'dispatched',
      };
      if (action.method === 'executePendingMessage') record.submittedTokenDigest = digest(turnToken);
      this.records.push(record);
      return record;
    });
    this.requestActions.set(request, records);
    this.unresolvedRequests.add(request);
  }

  async onResponse(response) {
    let url;
    try { url = new URL(response.url()); } catch (_) { return; }
    if (url.pathname !== '/aura') return;
    let request;
    try { request = response.request(); } catch (_) { return; }
    const records = this.requestActions.get(request);
    if (!records) return;
    let branch = 'response-host';
    try {
      if (url.protocol !== 'https:' || url.hostname.toLowerCase() !== this.expectedHost || url.port) {
        throw stageError('controller', 'host-mismatch');
      }
      const status = response.status();
      for (const record of records) {
        record.http_status = status;
        if (record.request_lifecycle === 'dispatched') record.request_lifecycle = 'response';
      }
      branch = 'http-non-2xx';
      if (status < 200 || status >= 300) {
        throw stageError('controller', 'controller-response-invalid');
      }
      branch = 'response-body-read';
      const body = await response.text();
      branch = 'response-body-decode';
      const pairs = pairAuraActions(records.map(record => ({ id: record.request_id,
        method: record.method, params: record.params, transport: record.transport })), body);
      // Native execution/provider HTTP success is not a browser receipt. Only
      // the paired browser response and its validation can supply this proof.
      branch = 'response-server-id';
      const serverId = this.trackSplit ? serverRequestId(await response.allHeaders()) : null;
      for (let index = 0; index < records.length; index += 1) {
        const record = records[index];
        const pair = pairs[index];
        record.response_id = pair.response_id;
        branch = 'response-lifecycle';
        record.json_string_decoded_once = pair.json_string_decoded_once;
        record.result = pair.result;
        if (serverId) record.server_request_id = serverId;
        if (record.method === 'saveSetup' || this.trackSplit && (TURN_METHODS.has(record.method)
            || ['testConnection', 'getConversation', 'confirmAction', 'cancelAction'].includes(record.method))) {
          // Compare browser network times, not asynchronous Node callback order:
          // the page can issue its next request before this observer reads the body.
          if (await response.finished()) throw stageError('controller', 'controller-response-invalid');
          const timing = request.timing();
          if (!Number.isFinite(timing.startTime) || timing.startTime <= 0
              || !Number.isFinite(timing.responseEnd) || timing.responseEnd < 0) {
            throw stageError('controller', 'controller-response-invalid');
          }
          record.request_started_at = timing.startTime;
          record.response_completed_at = timing.startTime + timing.responseEnd;
        }
        record.http_ok = true;
        record.response_state = pair.response_state;
      }
    } catch (error) {
      // Transport, headers, finished() and timing concern the shared request.
      // Only checker-owned pairing predicates identify an action; otherwise
      // identify a singleton or the batch, without inventing a culprit.
      const index = DIAGNOSTIC_METADATA.get(error)?.recordIndex;
      const record = Number.isInteger(index) && index >= 0 && index < records.length ? records[index]
        : (records.length === 1 ? records[0] : null);
      this.retainFailure(error, branch, record, records);
      throw error;
    } finally {
      this.responseCompleted.add(request);
      if (records.every(record => ['finished', 'failed'].includes(record.request_lifecycle))) {
        this.unresolvedRequests.delete(request);
      }
    }
  }

  mark() { return this.records.length; }

  async waitFor(method, predicate = () => true, timeoutMs = 90000, startAt = 0, { dispatched = false } = {}) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() <= deadline) {
      if (this.failure) throw this.failure;
      const match = this.records.slice(startAt).find(record => record.method === method
        && (dispatched || record.response_state !== 'PENDING') && predicate(record));
      if (match) return match;
      await this.page.waitForTimeout(100);
    }
    throw stageError('controller', 'controller-proof-missing');
  }

  async settle() {
    // A known failure must reach bounded failure reporting even if a different
    // response body never resolves. Successful settling still waits for jobs.
    while (this.pending.size && !this.failure) {
      await new Promise(resolve => setTimeout(resolve, 5));
    }
    if (this.failure) throw this.failure;
  }

  assertTurnsAccounted() {
    if (this.records.some(record => TURN_METHODS.has(record.method) && record.ui_correlated !== true)) {
      throw stageError('controller', 'controller-proof-missing');
    }
  }

  assertConnectionAccounted(connection) {
    const records = this.records.filter(record => record.method === 'testConnection');
    if (records.length !== 1 || records[0] !== connection || connection.result?.status !== 'ok') {
      throw stageError('connection', 'connection-failed');
    }
  }

  projection() {
    return this.records.map(record => {
      const result = record.result || {};
      const output = {
        method: record.method, request_sequence: record.sequence,
        request_id: record.request_id, response_id: record.response_id,
        response_state: record.response_state, params_valid: record.params_valid,
        json_string_decoded_once: record.json_string_decoded_once, http_ok: record.http_ok === true,
        ui_correlated: record.ui_correlated === true,
        request_lifecycle: record.request_lifecycle,
        ...(record.http_status ? { http_status: record.http_status } : {}),
      };
      if (result.status) output.result_status = result.status;
      if (result.operation) output.result_operation = result.operation;
      if (result.recordId) output.result_record_id = result.recordId;
      if (result.conversationId) output.result_conversation_id = result.conversationId;
      if (result.actionId) output.action_id = result.actionId;
      if (record.params.actionId) output.request_action_id = record.params.actionId;
      if (record.card_action_id) output.card_action_id = record.card_action_id;
      if (record.server_request_id) output.server_request_id = record.server_request_id;
      if (record.request_started_at) output.request_started_at = record.request_started_at;
      if (record.response_completed_at) output.response_completed_at = record.response_completed_at;
      if (TURN_METHODS.has(record.method)) {
        output.request_conversation_id = record.params.conversationId;
        if (record.params.message) output.message_sha256 = digest(record.params.message);
        if (record.params.clientRequestId) output.client_request_id_sha256 = digest(record.params.clientRequestId);
        if (record.submittedTokenDigest) output.submitted_turn_token_sha256 = record.submittedTokenDigest;
        if (result.pendingTokenDigest) output.issued_turn_token_sha256 = result.pendingTokenDigest;
      }
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

async function uniqueVisible(locator, timeout) {
  try {
    // Strict resolution refuses two visible matches even if just one is enabled.
    await locator.waitFor({ state: 'visible', timeout });
  } catch (_) {
    throw stageError('render', await locator.count() > 1 ? 'ui-state-invalid' : 'ui-control-missing');
  }
  return locator;
}

async function appRoot(page, timeout = 30000) {
  // The declared tab mounts slGrokChatApp. Salesforce's shell has its own Setup.
  return uniqueVisible(page.locator(APP_ROOT), timeout);
}

async function input(page, label) {
  const deadline = Date.now() + 30000;
  const app = await appRoot(page);
  const locator = app.getByLabel(label, { exact: true }).and(page.locator(':visible'));
  return uniqueVisible(locator, Math.max(1, deadline - Date.now()));
}

async function button(page, label) {
  const deadline = Date.now() + 30000;
  const app = await appRoot(page);
  const uniqueApp = page.locator(':root').filter({ hasNot: app.nth(1) }).locator(APP_ROOT);
  const locator = uniqueApp.getByRole('button', { name: label, exact: true }).and(page.locator(':visible'));
  try {
    await uniqueVisible(locator, Math.max(1, deadline - Date.now()));
  } catch (error) {
    if (await app.count() > 1) throw stageError('render', 'ui-state-invalid');
    throw error;
  }
  return locator;
}

async function clickAppControl(page, control) {
  const duplicate = page.locator(APP_ROOT).nth(1).or(control.nth(1)).first();
  // Playwright can keep a resolved element across click retries. Its action
  // prechecks also wait for a triggered locator handler's target to disappear.
  // The handler itself leaves the page untouched.
  let ambiguous = false;
  await page.addLocatorHandler(duplicate, () => { ambiguous = true; });
  try {
    const enabled = control.and(page.getByRole('button', { disabled: false }));
    await enabled.click({ timeout: 30000 });
  } catch (error) {
    if (ambiguous || await duplicate.count()) throw stageError('render', 'ui-state-invalid');
    throw error;
  } finally {
    await page.removeLocatorHandler(duplicate);
  }
}

async function click(page, label) {
  await clickAppControl(page, await enabledButton(page, label));
}

async function enabledButton(page, label) {
  const control = await button(page, label);
  const app = page.locator(APP_ROOT);
  const deadline = Date.now() + 30000;
  try {
    while (Date.now() < deadline) {
      if (await app.count() > 1) throw stageError('render', 'ui-state-invalid');
      if (await control.isEnabled({ timeout: Math.max(1, deadline - Date.now()) })) return control;
      await page.waitForTimeout(100);
    }
  } catch (error) {
    if (await app.count() > 1) throw stageError('render', 'ui-state-invalid');
    if (error.name !== 'TimeoutError') throw error;
  }
  throw stageError('render', 'ui-control-missing');
}

async function testConnection(page, observer, timeoutMs = 120000) {
  const control = await enabledButton(page, 'Test connection');
  const cursor = observer.mark();
  if (observer.records.some(record => record.method === 'testConnection')) {
    throw stageError('connection', 'connection-failed');
  }
  await clickAppControl(page, control);
  const connection = await observer.waitFor('testConnection', () => true, timeoutMs, cursor);
  await observer.settle();
  observer.assertConnectionAccounted(connection);
  connection.ui_correlated = true;
  return connection;
}

function matchTurn(records, before, conversationId, message) {
  const fail = () => { throw stageError('controller', 'controller-proof-missing'); };
  if (!records.length) return null;
  const [start, execute] = records;
  const split = start.method === 'beginMessage';
  if ((!split && (start.method !== 'sendMessage' || records.length !== 1))
      || (split && (records.length > 2 || execute && execute.method !== 'executePendingMessage'))
      || start.params.conversationId !== conversationId || start.params.message !== message
      || execute && execute.params.conversationId !== conversationId) fail();
  if (records.some(record => record.response_state === 'PENDING') || split && !execute) return null;
  if (records.some(record => record.response_state !== 'SUCCESS'
      || record.request_id !== record.response_id || record.result?.conversationId !== conversationId)) fail();

  const user = { role: 'user', content: message };
  const pendingMessages = [...before.messages, user];
  if (before.hasPending || before.conversationId !== conversationId) fail();
  if (split) {
    const pending = start.result;
    if (pending.status !== 'working' || !pending.pendingTokenDigest
        || pending.pendingTokenDigest !== execute.submittedTokenDigest
        || start.batch === execute.batch || start.request_id === execute.request_id
        || !Number.isFinite(start.response_completed_at) || !Number.isFinite(execute.request_started_at)
        || start.response_completed_at > execute.request_started_at
        || !isDeepStrictEqual(pending.messages, pendingMessages)
        || !isDeepStrictEqual(pending.actions, before.actions)
        || !isDeepStrictEqual(pending.toolCalls, before.toolCalls)
        || Object.hasOwn(pending, 'requestId') && pending.requestId !== start.params.clientRequestId
        || Object.hasOwn(pending, 'message') && pending.message !== message
        || Object.hasOwn(pending, 'messageHash') && pending.messageHash !== digest(message)) fail();
  }

  const call = execute || start;
  const completed = call.result;
  const replies = completed.messages.slice(pendingMessages.length);
  const priorActions = new Map(before.actions.map(action => [action.actionId, action]));
  const finalActions = new Map(completed.actions.map(action => [action.actionId, action]));
  if (completed.status !== 'ready' || completed.hasPending
      || !isDeepStrictEqual(completed.messages.slice(0, pendingMessages.length), pendingMessages)
      || replies.at(-1)?.role !== 'assistant'
      || replies.some(reply => !['tool', 'assistant'].includes(reply.role) || !nonemptyString(reply.content))
      || !isDeepStrictEqual(completed.toolCalls.slice(0, before.toolCalls.length), before.toolCalls)
      || priorActions.size !== before.actions.length
      || finalActions.size !== completed.actions.length
      || [...priorActions].some(([id, action]) => !isDeepStrictEqual(finalActions.get(id), action))) fail();
  return { call, begin: split ? start : null, conversation: completed,
    added: { messages: [user, ...replies], toolCalls: completed.toolCalls.slice(before.toolCalls.length),
      actions: completed.actions.filter(action => !priorActions.has(action.actionId)) } };
}

function turnBaseline(records, conversationId) {
  const sameConversation = record => record.response_state === 'SUCCESS'
    && record.result?.conversationId === conversationId;
  const latest = records.findLast(record => sameConversation(record)
    && (record.method === 'getConversation' || TURN_METHODS.has(record.method)));
  const anchor = records.findLast(record => sameConversation(record)
    && TURN_METHODS.has(record.method) && record.result.status === 'ready' && record.ui_correlated) || latest;
  if (!latest || latest.result.hasPending
      || !isDeepStrictEqual(latest.result.messages.slice(0, anchor.result.messages.length), anchor.result.messages)
      || !isDeepStrictEqual(latest.result.toolCalls, anchor.result.toolCalls)) {
    return null;
  }
  const appended = latest.result.messages.slice(anchor.result.messages.length);
  let actions = new Map(anchor.result.actions.map(action => [action.actionId, action]));
  if (actions.size !== anchor.result.actions.length) return null;
  let transitionSinceRead = null;
  for (const record of records.slice(records.indexOf(anchor) + 1)) {
    if (appended.length && ['confirmAction', 'cancelAction'].includes(record.method)
        && actions.has(record.params.actionId) && record.ui_correlated !== true) return null;
    if (record === latest) {
      const snapshot = record.result.actions;
      if (actions.size !== snapshot.length || new Set(snapshot.map(action => action.actionId)).size !== actions.size
          || snapshot.some(action => !isDeepStrictEqual(actions.get(action.actionId), action))) return null;
      // A fresh authoritative read can establish the bookkeeping prefix after
      // a checked action. Its text carries no confirmation authority of its own.
      if (appended.length && (record.method !== 'getConversation' || !transitionSinceRead
          || !Number.isFinite(transitionSinceRead.response_completed_at) || !Number.isFinite(record.request_started_at)
          || transitionSinceRead.response_completed_at > record.request_started_at
          || appended.some(entry => !['tool', 'developer'].includes(entry.role)))) return null;
      actions = new Map(snapshot.map(action => [action.actionId, action]));
      transitionSinceRead = null;
    }
    // Only the first fully checked action delivery can advance the baseline.
    // A retry's rejection never changes the stored result of a confirmation.
    const transition = record.validatedTransition;
    if (transition?.conversationId !== conversationId) continue;
    const { proposal } = transition;
    if (!isDeepStrictEqual(actions.get(proposal.actionId), proposal)) return null;
    const { status, recordId = proposal.recordId } = record.result;
    actions.set(proposal.actionId, { ...proposal, status, recordId });
    transitionSinceRead = record;
  }
  return { history: { ...latest.result, actions: [...actions.values()] }, unreadTransition: transitionSinceRead };
}

async function hasVisible(locator) {
  const elements = await locator.elementHandles();
  try {
    for (const element of elements) {
      if (await element.isVisible()) return true;
    }
    return false;
  } finally {
    await Promise.all(elements.map(element => element.dispose()));
  }
}

// Playwright's text locator can miss direct text nodes in an open shadow root.
// Read rendered fragments under this exact element, following slots and hosts.
// A text range supplies geometry even when no element wraps the text.
function renderedTextTree(roots, { boundary, omit = [], omitSelector } = {}) {
  const rootSet = new Set(Array.isArray(roots) ? roots : [roots]);
  const isBoundary = element => rootSet.has(element) || boundary && element.matches(boundary);
  const excluded = 'script, style, template, noscript, [hidden], [aria-hidden="true"]';
  const visible = (element, style) => !element.matches(excluded) && style.display !== 'none'
    && style.visibility === 'visible' && style.opacity !== '0' && style.contentVisibility !== 'hidden'
    && style.clip !== 'rect(0px, 0px, 0px, 0px)' && style.clipPath !== 'inset(50%)';
  const parent = node => node.assignedSlot || node.parentElement || node.getRootNode().host;
  const normalize = text => text.replace(/[\u200b\u00ad]/g, '').replace(/\s+/g, ' ').trim();
  const scrollable = /^(auto|scroll|overlay)$/;
  let segmenter;
  const range = document.createRange();
  const clipBoxes = new WeakMap();
  function insetClip(element, value) {
    // The default reference box for HTML is the border box. Support plain
    // rectangular insets where the border box can be mapped without transforms.
    const match = /^(?:border-box )?inset\(([^()]*)\)(?: border-box)?$/.exec(value);
    if (!match) return null;
    const offsets = match[1].trim().split(/\s+/);
    if (offsets.length > 4 || offsets.some(offset => !/^(?:0|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:px|%))$/.test(offset))) {
      return null;
    }
    for (let ancestor = element; ancestor; ancestor = parent(ancestor)) {
      if (!(ancestor instanceof HTMLElement)) return null;
      const style = getComputedStyle(ancestor);
      if ([style.transform, style.rotate, style.scale, style.perspective, style.offsetPath]
        .some(property => property !== 'none')) return null;
    }
    const rects = element.getClientRects();
    const zoom = element.currentCSSZoom;
    if (rects.length !== 1 || !Number.isFinite(zoom)) return null;
    const [top, right = top, bottom = top, left = right] = offsets;
    const rect = rects[0];
    const pixels = (offset, size) => parseFloat(offset) * (offset.endsWith('%') ? size / 100 : zoom);
    return {
      left: rect.left + pixels(left, rect.width), right: rect.right - pixels(right, rect.width),
      top: rect.top + pixels(top, rect.height), bottom: rect.bottom - pixels(bottom, rect.height),
      clipX: true, clipY: true, shiftLeft: 0, shiftRight: 0, shiftUp: 0, shiftDown: 0, tolerance: 0,
    };
  }
  function clipsFor(element) {
    if (clipBoxes.has(element)) return clipBoxes.get(element);
    const { overflowX, overflowY, overflowClipMargin, display, direction, position, clip, clipPath } = getComputedStyle(element);
    const boxes = [];
    if (!/^(inline|contents)$/.test(display) && (overflowX !== 'visible' || overflowY !== 'visible')) {
      const viewport = element === document.scrollingElement;
      const rect = element.getBoundingClientRect();
      const scaleX = element.offsetWidth ? rect.width / element.offsetWidth : 1;
      const scaleY = element.offsetHeight ? rect.height / element.offsetHeight : 1;
      const left = viewport ? 0 : rect.left + element.clientLeft * scaleX;
      const top = viewport ? 0 : rect.top + element.clientTop * scaleY;
      const scrollWidth = scrollable.test(overflowX) ? (element.scrollWidth - element.clientWidth) : 0;
      const scrollHeight = scrollable.test(overflowY) ? (element.scrollHeight - element.clientHeight) : 0;
      const clipX = overflowX !== 'visible' && !(viewport && scrollable.test(overflowX));
      const clipY = overflowY !== 'visible' && !(viewport && scrollable.test(overflowY));
      // A rounded zero client size can still expose subpixel text. Require a
      // zero border box extent and a local clip that cannot extend beyond it.
      const local = element !== document.documentElement && element !== document.body;
      const empty = local && (clipX && element.clientWidth === 0 && rect.width === 0
        && (overflowX !== 'clip' || overflowClipMargin === '0px')
        || clipY && element.clientHeight === 0 && rect.height === 0
        && (overflowY !== 'clip' || overflowClipMargin === '0px'));
      boxes.push({
        left, top, right: left + element.clientWidth * scaleX, bottom: top + element.clientHeight * scaleY,
        clipX, clipY, empty,
        shiftLeft: scrollWidth > 0 ? (element.scrollLeft - (direction === 'rtl' ? 0 : scrollWidth)) * scaleX : 0,
        shiftRight: scrollWidth > 0 ? (element.scrollLeft + (direction === 'rtl' ? scrollWidth : 0)) * scaleX : 0,
        shiftUp: scrollHeight > 0 ? (element.scrollTop - scrollHeight) * scaleY : 0,
        shiftDown: scrollHeight > 0 ? element.scrollTop * scaleY : 0,
        tolerance: 0.5, // Client dimensions are rounded to integer CSS pixels.
      });
    }
    // Scroll inside this element first, then apply its fixed clip path.
    const path = display !== 'contents' && clipPath !== 'none' ? insetClip(element, clipPath) : undefined;
    if (path) boxes.push(path);
    // A positioned legacy clip or an unsupported clip path leaves the text
    // range's visible geometry unknown.
    const outOfFlow = position === 'absolute' || position === 'fixed';
    const result = path === null || (clip !== 'auto' && outOfFlow) ? null : { boxes, outOfFlow };
    clipBoxes.set(element, result);
    return result;
  }
  function reachableRect(rect, boxes) {
    let leftmost = rect.left;
    let rightmost = rect.left;
    let uppermost = rect.top;
    let lowermost = rect.top;
    for (const box of boxes) {
      // Track where the whole fragment can fit, accounting for each scroll
      // range. Non-scrollable clips never reveal more content.
      if (box.clipX) {
        leftmost = Math.max(leftmost + box.shiftLeft, box.left);
        rightmost = Math.min(rightmost + box.shiftRight, box.right - rect.width);
      }
      if (box.clipY) {
        uppermost = Math.max(uppermost + box.shiftUp, box.top);
        lowermost = Math.min(lowermost + box.shiftDown, box.bottom - rect.height);
      }
      if (leftmost - rightmost > box.tolerance || uppermost - lowermost > box.tolerance) return false;
    }
    return true;
  }
  function possiblyVisibleRect(rect, boxes) {
    let { left, right, top, bottom } = rect;
    for (const box of boxes) {
      // Track any surviving portion through nested clips and available scroll.
      // Allow for rounded overflow dimensions when proving total exclusion.
      if (box.clipX) {
        left = Math.max(left + box.shiftLeft, box.left - box.tolerance);
        right = Math.min(right + box.shiftRight, box.right + box.tolerance);
      }
      if (box.clipY) {
        top = Math.max(top + box.shiftUp, box.top - box.tolerance);
        bottom = Math.min(bottom + box.shiftDown, box.bottom + box.tolerance);
      }
      if (right <= left || bottom <= top) return false;
    }
    return true;
  }
  function textReachability(node, element) {
    const boxes = [];
    let outOfFlow = false;
    let emptyClipReachability;
    for (let ancestor = element; ancestor; ancestor = parent(ancestor)) {
      const clips = clipsFor(ancestor);
      if (!clips) return 'incomplete';
      // A positioned descendant may have a containing block outside an overflow
      // ancestor. Keep uncertain text incomplete so it cannot disappear from an exact match.
      if (!emptyClipReachability && clips.boxes.some(box => box.empty)) {
        emptyClipReachability = outOfFlow ? 'incomplete' : 'hidden';
      }
      boxes.push(...clips.boxes);
      outOfFlow ||= clips.outOfFlow;
    }
    if (emptyClipReachability) return emptyClipReachability;
    function rangeReachability() {
      const rects = [...range.getClientRects()].filter(rect => rect.width > 0 && rect.height > 0);
      if (!rects.length) return 'incomplete';
      if (rects.every(rect => reachableRect(rect, boxes))) return 'complete';
      return rects.some(rect => possiblyVisibleRect(rect, boxes)) ? 'incomplete' : 'hidden';
    }
    range.selectNodeContents(node);
    const whole = rangeReachability();
    if (whole !== 'incomplete') return whole;
    // A line can be partially clipped, or scrollable a few glyphs at a time.
    // Only those text nodes need the finer-grained geometry checks.
    segmenter ??= new Intl.Segmenter(undefined, { granularity: 'grapheme' });
    let reachability;
    for (const { segment, index } of segmenter.segment(node.data)) {
      if (!normalize(segment)) continue;
      range.setStart(node, index);
      range.setEnd(node, index + segment.length);
      const part = rangeReachability();
      if (part === 'incomplete' || reachability && reachability !== part) return 'incomplete';
      reachability = part;
    }
    return reachability ?? 'incomplete';
  }
  function visit(element, root) {
    const style = getComputedStyle(element);
    if (!visible(element, style) || omit.includes(element) || omitSelector && element.matches(omitSelector)
        || element !== root && isBoundary(element)) return null;
    const children = [];
    const fragments = [];
    let actionMarkup = element.hasAttribute('data-action-id');
    let ownTextIncomplete = false;
    const slots = element.localName === 'slot' ? element.assignedNodes({ flatten: true }) : [];
    const nodes = slots.length ? slots : (element.shadowRoot || element).childNodes;
    const summary = element.matches('details:not([open])')
      ? Array.from(element.children).find(child => child.localName === 'summary') : null;
    for (const node of summary ? [summary] : nodes) {
      if (node.nodeType === Node.TEXT_NODE) {
        if (normalize(node.data)) {
          const reachability = textReachability(node, element);
          ownTextIncomplete ||= reachability === 'incomplete';
          if (reachability !== 'complete') continue;
        }
        fragments.push(node.data);
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        const child = visit(node, root);
        if (!child) {
          if (isBoundary(node)) actionMarkup = true;
          continue;
        }
        actionMarkup ||= child.tree.actionMarkup;
        children.push(child.tree);
        fragments.push(child.tree.breaksLine ? '\n' + child.raw + '\n' : child.raw);
      }
    }
    const raw = fragments.join('');
    const singleLine = !children.some(child => child.breaksLine);
    const textIncomplete = ownTextIncomplete || children.some(child => child.textIncomplete);
    return {
      raw, tree: { text: normalize(raw), firstLine: raw.split('\n').map(normalize).find(Boolean) ?? '',
        singleLine, breaksLine: !singleLine || element.localName === 'br' || !/^(inline|contents)/.test(style.display),
        label: element.getAttribute('aria-label'), children, actionMarkup, ownTextIncomplete, textIncomplete,
        group: element.matches('fieldset, [role="group"]'),
        heading: element.matches('h1, h2, h3, h4, h5, h6, [role="heading"]'),
        button: element.matches('button, [role="button"]') },
    };
  }
  function snapshot(root) {
    for (let ancestor = root; ancestor; ancestor = parent(ancestor)) {
      if (!visible(ancestor, getComputedStyle(ancestor))) return null;
    }
    return visit(root, root)?.tree ?? null;
  }
  return Array.isArray(roots) ? roots.map(snapshot) : snapshot(roots);
}

function cardText(value) {
  return value.replace(/[\u200b\u00ad]/g, '').replace(/\s+/g, ' ').trim();
}

function hasCardText(tree, predicate) {
  return !!tree && (predicate(tree) || tree.children.some(child => hasCardText(child, predicate)));
}

function nearestCard(element, { selector, expected }) {
  for (let node = element; node; node = node.assignedSlot || node.parentElement || node.getRootNode().host) {
    if (node.matches(selector)) return expected === undefined ? node : node === expected;
  }
  return expected === undefined ? null : false;
}

async function renderedHistory(page, messages) {
  const conversation = page.getByRole('region', { name: 'Conversation', exact: true });
  if (await conversation.count() !== 1 || !await conversation.isVisible()) return false;
  const roles = /^(user|assistant)$/i;
  const entries = name => conversation.getByRole('article', { name })
    .or(conversation.getByRole('group', { name }))
    .or(conversation.getByRole('listitem', { name }));
  const headed = entries()
    .filter({ has: page.getByRole('heading', { name: roles }) });
  const cards = await entries(roles).or(headed).all();
  const expected = messages.filter(message => ['user', 'assistant'].includes(message.role));
  if (cards.length !== expected.length) return false;
  for (const [index, locator] of cards.entries()) {
    const { role, content } = expected[index];
    const name = new RegExp(`^${role}$`, 'i');
    const [card] = await locator.elementHandles();
    if (!card) return false;
    const headings = await locator.getByRole('heading', { name }).elementHandles();
    try {
      const labelled = await locator.and(entries(name)).count();
      let roleHeading;
      for (const heading of headings) {
        if (!await heading.evaluate(nearestCard, { selector: CARD, expected: card })) continue;
        const tree = await heading.evaluate(renderedTextTree);
        if (tree?.text && !tree.textIncomplete) {
          roleHeading = heading;
          break;
        }
      }
      if (!await card.isVisible() || !(labelled || roleHeading)) return false;
      const options = { boundary: CARD, omitSelector: MESSAGE_METADATA };
      const matches = async omit => {
        const tree = await card.evaluate(renderedTextTree, { ...options, omit });
        return tree && !tree.textIncomplete && tree.text === cardText(content);
      };
      // A role-labelled entry can use a body heading that happens to have
      // the same name. Only the first owned role heading can be redundant.
      if (!(labelled && await matches([])) && !(roleHeading && await matches([roleHeading]))) return false;
    } finally {
      await Promise.all([card, ...headings].map(handle => handle.dispose()));
    }
  }
  return true;
}

async function writeMessage(page, observer, conversationId, message, timeoutMs = 150000) {
  await expectConversation(observer, conversationId);
  await observer.settle();
  observer.assertTurnsAccounted();
  const baseline = turnBaseline(observer.records, conversationId);
  if (baseline?.unreadTransition) {
    const reload = page.getByRole('button', { name: 'Reload history', exact: true });
    let cursor = observer.records.indexOf(baseline.unreadTransition) + 1;
    const forConversation = record => record.params.conversationId === conversationId;
    // Let an app-initiated read finish before requesting another one.
    if (!observer.records.slice(cursor).some(record => record.method === 'getConversation' && forConversation(record))) {
      cursor = observer.mark();
      if (await reload.count() === 1 && await reload.isVisible() && await reload.isEnabled()) {
        await reload.click({ timeout: Math.min(30000, timeoutMs) });
      } else {
        await page.reload({ waitUntil: 'domcontentloaded', timeout: Math.min(60000, timeoutMs) });
        await region(page, 'Conversation');
      }
    }
    await expectConversation(observer, conversationId, cursor, undefined, Math.min(45000, timeoutMs));
    await observer.settle();
  }
  await (await input(page, 'Message')).fill(message);
  const send = await enabledButton(page, 'Send');
  observer.assertTurnsAccounted();
  const checked = turnBaseline(observer.records, conversationId);
  if (!checked || checked.unreadTransition || !await renderedHistory(page, checked.history.messages)) {
    throw stageError('render', 'ui-state-invalid');
  }
  const before = checked.history;
  const cursor = observer.mark();
  const turnRecords = () => observer.records.slice(cursor).filter(record => TURN_METHODS.has(record.method));
  await clickAppControl(page, send);
  const deadline = Date.now() + timeoutMs;
  let chain;
  while (Date.now() <= deadline) {
    if (observer.failure) throw observer.failure;
    chain = matchTurn(turnRecords(), before, conversationId, message);
    if (chain && await renderedHistory(page, chain.conversation.messages)
        && await hasVisible(page.getByRole('region', { name: 'Chat status', exact: true })
          .getByText(/^ready\b/i))) break;
    chain = null;
    await page.waitForTimeout(100);
  }
  if (!chain) throw stageError('controller', 'controller-proof-missing');
  await observer.settle();
  const { call, begin } = matchTurn(turnRecords(), before, conversationId, message);
  if (begin && observer.records.slice(0, cursor).some(record => record.method === 'beginMessage'
      && (record.params.clientRequestId === begin.params.clientRequestId
        || record.result?.pendingTokenDigest === begin.result.pendingTokenDigest))) {
    throw stageError('controller', 'controller-proof-missing');
  }
  call.ui_correlated = true;
  if (begin) begin.ui_correlated = true;
  return { ...chain, proof: {
    conversation_id: conversationId, execution_request_sequence: call.sequence,
    begin_request_sequence: begin ? begin.sequence : null,
    before_message_count: before.messages.length, final_message_count: chain.conversation.messages.length,
    before_history_sha256: digest(JSON.stringify(before.messages)),
    final_history_sha256: digest(JSON.stringify(chain.conversation.messages)),
    rendered_history_matched: true,
  } };
}

function findAction(conversation, operation, predicate) {
  const matches = conversation.actions.filter(action => action.operation === operation
    && action.status === 'proposed' && predicate(action));
  return matches.length === 1 ? matches[0] : null;
}

function labelledValues(tree, labels) {
  if (!tree) return [];
  const inline = new RegExp(`^(?:${labels})\\s*:\\s*(.+)$`, 'i');
  const label = new RegExp(`^(?:${labels})\\s*:?$`, 'i');
  function visit(node) {
    const found = node.children.flatMap(visit);
    const line = node.singleLine && inline.exec(node.text);
    if (line) return found.length ? found : [line[1]];
    if (!found.length && node.label && label.test(cardText(node.label)) && node.text && !label.test(node.text)) {
      return [node.text];
    }
    for (const [index, child] of node.children.entries()) {
      const next = node.children[index + 1];
      if (label.test(child.text) && next?.text && !label.test(next.text)) found.push(next.text);
    }
    return found;
  }
  return visit(tree);
}

const OPERATION_HEADING = /^(?:operation:\s*)?(create|update)\b/i;

function readProposal(tree) {
  function readFieldGroups(node, root = false) {
    // An accessible group may be a nested action or just a field layout.
    // Only the latter can contribute values to this proposal.
    const group = node.group && !root;
    if (group && (node.actionMarkup || hasCardText(node, child =>
      child.heading && OPERATION_HEADING.test(child.text)
      || child.button && /^(confirm|cancel)$/i.test(child.label || child.text)))) return null;
    const parts = node.children.map(child => readFieldGroups(child)).filter(Boolean);
    const textIncomplete = node.ownTextIncomplete || parts.some(part => part.textIncomplete);
    const fields = parts.flatMap(part => part.fields);
    const children = parts.map(part => part.header).filter(Boolean);
    const intact = children.length === node.children.length && children.every((child, i) => child === node.children[i]);
    const remainder = intact ? node : { ...node, text: '', singleLine: false, children };
    const labels = new Set([node.label, ...children.map(child => child.text)].filter(label => FIELDS.has(label)));
    if (labels.size === 1) {
      const old = labelledValues(remainder, 'Old(?: value)?');
      const next = labelledValues(remainder, 'New(?: value)?');
      if (old.length || next.length) {
        fields.push({ name: [...labels][0], old, next });
        return { header: null, fields, textIncomplete };
      }
    }
    // Evaluate target and operation positions after extracting fields. An
    // old or new text value can itself begin with "Target:" or "Operation:".
    const ownPosition = node.singleLine && /^(Operation|Target|Record ID|Name)$/i.test(node.label || '');
    if (group && !ownPosition && labelledValues(remainder, 'Operation|Target|Record ID|Name').length) return null;
    return { header: remainder, fields, textIncomplete };
  }
  const { header, fields, textIncomplete } = readFieldGroups(tree, true);
  const operations = labelledValues(header, 'Operation');
  const readHeadings = node => {
    if (node.heading && OPERATION_HEADING.test(node.text)) operations.push(node.text);
    node.children.forEach(readHeadings);
  };
  if (header) readHeadings(header);
  return { header, fields, operations, textIncomplete, targets: labelledValues(header, 'Target'),
    ids: labelledValues(header, 'Record ID'), names: labelledValues(header, 'Name') };
}

function proposalTarget(view, { name: expectedName, nameUnique }, action) {
  const { targets, ids, names, fields } = view;
  const name = cardText(expectedName);
  const visibleNames = [...names];
  const explicitIds = [...ids];
  for (const value of targets) {
    // A target can show the record ID alone or next to its name.
    const namedId = /^(.*?)\s*\(([A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?)\)$/.exec(value);
    if (namedId) {
      if (namedId[1]) visibleNames.push(cardText(namedId[1]));
      explicitIds.push(namedId[2]);
    } else if (SF_ID_RE.test(value)) {
      explicitIds.push(value);
    } else {
      visibleNames.push(value);
    }
  }
  if (action.operation === 'create') {
    const nameField = fields.find(field => field.name === 'Name');
    return !explicitIds.length && visibleNames.every(value => value === name || /^new (?:work )?item$/i.test(value))
      && nameField?.next.includes(name) ? 1 : 0;
  }
  const nameMatches = visibleNames.length > 0 && visibleNames.every(value => value === name);
  if (explicitIds.length) {
    return explicitIds.every(id => id === action.recordId) && (!visibleNames.length || nameMatches) ? 2 : 0;
  }
  return nameUnique && nameMatches ? 1 : 0;
}

function proposalFieldsMatch(view, action) {
  if (view.textIncomplete || !view.operations.length
      || view.operations.some(value => OPERATION_HEADING.exec(value)?.[1].toLowerCase() !== action.operation)
      || view.fields.length !== Object.keys(action.newValues).length
      || labelledValues(view.header, 'Old(?: value)?|New(?: value)?').length) return false;
  const displayed = value => value === null ? '(empty)' : value === '' ? '(empty text)' : cardText(value);
  return Object.entries(action.newValues).every(([name, next]) => {
    const fields = view.fields.filter(field => field.name === name);
    if (fields.length !== 1) return false;
    const [field] = fields;
    return isDeepStrictEqual(field.next, [displayed(next)]) && (Object.hasOwn(action.oldValues, name)
      ? isDeepStrictEqual(field.old, [displayed(action.oldValues[name])])
      : field.old.length === 0 || field.old.length === 1 && /^(?:\(new item\)|\(empty\)|n\/a|—)$/i.test(field.old[0]));
  });
}

async function matchingProposal(proposals, target, action) {
  const trees = await proposals.evaluateAll(renderedTextTree, { boundary: PROPOSAL_TEXT_BOUNDARY });
  const matches = [];
  for (const [index, tree] of trees.entries()) {
    if (!tree) continue;
    const view = readProposal(tree);
    const priority = proposalTarget(view, target, action);
    if (priority) matches.push({ index, view, priority });
  }
  const preferred = matches.some(match => match.priority === 2)
    ? matches.filter(match => match.priority === 2) : matches;
  if (preferred.length > 1) throw stageError('render', 'proposal-missing');
  return preferred[0];
}

async function stillMatchesProposal(proposals, proposed, target, action) {
  const match = await matchingProposal(proposals, target, action);
  if (!match || !proposalFieldsMatch(match.view, action)) return false;
  const [current] = await proposals.nth(match.index).elementHandles();
  try {
    return !!current && await current.evaluate((element, original) => element === original, proposed);
  } finally {
    await current?.dispose();
  }
}

const CONTROL_BOUNDARY = `${CARD}, ${PROPOSAL_TEXT_BOUNDARY}, `
  + 'section:not([role])[aria-label="Proposed change"], [role="region"][aria-label="Proposed change"]';

function proposalRegions(page) {
  return page.getByRole('region', { name: 'Conversation', exact: true })
    .getByRole('region', { name: 'Proposed change', exact: true });
}

async function withProposalBoundaries(proposals, callback) {
  const proposalElements = await proposals.elementHandles();
  try {
    return await callback({ proposalElements, boundary: CONTROL_BOUNDARY, cardSelector: CARD });
  } finally {
    await Promise.all(proposalElements.map(element => element.dispose()));
  }
}

function watchProposalControl(element, { proposed, card, actionId, proposalElements, boundary, cardSelector, guard = false }) {
  function ownership() {
    const path = [];
    if (!element.isConnected) return { state: 'detached', path };
    let inProposal = false;
    let nested = false;
    let nestedCard = false;
    let wrongId = false;
    let matchingId = false;
    for (let node = element; node; node = node.assignedSlot || node.parentElement || node.getRootNode().host) {
      path.push(node);
      const marker = node.getAttribute('data-action-id');
      if (marker !== null) {
        matchingId ||= marker === actionId;
        wrongId ||= marker !== actionId;
      }
      if (node === proposed) inProposal = true;
      if (node === card) {
        if (!inProposal && !nestedCard) return { state: 'outside', path };
        if (!inProposal || nested) return { state: matchingId && !wrongId ? 'relocated' : 'foreign', path };
        return { state: wrongId ? 'rebound' : 'owned', path };
      }
      if (node !== proposed) {
        nested ||= proposalElements.includes(node) || node.matches(boundary);
        nestedCard ||= node.matches(cardSelector);
      }
    }
    return { state: matchingId && !wrongId ? 'relocated' : 'foreign', path };
  }
  const { state: initial, path } = ownership();
  if (!guard) return initial;
  let refused = false;
  function checkClick(event) {
    const current = ownership();
    if (event.composedPath().includes(element) && current.state === 'owned'
        && current.path.length === path.length && current.path.every((node, i) => node === path[i])) return;
    refused = true;
    event.preventDefault();
    event.stopImmediatePropagation();
  }
  // Playwright can wait for actionability between the ownership check and
  // dispatch. Recheck in capture before the page can handle the input.
  const events = ['pointerdown', 'pointerup', 'mousedown', 'mouseup', 'click'];
  if (initial === 'owned') for (const event of events) window.addEventListener(event, checkClick, true);
  return { initial, finish() {
    for (const event of events) window.removeEventListener(event, checkClick, true);
    return refused;
  } };
}

async function proposalRegion(page, target, action, timeoutMs = 15000) {
  const proposals = proposalRegions(page);
  const deadline = Date.now() + timeoutMs;
  let reason = 'proposal-missing';
  do {
    const match = await matchingProposal(proposals, target, action);
    if (match) {
      reason = 'proposal-mismatch';
      if (proposalFieldsMatch(match.view, action)) {
        const proposal = proposals.nth(match.index);
        const [proposed] = await proposal.elementHandles();
        if (!proposed) continue;
        const cardHandle = await proposed.evaluateHandle(nearestCard, { selector: CARD });
        const card = cardHandle.asElement();
        const controls = {};
        let pinned = false;
        try {
          if (!card) throw stageError('render', 'proposal-mismatch');
          const ready = await withProposalBoundaries(proposals, async boundaries => {
            for (const name of ['Confirm', 'Cancel']) {
              const buttons = await proposal.getByRole('button', { name, exact: true }).elementHandles();
              try {
                for (const button of buttons) {
                  const state = await button.evaluate(watchProposalControl, {
                    ...boundaries, proposed, card, actionId: action.actionId,
                  });
                  if (state === 'rebound' || state === 'owned' && controls[name]) {
                    throw stageError('render', 'proposal-mismatch');
                  }
                  if (state === 'owned') controls[name] = button;
                }
                if (!controls[name] || !await controls[name].isVisible()
                    || !await controls[name].evaluate(renderedTextTree)) return false;
              } finally {
                await Promise.all(buttons.filter(button => button !== controls[name]).map(button => button.dispose()));
              }
            }
            return true;
          });
          if (ready && await stillMatchesProposal(proposals, proposed, target, action)) {
            pinned = true;
            return { card, proposed, controls };
          }
        } finally {
          if (!pinned) {
            await Promise.all([cardHandle, proposed, ...Object.values(controls).filter(Boolean)].map(handle => handle.dispose()));
          }
        }
      }
    }
    if (Date.now() >= deadline) break;
    await page.waitForTimeout(100);
  } while (Date.now() <= deadline);
  throw stageError('render', reason);
}

async function cardStatus(page, card, actionId) {
  if (!await card.evaluate((element, id) => element.isConnected
      && (!element.hasAttribute('data-action-id') || element.getAttribute('data-action-id') === id), actionId)) {
    throw stageError('render', 'proposal-mismatch');
  }
  const statuses = await page.getByRole('region', { name: 'Action status', exact: true }).elementHandles();
  try {
    let label = null;
    for (const status of statuses) {
      if (!await status.evaluate(nearestCard, { selector: CARD, expected: card }) || !await status.isVisible()) continue;
      const tree = await status.evaluate(renderedTextTree, { boundary: CARD });
      if (!tree?.firstLine) continue;
      if (label !== null) throw stageError('render', 'proposal-mismatch');
      label = tree.firstLine.toLowerCase().replace(/^(?:action )?status:\s*/, '').trim();
    }
    return label;
  } finally {
    await Promise.all(statuses.map(status => status.dispose()));
  }
}

async function releaseProposal({ card, proposed, controls }) {
  await Promise.all([card, proposed, ...Object.values(controls)].map(handle => handle.dispose()));
}

async function clickProposalControl(control, { card, proposed }, actionId, boundaries, retry = false) {
  const args = { ...boundaries, card, proposed, actionId, guard: true };
  const guard = await control.evaluateHandle(watchProposalControl, args);
  try {
    const initial = await guard.evaluate(value => value.initial);
    if (initial === 'detached' && retry) return false;
    if (initial !== 'owned') throw stageError('render', 'proposal-mismatch');
    try {
      await control.click({ timeout: retry ? 1500 : 30000 });
      return true;
    } catch (error) {
      const ownership = await control.evaluate(watchProposalControl, { ...args, guard: false });
      if (!['detached', 'owned'].includes(ownership)) throw stageError('render', 'proposal-mismatch');
      if (!retry) throw error;
      if (await control.isVisible().catch(() => false) && await control.isEnabled().catch(() => false)) {
        throw stageError('render', 'ui-control-missing');
      }
      return false;
    }
  } finally {
    try {
      if (await guard.evaluate(value => value.finish())) throw stageError('render', 'proposal-mismatch');
    } finally {
      await guard.dispose();
    }
  }
}

async function checkRetry(page, proposals, pin, target, action, attempt) {
  const { proposed, card, controls: { Confirm: original } } = pin;
  return withProposalBoundaries(proposals, async boundaries => {
    const args = { ...boundaries, proposed, card, actionId: action.actionId };
    const initial = await original.evaluate(watchProposalControl, args);
    if (!['detached', 'owned'].includes(initial)) throw stageError('render', 'proposal-mismatch');
    const buttons = await page.getByRole('button', { name: 'Confirm', exact: true }).elementHandles();
    try {
      let enabled = false;
      for (const button of buttons) {
        const state = await button.evaluate(watchProposalControl, args);
        if (state === 'detached' || state === 'foreign' || !await button.isVisible()
            || !await button.isEnabled() || !await button.evaluate(renderedTextTree)) continue;
        if (state !== 'owned' || enabled || !await button.evaluate((element, pin) => element === pin, original)) {
          // An enabled replacement is a live retry path, even if the original
          // detached. Withhold credit instead of clicking an unpinned control.
          throw stageError('render', 'proposal-mismatch');
        }
        enabled = true;
      }
      if (!enabled) return false;
      if (!attempt || !await stillMatchesProposal(proposals, proposed, target, action)) {
        throw stageError('render', 'proposal-mismatch');
      }
      return await clickProposalControl(original, pin, action.actionId, boundaries, true);
    } finally {
      await Promise.all(buttons.map(button => button.dispose()));
    }
  });
}

async function performAction(page, observer, target, action, status, {
  conversationId, retry = false, timeoutMs = 90000, renderTimeoutMs = 30000, proposalTimeoutMs = 15000,
} = {}) {
  const { actionId } = action;
  const proposals = proposalRegions(page);
  const pin = await proposalRegion(page, target, action, proposalTimeoutMs);
  const { card, controls } = pin;
  try {
    const initial = await cardStatus(page, card, actionId);
    if (initial !== null && initial !== 'proposed') throw stageError('render', 'proposal-mismatch');
    const method = status === 'cancelled' ? 'cancelAction' : 'confirmAction';
    const control = controls[status === 'cancelled' ? 'Cancel' : 'Confirm'];
    const cursor = observer.mark();
    const actionCalls = () => observer.records.slice(cursor)
      .filter(record => ['confirmAction', 'cancelAction'].includes(record.method));
    const awaitResponse = call => observer.waitFor(method, record => record === call, timeoutMs, cursor);
    const fail = () => { throw stageError('controller', 'controller-proof-missing'); };

    await withProposalBoundaries(proposals, boundaries => clickProposalControl(control, pin, actionId, boundaries));
    const first = await observer.waitFor(method, () => true, timeoutMs, cursor, { dispatched: true });
    if (actionCalls().length !== 1 || actionCalls()[0] !== first || first.params.actionId !== actionId) fail();
    const retried = retry && await checkRetry(page, proposals, pin, target, action, true);
    // The second request can finish before the first. Await the pinned dispatch.
    await awaitResponse(first);
    if (first.result.status !== status || first.result.actionId !== actionId
        || method === 'confirmAction' && (first.result.operation !== action.operation
          || action.operation === 'update' && first.result.recordId !== action.recordId
          || action.operation === 'create' && status === 'applied' && !first.result.recordId)) fail();
    await observer.settle();
    const calls = actionCalls();
    if (calls.length !== (retried ? 2 : 1)
        || calls.some(call => call.method !== method || call.params.actionId !== actionId)) fail();
    if (calls.length === 2) {
      const duplicate = await awaitResponse(calls[1]);
      const result = duplicate.result;
      if (result.actionId !== actionId || result.operation !== first.result.operation
          || (result.status === status ? result.recordId !== first.result.recordId
            : result.status !== 'rejected' || result.recordId !== null && result.recordId !== first.result.recordId)) fail();
    }
    // Sample only after all dispatched responses. Require the owning card to
    // retain the terminal state across a render interval.
    const deadline = Date.now() + renderTimeoutMs;
    let terminalSeen = false;
    while (true) {
      if (observer.failure) throw observer.failure;
      const terminal = await cardStatus(page, card, actionId) === status;
      if (terminal && terminalSeen) break;
      if (Date.now() >= deadline) {
        throw stageError('render', status === 'stale' ? 'stale-not-rejected' : 'ui-state-invalid');
      }
      terminalSeen = terminal;
      await page.waitForTimeout(100);
    }
    await observer.settle();
    if (retry && !retried) await checkRetry(page, proposals, pin, target, action, false);
    if (actionCalls().length !== calls.length) fail();
    for (const call of calls) {
      call.card_action_id = actionId;
      call.ui_correlated = true;
    }
    if (conversationId) first.validatedTransition = { conversationId, proposal: action };
    return { first, count: calls.length };
  } finally {
    await releaseProposal(pin);
  }
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
    locator.evaluate(element => {
      function hasHandler(root) {
        for (const node of root.querySelectorAll('*')) {
          if ([...node.attributes].some(attr => /^on/i.test(attr.name))) return true;
          if (node.shadowRoot && hasHandler(node.shadowRoot)) return true;
        }
        return false;
      }
      return hasHandler(element);
    }),
    locator.evaluate(renderedTextTree).then(tree => hasCardText(tree,
      fragment => fragment.singleLine && fragment.text.includes(cardText(text)))),
  ]).then(([activeCount, eventAttrs, textVisible]) => activeCount === 0 && !eventAttrs && textVisible);
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

function ownsVisibleFocus(element) {
  // A shadow host can match :focus while its descendant has the actual focus.
  // Playwright's visible selector alone can also match a fully transparent input.
  return element.getRootNode().activeElement === element && !element.shadowRoot?.activeElement
    && element.checkVisibility({ opacityProperty: true, visibilityProperty: true });
}

async function keyboardCheck(page) {
  const setup = await enabledButton(page, 'Setup');
  await setup.focus();
  if (!await setup.evaluate(ownsVisibleFocus)) throw stageError('keyboard', 'keyboard-inaccessible');
  await page.keyboard.press('Enter');
  const deadline = Date.now() + 30000;
  const app = await appRoot(page);
  const native = page.locator(NATIVE_TEXT_FIELD).and(page.locator(':visible'));
  const field = label => app.getByLabel(label, { exact: true }).and(native);
  // Activation must reveal the configuration field. Only real Tab focus on an
  // enabled native field inside this app can supply the navigation evidence.
  await uniqueVisible(field('Named credential'), Math.max(1, deadline - Date.now()));
  const focusedField = TEXT_FIELDS.map(field).reduce((left, right) => left.or(right))
    .and(page.locator(':focus'));
  for (let index = 0; index < 10; index += 1) {
    await page.keyboard.press('Tab');
    if (await app.count() !== 1) throw stageError('keyboard', 'keyboard-inaccessible');
    if (await focusedField.count() === 1 && await focusedField.isEnabled()
        && await focusedField.evaluate(ownsVisibleFocus)) return true;
  }
  throw stageError('keyboard', 'keyboard-inaccessible');
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

async function expectConversation(observer, conversationId, startAt = 0, predicate = () => true, timeoutMs = 45000) {
  const call = await observer.waitFor('getConversation', item =>
    item.params.conversationId === conversationId && item.result.conversationId === conversationId
      && predicate(item.result), timeoutMs, startAt);
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
    const result = await observer.waitFor('getSetup', () => true, 45000, 0);
    // Read after the response and rendered transition; the initial loading text
    // is not evidence of the settled setup state.
    const setupText = await waitSetupStatus(page, result.result.status);
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
  if (step === 'setup') {
    const setupCursor = observer.mark();
    const chatCursor = observer.chatRequests.length;
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
    await region(page, 'Setup status');
    const initialCall = await observer.waitFor('getSetup', () => true, 45000, setupCursor);
    if (!initialCall || initialCall.result.status !== 'missing') throw stageError('setup-missing', 'setup-not-missing');
    await waitSetupStatus(page, 'missing');
    await screenshot(page, request, 'setup-missing');
    assertNoChatBeforeSetup(observer, chatCursor);
    const keyboardOk = await keyboardCheck(page);
    await (await input(page, 'Named credential')).fill(request.named_credential);
    await (await input(page, 'Model')).fill(request.model);
    const saveCursor = observer.mark();
    assertNoChatBeforeSetup(observer, chatCursor);
    const save = await button(page, 'Save setup');
    await save.focus();
    await page.keyboard.press('Enter');
    const saved = await observer.waitFor('saveSetup', record =>
      record.result.status === 'ready' && record.params.namedCredential === request.named_credential
        && record.params.model === request.model, 60000, saveCursor);
    const chatStarts = observer.chatRequests.slice(chatCursor).map(call => call.startedAt());
    if (!Number.isFinite(saved.response_completed_at)
        || chatStarts.some(start => !Number.isFinite(start) || start <= 0)) {
      throw stageError('controller', 'controller-proof-missing');
    }
    if (chatStarts.some(start => start <= saved.response_completed_at)) {
      throw stageError('setup-missing', 'chat-attempted-before-setup');
    }
    await waitSetupStatus(page, 'ready');
    await screenshot(page, request, 'setup-desktop');
    const connection = await testConnection(page, observer);
    await click(page, 'Setup');
    const recheckControl = await enabledButton(page, 'Recheck setup');
    const recheckCursor = observer.mark();
    await clickAppControl(page, recheckControl);
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
    observer.assertConnectionAccounted(connection);
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

  const makeMessage = content => writeMessage(page, observer, conversationId, content);
  const selectedTarget = { name: request.selected_name, nameUnique: request.selected_name_unique };
  const verifyProposal = async (target, action) => releaseProposal(await proposalRegion(page, target, action));
  const confirmProposal = (target, actionId, status, options) => {
    const turn = observer.records.findLast(record => TURN_METHODS.has(record.method)
      && record.ui_correlated && record.result.status === 'ready' && record.result.conversationId === conversationId);
    const action = turn?.result.actions.find(entry => entry.actionId === actionId && entry.status === 'proposed');
    if (!action) throw stageError(step, 'proposal-mismatch');
    return performAction(page, observer, target, action, status, { ...options, conversationId });
  };
  if (step === 'read-tool') {
    const readPrompt = `Find the demo item named ${request.selected_name}, read it, and tell me its Notes__c value exactly.`;
    const read = await makeMessage(readPrompt);
    const resultProof = findItemResult(read.added, request.selected_record_id,
      request.selected_name, request.note_payload);
    const conversationRegion = await region(page, 'Conversation');
    const markupTextSafe = await noUnsafeMarkup(request.note_payload, conversationRegion);
    const persisted = read.conversation.conversationId === conversationId
      && read.added.toolCalls.some(call => call.name === 'read_item');
    const assistantUsedResult = read.added.messages.some(message =>
      message.role === 'assistant' && message.content.includes(request.nonce));
    const promptExcludedNonce = !readPrompt.includes(request.nonce) && !readPrompt.includes(request.note_payload);
    const desktopLayoutOk = await checkLayout(page, 1280, 900);
    await screenshot(page, request, 'pending-desktop');
    await page.setViewportSize({ width: 390, height: 844 });
    const narrowLayoutOk = await checkLayout(page, 390, 844);
    await screenshot(page, request, 'chat-narrow');
    await observer.settle();
    return publicProjection(observer, page, request, { ...common,
      chat_turn: { step, ...read.proof },
      read_tool_proof: { find_items: resultProof.find, read_item: resultProof.read,
        result_matches_nonce: resultProof.result, assistant_used_result: assistantUsedResult && persisted,
        conversation_persisted: persisted, prompt_excluded_nonce: promptExcludedNonce,
        unsafe_markup_is_text: markupTextSafe },
      desktop_layout_ok: desktopLayoutOk, narrow_layout_ok: narrowLayoutOk,
      safe_text_ok: markupTextSafe, conversation_id: conversationId,
      provider_calls: session.providerCalls(), screenshots: 2 });
  }

  if (step === 'create-proposal') {
    const content = `Create one work item named ${request.create_name}, with Status__c Open and Notes__c ${request.create_notes}. Show the exact proposal and wait for my confirmation.`;
    const sent = await makeMessage(content);
    const toolProposal = hasToolCall(sent.added, 'propose_create_item', args =>
      exactKeys(args, ['fields']) && isRecord(args.fields)
      && args.fields.Name === request.create_name && args.fields.Status__c === 'Open'
      && args.fields.Notes__c === request.create_notes && Object.keys(args.fields).length === 3);
    if (!toolProposal) throw stageError('create-proposal', 'proposal-mismatch');
    const action = findAction(sent.added, 'create', entry => entry.recordId === null
      && Object.keys(entry.oldValues).length === 0
      && entry.newValues.Name === request.create_name && entry.newValues.Status__c === 'Open'
      && entry.newValues.Notes__c === request.create_notes && Object.keys(entry.newValues).length === 3);
    if (!action) throw stageError('create-proposal', 'proposal-mismatch');
    await verifyProposal({ name: request.create_name }, action);
    await page.setViewportSize({ width: 1280, height: 900 });
    await screenshot(page, request, 'pending-desktop');
    await observer.settle();
    return publicProjection(observer, page, request, { ...common,
      chat_turn: { step, ...sent.proof, proposal_action_id: action.actionId },
      proposal_exact: true, action_id: action.actionId, conversation_id: conversationId,
      provider_calls: session.providerCalls() });
  }

  if (step === 'create-confirm') {
    const confirmation = await confirmProposal({ name: request.create_name }, request.create_action_id,
      'applied', { retry: true });
    const reloadCursor = observer.mark();
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
    await region(page, 'Conversation');
    const reopened = await expectConversation(observer, conversationId, reloadCursor,
      value => value.actions.some(action => action.actionId === request.create_action_id && action.status === 'applied'));
    const actionAfterReload = reopened.actions.find(action => action.actionId === request.create_action_id);
    const statusPersisted = actionAfterReload && actionAfterReload.status === 'applied';
    await observer.settle();
    return publicProjection(observer, page, request, { ...common,
      one_write: confirmation.first.result.status === 'applied', duplicate_safe: true,
      duplicate_attempted: true, duplicate_delivery_count: confirmation.count,
      reload_history_persisted: statusPersisted, action_id: request.create_action_id,
      conversation_id: conversationId, provider_calls: session.providerCalls() });
  }

  if (step === 'update-proposal') {
    const content = `Update the demo item named ${request.selected_name} so Status__c is Done. Leave all other fields unchanged and wait for confirmation.`;
    const sent = await makeMessage(content);
    const toolProposal = hasToolCall(sent.added, 'propose_update_item', args =>
      exactKeys(args, ['recordId', 'fields']) && args.recordId === request.selected_record_id
      && exactKeys(args.fields, ['Status__c']) && args.fields.Status__c === 'Done');
    if (!toolProposal) throw stageError(step, 'proposal-mismatch');
    const action = findAction(sent.added, 'update', entry => entry.recordId === request.selected_record_id
      && Object.keys(entry.newValues).length === 1 && entry.newValues.Status__c === 'Done'
      && entry.oldValues.Status__c === 'Open');
    if (!action) throw stageError(step, 'proposal-mismatch');
    await verifyProposal(selectedTarget, action);
    return publicProjection(observer, page, request, { ...common, proposal_exact: true,
      chat_turn: { step, ...sent.proof, proposal_action_id: action.actionId },
      action_id: action.actionId, conversation_id: conversationId, provider_calls: session.providerCalls() });
  }

  if (step === 'update-confirm') {
    const { first } = await confirmProposal(selectedTarget, request.update_action_id, 'applied');
    return publicProjection(observer, page, request, { ...common, one_write: first.result.status === 'applied',
      action_id: request.update_action_id, conversation_id: conversationId, provider_calls: session.providerCalls() });
  }

  if (step === 'cancel-proposal') {
    const content = `Create one work item named ${request.cancel_name}, with Status__c Open and Notes__c ${request.cancel_notes}. Wait for confirmation.`;
    const sent = await makeMessage(content);
    const toolProposal = hasToolCall(sent.added, 'propose_create_item', args =>
      exactKeys(args, ['fields']) && isRecord(args.fields)
      && args.fields.Name === request.cancel_name && args.fields.Status__c === 'Open'
      && args.fields.Notes__c === request.cancel_notes && Object.keys(args.fields).length === 3);
    if (!toolProposal) throw stageError(step, 'proposal-mismatch');
    const action = findAction(sent.added, 'create', entry => entry.recordId === null
      && Object.keys(entry.oldValues).length === 0
      && entry.newValues.Name === request.cancel_name && entry.newValues.Status__c === 'Open'
      && entry.newValues.Notes__c === request.cancel_notes && Object.keys(entry.newValues).length === 3);
    if (!action) throw stageError(step, 'proposal-mismatch');
    await verifyProposal({ name: request.cancel_name }, action);
    return publicProjection(observer, page, request, { ...common, proposal_exact: true,
      chat_turn: { step, ...sent.proof, proposal_action_id: action.actionId },
      action_id: action.actionId, conversation_id: conversationId, provider_calls: session.providerCalls() });
  }

  if (step === 'cancel-confirm') {
    const { first: cancelled } = await confirmProposal({ name: request.cancel_name },
      request.cancel_action_id, 'cancelled');
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
    const toolProposal = hasToolCall(sent.added, 'propose_update_item', args =>
      exactKeys(args, ['recordId', 'fields']) && args.recordId === request.selected_record_id
      && exactKeys(args.fields, ['Notes__c']) && args.fields.Notes__c === request.stale_notes);
    if (!toolProposal) throw stageError(step, 'proposal-mismatch');
    const action = findAction(sent.added, 'update', entry => entry.recordId === request.selected_record_id
      && Object.keys(entry.newValues).length === 1 && entry.newValues.Notes__c === request.stale_notes
      && entry.oldValues.Notes__c === request.note_payload);
    if (!action) throw stageError(step, 'proposal-mismatch');
    await verifyProposal(selectedTarget, action);
    return publicProjection(observer, page, request, { ...common, proposal_exact: true,
      chat_turn: { step, ...sent.proof, proposal_action_id: action.actionId },
      action_id: action.actionId, conversation_id: conversationId, provider_calls: session.providerCalls() });
  }

  if (step === 'stale-confirm') {
    const { first: stale } = await confirmProposal(selectedTarget,
      request.stale_action_id, 'stale');
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
  if (/^(?:update|stale)-(?:proposal|confirm)$/.test(request.step)
      && typeof request.selected_name_unique !== 'boolean') {
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

async function failureReply(observer, request, error, stage, ipcDeadline = Date.now() + 1000) {
  // Reserve IPC write time and cap diagnostic work at one second. Recheck the
  // live sets: responses can register while earlier bodies drain, and dispatched
  // requests still need both response processing and a terminal lifecycle event.
  const deadline = Math.min(Date.now() + 1000, ipcDeadline - 25);
  while (observer && (observer.pending.size || observer.unresolvedRequests.size) && Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, Math.min(5, Math.max(1, deadline - Date.now()))));
  }
  const pendingJobs = observer?.pending.size || 0;
  const unresolvedRequests = observer?.unresolvedRequests.size || 0;
  return {
    status: 'failed', ipc_id: request && request.ipc_id,
    stage: safeErrorCode(error, 'stage', SAFE_STAGES, stage),
    reason: safeErrorCode(error, 'reason', SAFE_REASONS, 'evaluation-failed'),
    controller_calls: observer ? observer.projection() : [],
    browser_failure: { ...(observer?.firstFailure || { step: request?.step, branch: 'step-failure',
      ipc_id: request?.ipc_id }),
      // Counts describe missing evidence, never a retry or an acceptance gate.
      drain_state: pendingJobs || unresolvedRequests ? 'incomplete' : 'complete',
      pending_jobs: Math.min(10000, pendingJobs),
      unresolved_requests: Math.min(10000, unresolvedRequests) },
  };
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
      let ipcDeadline = Date.now() + 1000;
      try {
        const parsed = JSON.parse(line);
        if (Number.isSafeInteger(parsed?.ipc_deadline_ms)) ipcDeadline = parsed.ipc_deadline_ms;
        if (isRecord(parsed) && parsed.close === true) break;
        request = validateRequest(parsed);
        if (observer) { observer.step = request.step; observer.ipcId = request.ipc_id; }
        if (!session) {
          if (request.step !== 'attempt') throw stageError('browser', 'invalid-options');
          observer = new ApexObserver(null, request.expected_lightning_host, { trackSplit: request.mode === 'run' });
          observer.step = request.step;
          observer.ipcId = request.ipc_id;
          stage = 'route';
          session = await createSession(request, observer);
          session.uiAttemptedFirst = true;
          session.binding = {
            mode: request.mode, phase: request.phase, source_head: request.source_head,
            candidate_metadata_sha256: request.candidate_metadata_sha256,
            expected_lightning_host: request.expected_lightning_host,
          };
        } else if (session.binding.mode !== request.mode || session.binding.phase !== request.phase
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
        if (request.mode === 'run' && !['attempt', 'authenticate'].includes(request.step)) {
          observer.assertTurnsAccounted();
        }
        process.stdout.write(JSON.stringify({ ...result, ipc_id: request.ipc_id }) + '\n');
      } catch (error) {
        process.stdout.write(JSON.stringify(await failureReply(observer, request, error, stage, ipcDeadline)) + '\n');
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
  chatAttempts, assertNoChatBeforeSetup, click, enabledButton, runStep, matchTurn, writeMessage, performAction,
  serverRequestId, testConnection, keyboardCheck, failureReply,
};

if (require.main === module) main();
