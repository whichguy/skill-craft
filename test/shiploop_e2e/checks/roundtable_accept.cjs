/* Held-out browser observations for Roundtable, not a general UI grader. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const [base, mode, output] = process.argv.slice(2);
const report = {base, mode, observed: false, complete: false, checks: [], captures: [], measurements: []};
let browser, page;
fs.mkdirSync(output, {recursive: true});

function check(id, condition, note = '') {
  report.checks.push({id, pass: Boolean(condition), note});
  if (!condition) { const error = new Error(id + ': ' + note); error.assertion = true; throw error; }
}
async function settle() {
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}
async function visible(locator, id) {
  check(id, await locator.count() === 1 && await locator.isVisible(), 'one visible accessible target');
  return locator;
}
const button = name => page.getByRole('button', {name, exact: typeof name === 'string'});
const conversation = () => page.getByRole('region', {name: 'Conversation', exact: true});
const message = () => page.getByRole('textbox', {name: 'Message', exact: true});
const articles = () => conversation().getByRole('article');
const ownMessages = () => conversation().getByRole('article', {name:'Message from Maya',exact:true});
const escapedLines = text => text.trim().split(/\r?\n/).map(value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
const textQuery = text => new RegExp(escapedLines(text).join('\\s*'));
async function click(locator, id) {
  await visible(locator, id);
  check(id + '-enabled', await locator.isEnabled());
  await locator.click();
  await settle();
}
async function send(text) {
  await visible(message(), 'message-input');
  await message().fill(text);
  await click(button('Send'), 'send-control');
}
async function shownText(text, id, scope = conversation()) {
  const target = scope.getByRole('article').filter({hasText:textQuery(text)});
  await target.first().waitFor({state:'visible'});
  await visible(target, id);
  // Playwright text queries normalize whitespace even in exact mode. Locate
  // semantically, then check rendered newlines rather than mistaking lookup for
  // preservation. Admit <br> and paragraph markup; extra paragraph spacing is
  // layout, while collapsing the required line boundary remains a defect.
  if (text.includes('\n')) check(id + '-line-breaks',
    new RegExp(escapedLines(text).join('\\n+')).test((await target.innerText()).replace(/\r\n/g, '\n')));
}
async function snapshot(label) {
  const file = path.join(output, label + '.png');
  await page.screenshot({path: file, fullPage: true});
  report.captures.push({label, file, viewport: page.viewportSize()});
  const targets = {
    conversation: await conversation().count() === 1 ? await conversation().elementHandle() : null,
    composer: await message().count() === 1 ? await message().elementHandle() : null,
  };
  const measurement = await page.evaluate(targets => {
    const box = element => {
      if (!element) return null;
      const r = element.getBoundingClientRect(), s = getComputedStyle(element);
      const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
      const c = canvas.getContext('2d');
      const rgba = color => { c.clearRect(0, 0, 1, 1); c.fillStyle = color; c.fillRect(0, 0, 1, 1); return [...c.getImageData(0, 0, 1, 1).data]; };
      return {x:r.x, y:r.y, width:r.width, height:r.height, background:s.backgroundColor,
        background_rgba:rgba(s.backgroundColor), color:s.color, color_rgba:rgba(s.color),
        font:s.fontFamily, fontSize:s.fontSize, lineHeight:s.lineHeight,
        radius:s.borderRadius, padding:s.padding, gap:s.gap};
    };
    return {viewport:{width:innerWidth,height:innerHeight}, scrollWidth:document.documentElement.scrollWidth,
      body:box(document.body), conversation:box(targets.conversation),
      composer:box(targets.composer), activeTag:document.activeElement?.tagName,
      themeControls:[...document.querySelectorAll('button,[role="button"]')].map(e => e.getAttribute('aria-label') || e.textContent).filter(t => /appearance/i.test(t))};
  }, targets);
  report.measurements.push({label, ...measurement});
}
async function appearanceValues() {
  // Observe finite transitions reaching their actual endpoint. Do not impose a
  // sleep/deadline or wait on unrelated perpetual animations such as spinners.
  await page.evaluate(() => Promise.all(document.getAnimations().filter(animation =>
    animation.playState === 'running' && Number.isFinite(animation.effect?.getComputedTiming().endTime)
  ).map(animation => animation.finished.catch(() => {}))));
  const values = [];
  for (const locator of [page.locator('body'), conversation(), message()]) {
    values.push(await locator.evaluate(e => {
      const s = getComputedStyle(e); return [s.backgroundColor,s.color,s.backgroundImage];
    }));
  }
  return JSON.stringify(values);
}
async function geometry(label) {
  await message().scrollIntoViewIfNeeded();
  await settle();
  const box = await message().boundingBox(), viewport = page.viewportSize();
  check(label + '-composer-reachable', box && box.width > 0 && box.height > 0 && box.x >= -1 && box.y >= -1 &&
    box.x + box.width <= viewport.width + 1 && box.y + box.height <= viewport.height + 1);
  const width = await page.evaluate(() => document.documentElement.scrollWidth);
  check(label + '-no-page-overflow', width <= viewport.width + 1, String(width));
  await snapshot(label);
}

// A real response is fetched before holding delivery. Injected failure is the
// only response we invent. No timers decide when a reply completes.
async function agentGate({fail = false} = {}) {
  let release, handled, ready;
  const hold = new Promise(resolve => { release = resolve; });
  const finished = new Promise(resolve => { handled = resolve; });
  const prepared = new Promise(resolve => { ready = resolve; });
  const state = {requests: [], response: null, aborted: false};
  const handler = async route => {
    state.requests.push(route.request().postDataJSON());
    try {
      if (!fail) {
        state.response = await route.fetch({timeout:0});
        state.body = await state.response.json();
      }
      ready();
      await hold;
      if (fail) await route.fulfill({status:503, contentType:'application/json', body:JSON.stringify({error:'Local agent unavailable'})});
      else await route.fulfill({response:state.response});
    } catch (error) { state.aborted = true; state.error = String(error); ready(); }
    finally { handled(); }
  };
  await page.route('**/api/agent', handler, {times:1});
  return {
    state,
    async pending(id) {
      await prepared;
      check(id + '-request', state.requests.length === 1, JSON.stringify(state.requests));
      if (!fail) check(id + '-real-response', state.response?.ok() && typeof state.body?.text === 'string', state.error || '');
      if (!fail && state.requests[0]?.text?.startsWith('@Scribe plan')) check(id + '-plan-contract',
        state.body.text === 'Next steps\n- Confirm scope\n- Assign an owner\n- Review delivery');
      await snapshot(id + '-pending');
    },
    async finish() { release(); await finished; await settle(); },
  };
}

async function roomControl(name) {
  let control = button(new RegExp('^' + name + '(?:,|$)'));
  if (!await control.isVisible()) await click(button('Rooms'), 'open-rooms');
  return button(new RegExp('^' + name + '(?:,|$)'));
}
async function chooseRoom(name) {
  const control = await roomControl(name);
  await click(control, 'room-' + name.replaceAll(' ', '-'));
}
async function backgroundActivity(room, completed = false) {
  const status = page.getByRole('status',{name:'Room activity',exact:true}).filter({hasText:room});
  await (completed ? status.filter({hasText:/completed/i}) : status).waitFor({state:'visible'});
}

async function conversationChecks() {
  check('title', /\bRoundtable\b/.test(await page.title()));
  await visible(conversation(), 'conversation-region');
  check('seeded-messages', await articles().count() >= 3);
  for (const author of ['Maya', 'Theo', 'Scribe']) {
    check('author-' + author, (await articles().allTextContents()).some(t => t.includes(author)));
  }
  check('agent-identified', /demo|agent/i.test((await articles().allTextContents()).find(t => t.includes('Scribe')) || ''));
  const count = await articles().count();
  await message().fill('  \n  ');
  if (await button('Send').isEnabled()) await click(button('Send'), 'blank-send');
  check('blank-ignored', await articles().count() === count);
  const text = 'First launch item\nKeep the second line';
  await send(text);
  await shownText(text, 'multiline-sent');
  check('draft-cleared', await message().inputValue() === '');
  await message().fill('Keyboard first');
  await message().press('Shift+Enter');
  await message().press('K');
  check('shift-enter-newline', (await message().inputValue()).includes('\n'));
  const keyboardText = await message().inputValue();
  await message().press('Enter'); await settle();
  await shownText(keyboardText, 'enter-sends');
  const gate = await agentGate();
  const prompt = '@Scribe outline our launch';
  await send(prompt); await gate.pending('agent');
  await page.getByRole('status').filter({hasText:/\S/}).first().waitFor({state:'visible'});
  check('working-visible', (await page.getByRole('status').allTextContents()).some(text => text.trim().length > 0));
  await gate.finish();
  await shownText('Demo reply: ' + prompt, 'agent-replied');

  const failure = await agentGate({fail:true});
  const failedPrompt = '@Scribe summarize the launch';
  await send(failedPrompt); await failure.pending('failure'); await failure.finish();
  await page.getByRole('alert').first().waitFor({state:'visible'});
  check('error-visible', await page.getByRole('alert').count() > 0);
  await snapshot('recoverable-error');
  await click(button('Retry Scribe'), 'retry-scribe');
  // The ordinary server response remains real, rather than fulfilled by a mock.
  await shownText('Demo reply: ' + failedPrompt, 'retry-replied');
  check('retry-no-duplicate-person', await ownMessages().filter({hasText:textQuery(failedPrompt)}).count() === 1);
  await send('Long release note: ' + 'requirements-and-review-'.repeat(20) + '\n' + 'A paragraph of project context. '.repeat(20));

  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({width, height:width === 1440 ? 1000 : 844});
    await geometry('light-' + width);
  }
  const lightValues = await appearanceValues();
  await click(button('Use dark appearance'), 'dark-control');
  await visible(button('Use light appearance'), 'dark-active-control');
  check('appearance-values-changed', await appearanceValues() !== lightValues,
    'primary surface/ink values change; dark visual quality is reviewed separately');
  for (const width of [390, 1440]) {
    await page.setViewportSize({width,height:width === 1440 ? 1000 : 844});
    await geometry('dark-' + width);
  }
  await page.setViewportSize({width:320,height:844}); await settle();
  await click(button('Use light appearance'), 'restore-light');
  check('light-values-restored', await appearanceValues() === lightValues);
  await message().focus();
  await snapshot('keyboard-focus');
  check('composer-focus', await message().evaluate(e => document.activeElement === e));
  await page.goto(base + '/?empty=1', {waitUntil:'load'}); await settle();
  check('empty-conversation', await articles().count() === 0);
  check('empty-guidance', (await conversation().innerText()).trim().length > 0);
  await snapshot('empty-guidance');
  await send('Hello from an empty room');
  await shownText('Hello from an empty room', 'empty-can-send');
  await snapshot('empty-after-send');
}

async function roomChecks() {
  await chooseRoom('Launch plan');
  await message().fill('launch draft');
  await chooseRoom('Design review');
  check('design-own-draft', await message().inputValue() === '');
  await message().fill('design draft');
  await chooseRoom('Launch plan');
  check('launch-draft-restored', await message().inputValue() === 'launch draft');
  await chooseRoom('Design review');
  check('design-draft-restored', await message().inputValue() === 'design draft');
  await chooseRoom('Launch plan');
  const gate = await agentGate();
  const text = '@Scribe keep this reply in Launch plan';
  await send(text); await gate.pending('room-origin');
  await chooseRoom('Design review'); await gate.finish();
  await backgroundActivity('Launch plan');
  check('reply-not-in-wrong-room', await articles().filter({hasText:textQuery('Demo reply: ' + text)}).count() === 0);
  check('other-draft-untouched', await message().inputValue() === 'design draft');
  await roomControl('Launch plan');
  await visible(button('Launch plan, 1 unread'), 'inactive-unread');
  await chooseRoom('Launch plan');
  await shownText('Demo reply: ' + text, 'origin-reply');
  await roomControl('Launch plan');
  await visible(button('Launch plan'), 'unread-cleared');
  await chooseRoom('Launch plan');
  check('sent-room-draft-cleared', await message().inputValue() === '');
  await message().fill('draft survives narrow navigation');
  await page.setViewportSize({width:390,height:844}); await settle();
  await chooseRoom('Support');
  check('support-empty', await articles().count() === 0);
  await chooseRoom('Launch plan');
  check('narrow-draft-preserved', await message().inputValue() === 'draft survives narrow navigation');
  await geometry('rooms-narrow');
  await page.setViewportSize({width:1440,height:1000}); await settle();
  await geometry('rooms-wide');
}

const tasks = () => page.getByRole('article', {name:/^Agent task/});
const tasksInState = status => tasks().filter({has:page.getByRole('status', {name:'Task status',exact:true})
  .filter({hasText:new RegExp('^\\s*' + status + '\\s*$','i')})});
async function taskState(status, id, count = 1, wait = true) {
  const cards = tasksInState(status);
  if (wait) await cards.nth(count - 1).waitFor({state:'visible'});
  check(id, await cards.count() === count, 'expected ' + count + ' ' + status + ' attempt(s)');
  return cards;
}
async function agentWorkChecks() {
  await chooseRoom('Launch plan');
  const cancelled = await agentGate();
  await send('@Scribe plan prepare the launch'); await cancelled.pending('cancel');
  let card = await taskState('running','task-running');
  await visible(card, 'task-card');
  await click(card.getByRole('button',{name:'Cancel task',exact:true}), 'cancel-task');
  await taskState('cancelled','task-cancelled');
  await cancelled.finish();

  const failed = await agentGate({fail:true});
  const text = '@Scribe plan organize a review';
  await send(text); await failed.pending('task-failure'); await failed.finish();
  card = await taskState('failed','task-failed');
  const beforeRetry = await tasks().count();
  const retry = await agentGate();
  await click(card.getByRole('button',{name:'Retry task',exact:true}), 'retry-task');
  await retry.pending('retry');
  await taskState('running','retry-running');
  check('retry-new-attempt', await tasks().count() === beforeRetry + 1);
  await taskState('failed','failed-attempt-retained');
  await retry.finish();
  await tasksInState('completed').first().waitFor({state:'visible'});
  await taskState('cancelled','late-response-stays-cancelled',1,false);
  card = await taskState('completed','retry-completed');
  check('retry-one-person-request', await ownMessages().filter({hasText:textQuery(text)}).count() === 1);
  await message().fill('draft while reviewing a result');
  const open = card.getByRole('button',{name:'Open result',exact:true});
  await click(open,'open-result');
  const result = page.getByRole('region',{name:'Agent result',exact:true});
  await visible(result,'result-region');
  const resultText = await result.innerText();
  check('useful-result', ['Next steps','Confirm scope','Assign an owner','Review delivery'].every(text => resultText.includes(text)));
  await snapshot('result-wide');
  await page.setViewportSize({width:390,height:844}); await settle();
  await snapshot('result-narrow');
  await click(button('Close result'),'close-result');
  check('result-focus-return', await open.evaluate(e => document.activeElement === e));
  check('result-draft-retained', await message().inputValue() === 'draft while reviewing a result');
  await geometry('result-closed-narrow');

  await page.setViewportSize({width:1440,height:1000}); await settle();
  const origin = await agentGate();
  await send('@Scribe plan another release'); await origin.pending('task-origin');
  await chooseRoom('Design review'); await message().fill('other room work'); await origin.finish();
  await backgroundActivity('Launch plan', true);
  check('task-no-wrong-room', await tasks().count() === 0);
  check('task-keeps-other-draft', await message().inputValue() === 'other room work');
  check('task-keeps-focus', await message().evaluate(e => document.activeElement === e));
  await roomControl('Launch plan');
  await visible(button('Launch plan, 1 unread'),'task-unread');
  await chooseRoom('Launch plan');
  // Recheck after the remaining asynchronous workflow, not immediately after
  // network delivery. This is a scenario observation, not proof about all future time.
  card = await taskState('cancelled','late-response-stays-cancelled',1,false);
  check('cancel-no-result', await card.getByRole('button',{name:'Open result',exact:true}).count() === 0);
  await taskState('completed','task-completed-in-origin',2);
  await snapshot('jobs-wide');
}

(async () => {
  let playwright;
  try { playwright = require(process.env.PLAYWRIGHT_NODE_PATH || 'playwright'); }
  catch (error) { report.error = 'Playwright unavailable: ' + error; return; }
  try {
    browser = await playwright.chromium.launch({headless:true,timeout:0,
      ...(process.env.BROWSER_EXECUTABLE_PATH ? {executablePath:process.env.BROWSER_EXECUTABLE_PATH} : {})});
    report.browser = browser.version();
  } catch (error) { report.error = 'Browser unavailable: ' + error; return; }
  const context = await browser.newContext({viewport:{width:1440,height:1000},colorScheme:'light',reducedMotion:'reduce'});
  page = await context.newPage();
  page.setDefaultTimeout(0); page.setDefaultNavigationTimeout(0);
  const errors = []; page.on('pageerror', error => errors.push(String(error)));
  await page.goto(base + '/', {waitUntil:'load'}); await settle();
  report.observed = true;
  const checks = {'conversation':conversationChecks, 'rooms':roomChecks, 'agent-work':agentWorkChecks};
  if (!checks[mode]) throw new Error('Unknown mode: ' + mode);
  await checks[mode]();
  check('no-page-errors', errors.length === 0, errors.join('\n'));
  // OS preference is a separate observation; it does not activate an explicit
  // product theme by assumption and does not establish real-device behavior.
  const darkPreference = await browser.newContext({viewport:{width:390,height:844},colorScheme:'dark',reducedMotion:'reduce'});
  page = await darkPreference.newPage(); page.setDefaultTimeout(0); page.setDefaultNavigationTimeout(0);
  await page.goto(base + '/', {waitUntil:'load'}); await settle();
  await snapshot('first-paint-os-dark');
  report.complete = true;
})().catch(async error => {
  report.error = String(error);
  if (!error.assertion && report.observed) report.checks.push({id:'browser-execution',pass:false,note:String(error)});
  if (page && report.observed) { try { await snapshot('failure'); } catch {} }
}).finally(async () => {
  if (browser) await browser.close();
  fs.writeFileSync(path.join(output,'observation.json'), JSON.stringify(report,null,2) + '\n');
  process.exitCode = report.observed && report.complete && report.checks.every(row => row.pass) ? 0 : 1;
});
