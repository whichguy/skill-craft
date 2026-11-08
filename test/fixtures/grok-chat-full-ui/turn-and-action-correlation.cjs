'use strict';

// Synthetic calibration only. Route every request locally through Playwright.
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const browserTools = require('../../shiploop_e2e/checks/battleship_ui_browser.cjs');
const driver = require('../../shiploop_e2e/checks/grok_chat_full_ui_browser.cjs');

const host = 'calibration.lightning.force.com';
const conversationId = 'a01000000000001AAA';
const recordId = 'a02000000000001AAA';
const otherId = 'a02000000000002AAA';
const message = 'Find the synthetic item.';
const token = 'synthetic-pending-capability';
const actionId = 'update-this-action';

const prior = [
  { role: 'user', content: 'Earlier question' },
  { role: 'assistant', content: 'Earlier reply' },
];
const completed = [...prior, { role: 'user', content: message }, { role: 'assistant', content: 'Fresh reply' }];
const conversation = (messages, fields = {}) => ({
  conversationId, messages, status: 'ready', actions: [], toolCalls: [], ...fields,
});

function installFixtureRuntime() {
  let sequence = 0;
  window.rpcBatch = async entries => {
    const response = await fetch('/aura', { method: 'POST', body: JSON.stringify({ actions: entries.map(([method, params]) => ({
      id: 'req-' + (++sequence) + ';a', descriptor: 'aura://ApexActionController/ACTION$execute',
      params: { classname: 'SLGrokChatController', method, params },
    })) }) });
    const body = await response.json();
    return body.actions.map(action => JSON.parse(action.returnValue.returnValue));
  };
  window.rpc = async (method, params) => (await window.rpcBatch([[method, params]]))[0];
  customElements.define('fixture-text', class extends HTMLElement {
    connectedCallback() {
      const value = this.textContent;
      this.textContent = '';
      this.attachShadow({ mode: 'open' }).append(document.createTextNode(value));
    }
  });
  customElements.define('fixture-button', class extends HTMLElement {
    connectedCallback() {
      if (this.shadowRoot) return;
      const button = document.createElement('button');
      button.textContent = this.getAttribute('label');
      this.attachShadow({ mode: 'open' }).append(button);
    }
  });
  customElements.define('fixture-action-status', class extends HTMLElement {
    connectedCallback() {
      const status = document.createElement('section');
      status.setAttribute('aria-label', 'Action status');
      status.textContent = 'proposed';
      this.attachShadow({ mode: 'open' }).append(status);
    }
  });
}

async function withPage(browser, markup, handle, scenario, mount = '') {
  const html = '<!doctype html><meta charset="utf-8">' + markup
    + `<script>(${installFixtureRuntime})();${mount}</script>`;
  const context = await browser.newContext({ serviceWorkers: 'block' });
  const page = await context.newPage();
  const observer = new driver.ApexObserver(page, host, { trackSplit: true });
  observer.attach();
  const calls = [];
  let batches = 0;
  await context.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    assert.equal(url.hostname, host, 'The fixture must not access external services');
    if (url.pathname !== '/aura') {
      return route.fulfill({ contentType: 'text/html', body: html });
    }
    const batch = ++batches;
    const actions = await Promise.all(JSON.parse(request.postData()).actions.map(async action => {
      const { method, params } = action.params;
      calls.push({ method, params });
      const { payload, responseId = action.id } = await handle(method, params);
      return { id: responseId, state: 'SUCCESS',
        returnValue: { returnValue: JSON.stringify(payload), cacheable: false } };
    }));
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ actions }),
      headers: { 'x-sfdc-request-id': 'fixture-' + batch } });
  });
  try {
    await page.goto('https://' + host + '/lightning/n/SLGrokChat_Chat');
    return await scenario(page, observer, calls);
  } finally {
    await context.close();
  }
}

const directSendCases = [
  'direct', 'missing-render', 'hidden-shadow', 'nested-shadow', 'sibling-shadow',
  'wrong-body-with-matching-fragment', 'clipped-reply', 'first-glyph-only-reply', 'scrollable-history', 'message-metadata',
  'inset-clipped-reply', 'unsupported-ancestor-clip-reply', 'fully-visible-inset-reply',
  'partially-clipped-extra-line', 'unevaluable-extra-line', 'fully-hidden-extra-lines',
  'zero-width-overflow-extra-line', 'partially-visible-overflow-extra-line',
  'absolute-overflow-extra-line', 'fixed-overflow-extra-line',
];

async function sendScenario(browser, kind) {
  const position = { 'absolute-overflow-extra-line': 'absolute', 'fixed-overflow-extra-line': 'fixed' }[kind];
  const style = kind === 'scrollable-history' ? ' style="height: 75px; overflow: auto"' : '';
  const markup = '<section aria-label="Conversation" id="history"' + style + '></section>'
    + '<section aria-label="Chat status"><p id="state">ready</p></section>'
    + '<label>Message<textarea></textarea></label><button id="send">Send</button>';
  const handle = (method, params) => {
    if (method === 'getConversation') return { payload: conversation(prior) };
    if (method === 'beginMessage') return { payload: conversation([...prior, completed[2]], {
      conversationId: params.conversationId, status: 'working',
      pending: { token, requestId: params.clientRequestId, message: params.message, status: 'working' },
    }) };
    if (method === 'sendMessage') return { payload: conversation(completed) };
    assert.equal(method, 'executePendingMessage');
    return { payload: conversation(kind === 'replay' ? prior : completed),
      responseId: kind === 'wrong-response-id' ? 'other;a' : undefined };
  };
  return withPage(browser, markup, handle, async (page, observer) => {
    await page.evaluate(async ({ kind, conversationId, direct, position }) => {
      const region = document.getElementById('history');
      const state = document.getElementById('state');
      const render = (value, priorOnly = false) => {
        let sibling;
        region.replaceChildren(...value.messages.filter(row => !priorOnly || row.content !== 'Fresh reply').map(row => {
          const card = document.createElement('article');
          const heading = document.createElement('h3');
          heading.textContent = row.role;
          const text = document.createElement('fixture-text');
          text.textContent = row.content;
          card.append(heading, text);
          if (row.content === 'Fresh reply') {
            if (kind === 'hidden-shadow') text.style.opacity = '0';
            if (kind === 'nested-shadow') {
              const nested = document.createElement('div');
              nested.setAttribute('role', 'group');
              nested.append(text);
              card.append(nested);
            }
            if (kind === 'sibling-shadow') {
              text.remove();
              sibling = text;
            }
            if (kind === 'wrong-body-with-matching-fragment') {
              const wrong = document.createElement('p');
              wrong.textContent = 'Wrong visible reply';
              const fragment = document.createElement('small');
              fragment.append(text);
              card.append(wrong, fragment);
            }
            if (kind === 'clipped-reply') {
              const clip = document.createElement('div');
              clip.style.cssText = 'height: 12px; overflow: hidden';
              const spacer = document.createElement('div');
              spacer.style.height = '60px';
              clip.append(spacer, text);
              card.append(clip);
            }
            if (kind === 'first-glyph-only-reply') {
              text.style.cssText = 'display:block; width:1.1ch; overflow:hidden; white-space:nowrap; font-family:monospace';
            }
            if (kind === 'inset-clipped-reply' || kind === 'fully-visible-inset-reply') {
              text.style.cssText = 'display:block; width:22ch; padding-block:4px; white-space:nowrap; font-family:monospace';
              text.style.clipPath = kind === 'inset-clipped-reply' ? 'inset(0 95% 0 0)' : 'inset(0 20px 0 0)';
            }
            if (kind === 'unsupported-ancestor-clip-reply') {
              const clip = document.createElement('div');
              clip.style.clipPath = 'circle(10px at left center)';
              clip.append(text);
              card.append(clip);
            }
            if (kind === 'zero-width-overflow-extra-line' || kind === 'partially-visible-overflow-extra-line') {
              const extra = document.createElement('div');
              const width = kind === 'zero-width-overflow-extra-line' ? '0' : '2ch';
              extra.style.cssText = 'width:' + width + '; overflow:hidden; white-space:nowrap; font-family:monospace';
              extra.textContent = 'Extra reply line';
              card.append(extra);
            }
            if (position) {
              card.style.cssText = 'position:relative; min-height:90px';
              const clip = document.createElement('div');
              clip.style.cssText = 'width:0; overflow:hidden; white-space:nowrap';
              const extra = document.createElement('span');
              extra.id = 'positioned-extra-line';
              extra.style.position = position;
              extra.style.left = position === 'absolute' ? '0' : '300px';
              extra.style.top = position === 'absolute' ? '64px' : '8px';
              extra.textContent = 'Extra reply line';
              clip.append(extra);
              card.append(clip);
            }
            if (['partially-clipped-extra-line', 'unevaluable-extra-line', 'fully-hidden-extra-lines'].includes(kind)) {
              const extra = document.createElement('div');
              extra.style.cssText = 'width:22ch; padding-block:4px; white-space:nowrap; font-family:monospace';
              extra.style.clipPath = {
                'partially-clipped-extra-line': 'inset(0 72% 0 0)',
                'unevaluable-extra-line': 'circle(10px at left center)',
                'fully-hidden-extra-lines': 'inset(0 0 0 85%)',
              }[kind];
              extra.textContent = 'Extra reply line';
              card.append(extra);
              if (kind === 'fully-hidden-extra-lines') {
                const hidden = document.createElement('div');
                hidden.style.opacity = '0';
                hidden.textContent = 'Invisible reply line';
                card.append(hidden);
              }
            }
            if (kind === 'message-metadata') {
              const timestamp = document.createElement('time');
              timestamp.dateTime = '2026-11-08';
              timestamp.textContent = 'November 8';
              const metadata = document.createElement('div');
              metadata.setAttribute('aria-label', 'Message metadata');
              metadata.textContent = 'Delivery succeeded';
              card.append(timestamp, metadata);
            }
          }
          return card;
        }));
        if (sibling) region.append(sibling);
        if (kind === 'scrollable-history') region.scrollTop = 0;
        state.textContent = value.status;
      };
      render(await window.rpc('getConversation', { conversationId }));
      document.getElementById('send').onclick = async () => {
        state.textContent = 'working';
        const message = document.querySelector('textarea').value;
        if (direct) {
          const response = await window.rpc('sendMessage', { conversationId, message });
          render(response, kind === 'missing-render');
          return;
        }
        const start = await window.rpc('beginMessage', {
          conversationId: kind === 'wrong-conversation' ? 'a01000000000002AAA' : conversationId,
          message, clientRequestId: 'ui-request-1',
        });
        render(start);
        const response = await window.rpc('executePendingMessage', {
          conversationId, turnToken: kind === 'wrong-token' ? 'wrong-token' : start.pending.token,
        });
        // Observer must wait past the completed response for its rendered messages.
        setTimeout(() => render(response), 250);
      };
    }, { kind, conversationId, direct: directSendCases.includes(kind), position });
    const run = () => driver.writeMessage(page, observer, conversationId, message, 2200);
    if (['direct', 'split', 'scrollable-history', 'message-metadata', 'fully-visible-inset-reply',
      'fully-hidden-extra-lines', 'zero-width-overflow-extra-line'].includes(kind)) {
      const result = await run();
      assert.equal(result.call.method, kind === 'split' ? 'executePendingMessage' : 'sendMessage');
      assert.equal(result.proof.final_message_count, 4);
      assert.equal(result.proof.rendered_history_matched, true);
      observer.assertTurnsAccounted();
      assert.ok(!JSON.stringify(observer.projection()).includes(token));
      if (kind === 'scrollable-history') {
        assert.equal(await page.locator('#history').evaluate(history =>
          history.lastElementChild.getBoundingClientRect().top >= history.getBoundingClientRect().bottom), true);
      }
    } else if (position) {
      const [result] = await Promise.allSettled([run()]);
      const firstGlyphHit = await page.locator('#positioned-extra-line').evaluate(extra => {
        const range = document.createRange();
        range.setStart(extra.firstChild, 0);
        range.setEnd(extra.firstChild, 1);
        const { x, y, width, height } = range.getBoundingClientRect();
        return width > 0 && height > 0 && document.elementFromPoint(x + width / 2, y + height / 2) === extra;
      }, undefined, { timeout: 1000 });
      assert.equal(firstGlyphHit, true, `${kind} must expose the extra text`);
      assert.equal(result.status, 'rejected', `${kind} must fail exact history matching`);
      assert.equal(result.reason.reason, 'controller-proof-missing');
    } else {
      const expected = kind === 'wrong-response-id' ? 'controller-response-id-mismatch' : 'controller-proof-missing';
      await assert.rejects(run, error => error.reason === expected);
    }
    return kind;
  });
}

const name = 'Shared item name';
const update = { actionId, status: 'proposed', operation: 'update', recordId,
  oldValues: { Status__c: 'Open' }, newValues: { Status__c: 'Done' } };
const stale = { ...update, oldValues: { Notes__c: 'Old note' }, newValues: { Notes__c: 'New note' } };
const create = { actionId, status: 'proposed', operation: 'create', recordId: null, oldValues: {},
  newValues: { Name: name, Status__c: 'Open', Notes__c: 'Synthetic note' } };
const chatMarkup = '<section aria-label="Conversation" id="history"><p>No messages yet.</p></section>'
  + '<section aria-label="Chat status"><p>ready</p></section>'
  + '<label>Message<textarea></textarea></label><button id="send">Send</button>';
const clippedProposalExtra = '<div style="width:22ch; padding-block:4px; white-space:nowrap; '
  + 'font-family:monospace; clip-path:inset(0 72% 0 0)">Extra value line</div>';

function proposal(id, action, {
  target = action.recordId || 'New item', label = 'Target', swapped = false,
  incidental = '', controls = true, marker = action.actionId, nested = false, alternateLayout = false,
  nestedDetails = false, nestedOperation = false, heading = action.operation + ' work item', labelledOperation = false,
  nestedLabelledFields = false, nestedLabelledControls = false, clippedField = false, fieldInset, clippedExtra = false,
} = {}) {
  const buttons = '<fixture-button label="Confirm" data-action-id="' + marker + '"></fixture-button>'
    + '<fixture-button label="Cancel" data-action-id="' + marker + '"></fixture-button>';
  const fields = Object.entries(action.newValues).map(([field, next]) => {
    const old = action.oldValues[field] ?? '(new item)';
    const oldText = swapped ? next : old;
    const newText = swapped ? old : next;
    if (alternateLayout) {
      return '<div role="group" aria-label="Field changes"><fieldset><legend>' + field
        + '</legend><dl><dt>Old value</dt><dd>' + oldText + '</dd><dt>New value</dt><dd>'
        + newText + '</dd></dl></fieldset></div>';
    }
    const clip = clippedField ? ' style="display:block; width:1.1ch; overflow:hidden; white-space:nowrap; font-family:monospace"' : '';
    const value = '<fixture-text' + clip + '>' + newText + '</fixture-text>';
    let shownValue = fieldInset
      ? '<div style="width:22ch; padding-block:4px; font-family:monospace; clip-path:' + fieldInset + '">' + value + '</div>' : value;
    if (clippedExtra) {
      shownValue = '<div>' + shownValue + clippedProposalExtra + '</div>';
    }
    return '<div><p>' + field + '</p><div><p>Old value</p><fixture-text>' + oldText + '</fixture-text></div>'
      + '<div><p>New value</p>' + shownValue + '</div></div>';
  }).join('');
  const status = '<section aria-label="Action status">proposed</section>';
  const nestedProposal = content => '<section aria-labelledby="' + id + '-nested-title"><h4 id="'
    + id + '-nested-title">Proposed change</h4>' + content + '</section>';
  const details = '<p>' + label + ': ' + target + '</p>' + (nestedLabelledFields ? nestedProposal(fields) : fields);
  const operation = labelledOperation ? '<p aria-label="Operation">' + action.operation + '</p>' : '<h3>' + heading + '</h3>';
  return '<article id="' + id + '"><section aria-label="Proposed change">'
    + (nestedOperation ? '<div role="group" aria-label="Other action">' + operation + '</div>' : operation)
    + incidental
    + (nestedDetails ? '<div role="group" aria-label="Other action">' + details + '</div>' : details)
    + '<div class="controls">' + (controls ? nestedLabelledControls ? nestedProposal(buttons) : buttons : '') + '</div></section>'
    + (nested ? '<article><fixture-action-status></fixture-action-status></article>' : status) + '</article>';
}

async function actionScenario(browser, kind) {
  const retry = kind.startsWith('retry-');
  const action = retry ? create : kind === 'stale-name' ? stale
    : kind === 'fieldset-and-labelled-operation' ? { ...stale, newValues: { Notes__c: 'Target: New note' } }
      : update;
  const terminal = action === stale ? 'stale' : 'applied';
  const nameOnly = ['update-name', 'stale-name', 'ambiguous-name', 'wrong-result-record'].includes(kind);
  const shownName = 'Sha\u200bred item\u00a0 name';
  const nonuniqueSnapshot = ['nonunique-name', 'authoritative-id'].includes(kind);
  const normalizedName = kind === 'normalized-name' || nonuniqueSnapshot;
  const selected = proposal('selected', action, {
    target: kind === 'normalized-name' || kind === 'nonunique-name' ? shownName
      : nameOnly ? name : kind === 'incidental-target' ? otherId : undefined,
    label: kind === 'stale-name' ? 'Name' : 'Target',
    incidental: kind === 'incidental-target' ? '<p>' + recordId + '</p><p>Name: ' + name + '</p>'
      : kind === 'wrong-operation-prose' ? '<p>Update this record only after confirmation.</p>'
        : kind === 'foreign-action-clipped-extra' ? '<div role="group" aria-label="Other action">'
          + '<h3>Create work item</h3>' + clippedProposalExtra + '</div>' : '',
    swapped: kind === 'swapped-values', marker: kind === 'wrong-marker' ? 'different-action' : actionId,
    controls: !['delayed-controls', 'absent-controls'].includes(kind),
    nested: kind === 'nested-status', alternateLayout: ['stale-name', 'fieldset-and-labelled-operation'].includes(kind),
    nestedDetails: kind === 'nested-action-details',
    nestedOperation: kind === 'nested-action-operation',
    nestedLabelledFields: kind === 'nested-labelledby-fields',
    nestedLabelledControls: kind === 'nested-labelledby-controls',
    clippedField: kind === 'clipped-proposal-field',
    fieldInset: { 'ancestor-inset-clipped-proposal-field': 'inset(0 95% 0 0)',
      'fully-visible-inset-proposal-field': 'inset(0 60% 0 0)' }[kind],
    clippedExtra: kind === 'partially-clipped-proposal-extra',
    heading: kind === 'wrong-operation-prose' ? 'Create work item' : undefined,
    labelledOperation: kind === 'fieldset-and-labelled-operation',
  });
  const decoy = proposal('decoy', { ...update, recordId: kind === 'ambiguous-record' ? recordId : otherId,
    actionId: 'other-proposal' }, { target: nonuniqueSnapshot || kind === 'ambiguous-name' ? name : undefined,
    incidental: '<p>' + name + '</p>' });
  const markup = '<section aria-label="Conversation">'
    + '<article id="old"><section aria-label="Action status">applied</section></article>'
    + decoy + (kind === 'delayed-card' ? '' : selected) + '</section>';
  let writes = 0;
  let releaseFirst;
  const firstMayReturn = new Promise(resolve => { releaseFirst = resolve; });
  let deliveries = 0;
  const completionOrder = [];
  const handle = async (method, params) => {
    assert.equal(method, 'confirmAction');
    const delivery = ++deliveries;
    const outOfOrder = kind === 'retry-out-of-order' || kind === 'retry-wrong-result';
    if (delivery === 1 && terminal === 'applied') writes += 1;
    if (outOfOrder && delivery === 1) {
      const safety = setTimeout(releaseFirst, 1800);
      try { await firstMayReturn; } finally { clearTimeout(safety); }
    }
    if (outOfOrder && delivery === 2) setTimeout(releaseFirst, 350);
    if (kind === 'retry-applied-then-rejected' && delivery === 2) await new Promise(resolve => setTimeout(resolve, 650));
    completionOrder.push(delivery);
    return { payload: { actionId: params.actionId, operation: action.operation,
      status: delivery === 1 ? terminal : 'rejected',
      recordId: kind === 'wrong-result-record' || (kind === 'retry-wrong-result' && delivery === 2)
        ? otherId : delivery === 1 ? recordId : null } };
  };

  return withPage(browser, markup, handle, async (page, observer, calls) => {
    await page.evaluate(({ kind, actionId, selected }) => {
      window.confirmationResponses = [];
      window.statusBeforeRejection = null;
      function connect(card) {
        const control = card.querySelector('fixture-button[label="Confirm"]');
        if (!control) return;
        const onClick = async () => {
          const requestedAction = kind === 'wrong-rpc' || card.id === 'decoy'
            ? 'wrong-action' : control.getAttribute('data-action-id');
          if (card.id === 'selected' && kind === 'retry-disabled') {
            control.shadowRoot.querySelector('button').disabled = true;
          }
          if (card.id === 'selected' && kind === 'retry-removed') control.remove();
          if (card.id === 'selected' && kind === 'retry-enabled-replacement' && control.isConnected) {
            const replacement = document.createElement('fixture-button');
            replacement.setAttribute('label', 'Confirm');
            replacement.setAttribute('data-action-id', actionId);
            replacement.addEventListener('click', onClick);
            control.replaceWith(replacement);
          }
          if (kind === 'retry-rebound') control.setAttribute('data-action-id', 'other-proposal');
          if (kind === 'retry-reparented') document.querySelector('#decoy .controls').append(control);
          const result = await window.rpc('confirmAction', { actionId: requestedAction });
          window.confirmationResponses.push(result.status);
          if (result.status === 'rejected') {
            if (kind === 'retry-applied-then-rejected') {
              const status = card.querySelector('[aria-label="Action status"]');
              window.statusBeforeRejection = status.textContent;
              status.textContent = 'rejected';
            }
            return;
          }
          setTimeout(() => {
            const changed = kind === 'wrong-status' ? document.getElementById('decoy') : card;
            if (!['retry-disabled', 'retry-enabled-replacement'].includes(kind)) {
              changed.querySelector('[aria-label="Proposed change"]')?.remove();
            }
            const status = changed.querySelector('[aria-label="Action status"]')
              || changed.querySelector('fixture-action-status').shadowRoot.querySelector('section');
            status.textContent = result.status;
          }, 280);
        };
        control.addEventListener('click', onClick);
      }
      connect(document.getElementById('decoy'));
      const card = document.getElementById('selected');
      if (kind === 'delayed-card') {
        setTimeout(() => {
          document.querySelector('[aria-label="Conversation"]').insertAdjacentHTML('beforeend', selected);
          connect(document.getElementById('selected'));
        }, 300);
      } else if (kind === 'delayed-controls') {
        setTimeout(() => {
          const controls = card.querySelector('.controls');
          for (const label of ['Confirm', 'Cancel']) {
            const button = document.createElement('fixture-button');
            button.setAttribute('label', label);
            button.setAttribute('data-action-id', actionId);
            controls.append(button);
          }
          connect(card);
        }, 300);
      } else {
        connect(card);
      }
    }, { kind, actionId, selected });

    const target = { name: normalizedName ? 'Shared  item name\u00ad' : name, nameUnique: !nonuniqueSnapshot };
    const run = () => driver.performAction(page, observer, target, action, terminal, {
      retry, timeoutMs: 2200, renderTimeoutMs: 1000, proposalTimeoutMs: 950,
    });
    const reasons = { 'wrong-status': 'ui-state-invalid', 'nested-status': 'ui-state-invalid',
      'wrong-marker': 'proposal-mismatch', 'wrong-rpc': 'controller-proof-missing',
      'ambiguous-record': 'proposal-missing', 'ambiguous-name': 'proposal-missing', 'nonunique-name': 'proposal-missing',
      'swapped-values': 'proposal-mismatch', 'incidental-target': 'proposal-missing',
      'nested-action-details': 'proposal-missing', 'nested-action-operation': 'proposal-mismatch',
      'nested-labelledby-fields': 'proposal-mismatch', 'nested-labelledby-controls': 'proposal-mismatch',
      'clipped-proposal-field': 'proposal-mismatch', 'ancestor-inset-clipped-proposal-field': 'proposal-mismatch',
      'partially-clipped-proposal-extra': 'proposal-mismatch',
      'wrong-operation-prose': 'proposal-mismatch',
      'absent-controls': 'proposal-mismatch', 'wrong-result-record': 'controller-proof-missing',
      'retry-wrong-result': 'controller-proof-missing', 'retry-rebound': 'proposal-mismatch',
      'retry-reparented': 'proposal-mismatch', 'retry-enabled-replacement': 'proposal-mismatch',
      'retry-applied-then-rejected': 'ui-state-invalid' };
    if (Object.hasOwn(reasons, kind)) {
      await assert.rejects(run, error => error.reason === reasons[kind]);
      if (['retry-rebound', 'retry-reparented', 'retry-enabled-replacement'].includes(kind)) {
        await page.waitForFunction(() => window.confirmationResponses.length === 1, undefined, { timeout: 2200 });
        assert.deepEqual(calls.map(call => call.params.actionId), [actionId]);
      }
      if (kind === 'retry-enabled-replacement') {
        assert.equal(await page.locator('#selected').getByRole('button', { name: 'Confirm', exact: true }).isEnabled(), true);
        assert.equal(observer.projection().some(call => call.ui_correlated), false);
      }
      const afterClick = ['wrong-status', 'nested-status', 'wrong-rpc', 'wrong-result-record',
        'retry-rebound', 'retry-reparented', 'retry-enabled-replacement'];
      const retried = ['retry-wrong-result', 'retry-applied-then-rejected'].includes(kind);
      assert.equal(calls.length, retried ? 2 : Number(afterClick.includes(kind)));
      if (kind === 'retry-applied-then-rejected') {
        assert.deepEqual(await page.evaluate(() => window.confirmationResponses), ['applied', 'rejected']);
        assert.equal(await page.evaluate(() => window.statusBeforeRejection), 'applied');
        assert.equal(await page.locator('#selected').getByRole('region', { name: 'Action status' }).innerText(), 'rejected');
      }
    } else {
      const result = await run();
      const count = kind === 'retry-out-of-order' ? 2 : 1;
      assert.equal(result.first.result.actionId, actionId);
      assert.equal(result.first.result.status, terminal);
      assert.equal(result.count, count);
      assert.equal(await page.locator('#selected').getByRole('region', { name: 'Action status' }).innerText(), terminal);
      assert.deepEqual(observer.projection().map(call => call.card_action_id), Array(count).fill(actionId));
      assert.deepEqual(calls.map(call => call.params.actionId), Array(count).fill(actionId));
      assert.deepEqual(completionOrder, count === 2 ? [2, 1] : [1]);
      assert.deepEqual(await page.evaluate(() => window.confirmationResponses), count === 2 ? ['rejected', terminal] : [terminal]);
      assert.equal(writes, terminal === 'applied' ? 1 : 0);
      const confirm = page.locator('#selected').getByRole('button', { name: 'Confirm', exact: true });
      if (kind === 'retry-removed') assert.equal(await confirm.count(), 0);
      if (kind === 'retry-disabled') assert.equal(await confirm.isDisabled(), true);
    }
    return kind;
  });
}

async function delayedProposalAfterSend(browser) {
  const args = { recordId, fields: { Status__c: 'Done' } };
  const handle = (method, params) => {
    if (method === 'getConversation') return { payload: conversation([]) };
    assert.equal(method, 'sendMessage');
    return { payload: conversation([{ role: 'user', content: params.message }, completed.at(-1)], {
      actions: [update], toolCalls: [{ name: 'propose_update_item', status: 'ok', arguments: args, result: {} }],
    }) };
  };
  return withPage(browser, chatMarkup, handle, async (page, observer) => {
    await page.evaluate(async ({ conversationId, markup }) => {
      await window.rpc('getConversation', { conversationId });
      document.getElementById('send').onclick = async () => {
        const message = document.querySelector('textarea').value;
        const result = await window.rpc('sendMessage', { conversationId, message });
        const region = document.getElementById('history');
        for (const row of result.messages) {
          const card = document.createElement('article');
          const role = document.createElement('h3');
          role.textContent = row.role;
          const content = document.createElement('fixture-text');
          content.textContent = row.content;
          card.append(role, content);
          region.append(card);
        }
        setTimeout(() => region.insertAdjacentHTML('beforeend', markup), 650);
      };
    }, { conversationId, markup: proposal('selected', update) });
    const result = await driver.runStep({ step: 'update-proposal', conversation_id: conversationId,
      selected_record_id: recordId, selected_name: name, selected_name_unique: true },
    { page, providerCalls: () => 0 }, observer);
    assert.equal(result.proposal_exact, true);
    assert.equal(result.chat_turn.proposal_action_id, actionId);
    return 'delayed-proposal-after-ready';
  });
}

async function sendAfterAction(browser, kind) {
  const cancelled = kind === 'after-cancel-direct';
  const split = kind.endsWith('-split');
  const buttonRead = ['after-confirm-bookkeeping-direct', 'after-confirm-bookkeeping-split',
    'unexplained-bookkeeping'].includes(kind);
  const disabledReload = kind.startsWith('disabled-reload-bookkeeping-');
  const bookkeepingAdded = buttonRead || disabledReload || ['page-reload-bookkeeping-direct', 'page-reload-bookkeeping-split',
    'changed-prior-history', 'changed-readback-proposal', 'unread-bookkeeping'].includes(kind);
  const automaticRead = kind === 'after-confirm-direct';
  const noAction = ['unexplained-terminal', 'unexplained-bookkeeping'].includes(kind);
  const pageRead = !noAction && !buttonRead && !automaticRead;
  const action = cancelled ? create : update;
  const method = cancelled ? 'cancelAction' : 'confirmAction';
  const status = cancelled ? 'cancelled' : 'applied';
  const terminal = { ...action, status };
  const nextMessage = 'Continue from this action.';
  const bookkeeping = { role: 'tool', content: JSON.stringify({ actionId, operation: 'update', status: 'applied', recordId }) };
  const durableMessages = [...completed, ...(bookkeepingAdded ? [bookkeeping] : [])];
  const pending = [...durableMessages, { role: 'user', content: nextMessage }];
  const reply = [...pending, { role: 'assistant', content: 'Following reply' }];
  const mutatedProposal = { ...terminal, newValues: { Status__c: 'Open' } };
  const result = kind === 'changed-prior-proposal' ? mutatedProposal : terminal;
  let durable = conversation(prior);
  const handle = (name, params) => {
    if (name === 'getConversation') return { payload: durable };
    if (name === method) {
      const messages = kind === 'changed-prior-history'
        ? [completed[0], { ...completed[1], content: 'Earlier reply was rewritten' }, ...durableMessages.slice(2)]
        : kind === 'unread-bookkeeping' ? completed : durableMessages;
      durable = conversation(messages, { actions: [kind === 'changed-readback-proposal' ? mutatedProposal : terminal] });
      return { payload: cancelled ? { actionId, status } : { actionId, status, operation: action.operation, recordId } };
    }
    if (name === 'beginMessage') return { payload: conversation(pending, {
      status: 'working', actions: [terminal], pending: { token, requestId: params.clientRequestId },
    }) };
    if (name === 'sendMessage' && params.message === message) {
      const payload = conversation(completed, { actions: [action] });
      durable = kind === 'unexplained-bookkeeping' ? { ...payload, messages: durableMessages } : payload;
      return { payload };
    }
    assert.ok(['sendMessage', 'executePendingMessage'].includes(name));
    return { payload: conversation(reply, { actions: [result] }) };
  };
  const markup = chatMarkup + (buttonRead || disabledReload
    ? '<button id="reload"' + (disabledReload ? ' disabled' : '') + '>Reload history</button>' : '');
  const mount = async ({ conversationId, proposalMarkup, split, method, label, message, automaticRead }) => {
    const history = document.getElementById('history');
    const send = document.getElementById('send');
    send.disabled = true;
    function render(value) {
      for (const card of history.querySelectorAll('[data-message-entry]')) card.remove();
      for (const row of value.messages) {
        const card = document.createElement('article');
        card.dataset.messageEntry = '';
        const heading = document.createElement('h3');
        heading.textContent = row.role;
        const content = document.createElement('fixture-text');
        content.textContent = row.content;
        card.append(heading, content);
        history.append(card);
      }
    }
    const read = async () => render(await window.rpc('getConversation', { conversationId }));
    await read();
    const reload = document.getElementById('reload');
    if (reload) reload.onclick = read;
    send.onclick = async () => {
      const text = document.querySelector('textarea').value;
      let value;
      if (split && text !== message) {
        const start = await window.rpc('beginMessage', {
          conversationId, message: text, clientRequestId: 'next-request',
        });
        value = await window.rpc('executePendingMessage', { conversationId, turnToken: start.pending.token });
      } else {
        value = await window.rpc('sendMessage', { conversationId, message: text });
      }
      render(value);
      if (text === message) {
        history.insertAdjacentHTML('beforeend', proposalMarkup);
        document.querySelector('#selected fixture-button[label="' + label + '"]').onclick = async event => {
          const card = document.getElementById('selected');
          const actionId = event.currentTarget.getAttribute('data-action-id');
          const outcome = await window.rpc(method, { actionId });
          if (automaticRead) await read();
          card.querySelector('[aria-label="Proposed change"]').remove();
          card.querySelector('[aria-label="Action status"]').textContent = outcome.status;
        };
      }
    };
    send.disabled = false;
  };
  const args = { conversationId, proposalMarkup: proposal('selected', action), split, method,
    label: cancelled ? 'Cancel' : 'Confirm', message, automaticRead };
  const start = `window.fixtureMounted = (${mount})(${JSON.stringify(args)});`;
  return withPage(browser, markup, handle, async (page, observer, calls) => {
    await page.evaluate(() => window.fixtureMounted);
    const first = await driver.writeMessage(page, observer, conversationId, message, 2200);
    if (!noAction) {
      await driver.performAction(page, observer, { name, nameUnique: true }, first.added.actions[0], status, {
        conversationId, timeoutMs: 2200, renderTimeoutMs: 1000, proposalTimeoutMs: 950,
      });
    }
    const reads = () => calls.filter(call => call.method === 'getConversation').length;
    assert.equal(reads(), automaticRead ? 2 : 1);
    const reload = page.getByRole('button', { name: 'Reload history', exact: true });
    if (disabledReload) {
      assert.equal(await reload.isVisible(), true);
      assert.equal(await reload.isEnabled(), false);
    } else if (pageRead) {
      assert.equal(await reload.count(), 0);
    }
    if (kind === 'unexplained-bookkeeping') {
      const cursor = observer.mark();
      await reload.click();
      await observer.waitFor('getConversation', () => true, 2200, cursor);
    }
    const run = () => driver.writeMessage(page, observer, conversationId, nextMessage, 2200);
    if (['unexplained-bookkeeping', 'changed-prior-history', 'changed-readback-proposal'].includes(kind)) {
      await assert.rejects(run, error => error.reason === 'ui-state-invalid');
      assert.ok(!calls.some(call => call.params.message === nextMessage));
    } else if (['changed-prior-proposal', 'unexplained-terminal', 'unread-bookkeeping'].includes(kind)) {
      await assert.rejects(run, error => error.reason === 'controller-proof-missing');
    } else {
      const second = await run();
      assert.equal(second.call.method, split ? 'executePendingMessage' : 'sendMessage');
      assert.deepEqual(second.conversation.actions, [terminal]);
      const before = createHash('sha256').update(JSON.stringify(durableMessages)).digest('hex');
      assert.equal(second.proof.before_history_sha256, before);
      assert.equal(second.proof.before_message_count, first.proof.final_message_count + Number(bookkeepingAdded));
      assert.deepEqual(calls.slice(2).map(call => call.method), [method, 'getConversation',
        ...(split ? ['beginMessage', 'executePendingMessage'] : ['sendMessage'])]);
      observer.assertTurnsAccounted();
    }
    assert.equal(reads(), !noAction || buttonRead ? 2 : 1);
    assert.equal(await page.evaluate(() => performance.getEntriesByType('navigation')[0].type),
      pageRead ? 'reload' : 'navigate');
    return kind;
  }, start);
}

async function connectionScenario(browser, kind) {
  const handle = method => ({ payload: method === 'testConnection' ? { status: 'ok' }
    : { status: 'ready', canConfigure: true, namedCredential: 'Grok_Chat_Model', model: 'grok-4.7' } });
  return withPage(browser, '<button>Test connection</button>', handle, async (page, observer, calls) => {
    await page.evaluate(async kind => {
      if (kind === 'uncorrelated-connection') await window.rpc('testConnection', {});
      document.querySelector('button').onclick = () => window.rpcBatch([
        ['testConnection', {}], [kind === 'duplicate-connection-in-batch' ? 'testConnection' : 'getSetup', {}],
      ]);
    }, kind);
    const run = () => driver.testConnection(page, observer, 2200);
    if (kind === 'one-connection-plus-setup') {
      await run();
      assert.deepEqual(calls.map(call => call.method), ['testConnection', 'getSetup']);
      assert.deepEqual(observer.projection().filter(call => call.ui_correlated).map(call => call.method), ['testConnection']);
    } else {
      await assert.rejects(run, error => error.reason === 'connection-failed');
      assert.equal(calls.length, kind === 'uncorrelated-connection' ? 1 : 2);
      assert.equal(observer.projection().filter(call => call.ui_correlated).length, 0);
    }
    return kind;
  });
}

async function main() {
  const { chromium } = browserTools.playwrightModule();
  const executablePath = browserTools.browserExecutable();
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}),
    args: ['--password-store=basic', '--use-mock-keychain', '--disable-features=DialMediaRouteProvider'] });
  try {
    const send = [];
    for (const kind of [...directSendCases, 'split', 'wrong-conversation', 'wrong-token', 'wrong-response-id', 'replay']) {
      send.push(await sendScenario(browser, kind));
    }
    for (const kind of ['after-confirm-direct', 'after-confirm-split', 'after-cancel-direct',
      'changed-prior-proposal', 'unexplained-terminal', 'after-confirm-bookkeeping-direct', 'after-confirm-bookkeeping-split',
      'page-reload-bookkeeping-direct', 'page-reload-bookkeeping-split',
      'disabled-reload-bookkeeping-direct', 'disabled-reload-bookkeeping-split',
      'unexplained-bookkeeping', 'changed-prior-history', 'changed-readback-proposal', 'unread-bookkeeping']) {
      send.push(await sendAfterAction(browser, kind));
    }
    const actions = [await delayedProposalAfterSend(browser)];
    for (const kind of ['delayed-status', 'wrong-status', 'nested-status', 'wrong-marker', 'wrong-rpc',
      'ambiguous-record', 'ambiguous-name', 'update-name', 'stale-name', 'nonunique-name', 'authoritative-id',
      'normalized-name', 'swapped-values', 'incidental-target', 'nested-action-details', 'nested-action-operation',
      'nested-labelledby-fields', 'nested-labelledby-controls', 'clipped-proposal-field',
      'ancestor-inset-clipped-proposal-field', 'fully-visible-inset-proposal-field', 'partially-clipped-proposal-extra',
      'foreign-action-clipped-extra', 'wrong-operation-prose', 'fieldset-and-labelled-operation',
      'delayed-card', 'delayed-controls', 'absent-controls',
      'wrong-result-record', 'retry-disabled', 'retry-removed', 'retry-enabled-replacement', 'retry-out-of-order',
      'retry-wrong-result', 'retry-rebound', 'retry-reparented',
      'retry-applied-then-rejected']) actions.push(await actionScenario(browser, kind));
    const connections = [];
    for (const kind of ['one-connection-plus-setup', 'duplicate-connection-in-batch', 'uncorrelated-connection']) {
      connections.push(await connectionScenario(browser, kind));
    }
    process.stdout.write(JSON.stringify({ status: 'PASS', send, actions, connections, browser: browser.version() }) + '\n');
  } finally {
    await browser.close();
  }
}

main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1; });
