/* Held-out browser checks for the grokbot-local scenario. No model session is shown this file.
 *
 *   PLAYWRIGHT_NODE_PATH=<playwright module> BROWSER_EXECUTABLE_PATH=<chromium> \
 *     node grokbot_accept.cjs PRODUCT OUTPUT
 *
 * PRODUCT is a built copy of the app; OUTPUT receives observation.json and the server logs. The script starts and
 * stops `node server.js` itself, each mode on a free port with an empty data folder of its own, and finds everything
 * by role and accessible name, as REQUEST.md states them. Every check is tried and recorded: one failing does not stop
 * the others, though checks in one mode share that mode's state. It exits 0 only when every check passes.
 *
 * Calibration, 2026-11-20, on the bare arm's build and before any other arm had a result (the journal lists each
 * correction with what was observed):
 *   1. Setup is looked for on the first screen and, when it is not there, after continuing as a person. The request
 *      says the first screen offers the Continue as buttons and that Setup is shown while no token is saved; it does
 *      not say which comes first, and the first version assumed Setup did.
 *   2. A good token counts as accepted when a first message then gets a reply. The first version waited for the
 *      Continue as buttons to appear after saving, which is assumption 1 again.
 *   3. After a restart Setup must be absent on the first screen and after continuing (stricter than before for an
 *      app that shows people first).
 *   4. After New conversation the check waits for the conversation to show no messages, which is what it is named
 *      for, before it writes. The first version wrote within milliseconds of the click.
 *   5. `send` pauses 300 ms before it writes, the pause `openBot` always had: a person does not send a message
 *      within milliseconds of their last click, and the request states no such speed.
 * Calibration on the Ratchet arm's first build, the same evening, before the ShipLoop arm's result had been read:
 *   6. `signIn` waits until the first screen has drawn its Continue as button, or the Message box, before it decides
 *      whether to click. The first version looked the instant the page had loaded; a build that draws the people
 *      after fetching them was found without the button and never signed in.
 *   7. After a restart, the check that Setup is absent waits half a second for the first screen to draw before it
 *      looks (the same instant-of-load fault, here in the lenient direction).
 *   8. The account of what happened while away is read on coming back (for up to three seconds after signing in),
 *      which is when the request says it tells me. The first version read it only after the task had gone on to
 *      finish in front of the person, and a build whose account follows the tasks live had by then moved on.
 * Calibration on the Sonnet bare arm's build:
 *   9. After a cancel, the step that was in flight may finish and be shown (one more "Done:" within three seconds);
 *      after that nothing more may finish. The request speaks of "what can still be stopped and what has already
 *      happened"; the first version allowed no step at all after the status read Cancelled, and a build that lets
 *      the step in flight finish, and labels it "in progress" until it has, failed for it.
 * Calibration on the ShipLoop arm's build:
 *  10. Waiting for a new conversation to be empty counts messages only; that build draws task cards inside the
 *      Conversation region (the second yardstick's correction E, where it was found).
 * Calibration on the Ratchet arm's first build, second look:
 *  11. Coming back after the page was closed happens in the same browser (a new page of the same context), not in
 *      a new one. That build keeps what a person has already seen with the browser, and in a brand-new browser it
 *      had nothing to call "finished while you were away"; its own test of the same sentence, which reopens a tab,
 *      passes. The request speaks of coming back, not of arriving on another machine.
 */
'use strict';
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');
const { spawn } = require('node:child_process');

const [productArg, outputArg] = process.argv.slice(2);
const product = path.resolve(productArg);
const output = path.resolve(outputArg);
const TOKEN = 'sk-local-Yardstick00017';
const ONLY = (process.env.GROKBOT_MODES || 'setup,core,tasks,layout,tests').split(',');
const report = { product, started: new Date().toISOString(), observed: false, complete: false, checks: [], notes: [] };
fs.mkdirSync(output, { recursive: true });
let browser;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
function expect(condition, note) {
  if (!condition) throw new Error(note);
}
async function attempt(id, run, limit = 60000) {
  let timer;
  try {
    await Promise.race([run(), new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`no result within ${limit / 1000} s`)), limit); })]);
    report.checks.push({ id, pass: true });
  } catch (error) {
    report.checks.push({ id, pass: false, note: String(error && error.message ? error.message : error).split('\n')[0].slice(0, 300) });
  } finally {
    clearTimeout(timer);
  }
}

// ---------------------------------------------------------------- the server under test
function freePort() {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => { const { port } = probe.address(); probe.close(() => resolve(port)); });
  });
}
async function startServer(name, { token = true, data } = {}) {
  const port = await freePort();
  const dataDir = data || path.join(output, `data-${name}`);
  fs.mkdirSync(dataDir, { recursive: true });
  const env = { ...process.env, PORT: String(port), DATA_DIR: dataDir, STANDIN_SLOW_MS: '1500', STANDIN_STEP_MS: '700' };
  delete env.PROVIDER_TOKEN;
  if (token) env.PROVIDER_TOKEN = TOKEN;
  const log = fs.openSync(path.join(output, `server-${name}.log`), 'a');
  const child = spawn('node', ['server.js'], { cwd: product, env, detached: true, stdio: ['ignore', log, log] });
  const base = `http://127.0.0.1:${port}`;
  let up = false;
  for (let tries = 0; tries < 80 && !up; tries += 1) {
    if (child.exitCode !== null) break;
    try { const answer = await fetch(base + '/'); up = answer.status < 500; } catch { await sleep(250); }
  }
  const stop = async () => {
    if (child.exitCode === null) {
      try { process.kill(-child.pid, 'SIGTERM'); } catch { /* already gone */ }
      for (let tries = 0; tries < 20 && child.exitCode === null; tries += 1) await sleep(100);
      if (child.exitCode === null) { try { process.kill(-child.pid, 'SIGKILL'); } catch { /* already gone */ } }
    }
    fs.closeSync(log);
  };
  if (!up) { await stop(); throw new Error(`node server.js did not answer on PORT=${port} (see server-${name}.log)`); }
  return { base, dataDir, stop };
}

// ---------------------------------------------------------------- finding things, as the request names them
const button = (scope, name) => scope.getByRole('button', { name, exact: true });
const region = (page, name) => page.getByRole('region', { name, exact: true });
const navigation = (page, name) => page.getByRole('navigation', { name, exact: true });
const textbox = (scope, name) => scope.getByRole('textbox', { name, exact: true });
const conversation = (page) => region(page, 'Conversation');
const messages = (page, who) => conversation(page).getByRole('article', { name: `Message from ${who}`, exact: true });
const task = (page, title) => page.getByRole('article', { name: `Task: ${title}`, exact: true });
const taskStatus = (page, title) => task(page, title).getByRole('status', { name: 'Task status', exact: true });

async function newPage(width = 1440, height = 1000, sameBrowser = null) {
  const context = sameBrowser || await browser.newContext({ viewport: { width, height }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  page.setDefaultTimeout(8000);
  page.setDefaultNavigationTimeout(15000);
  return page;
}
async function signIn(page, base, who) {
  await page.goto(base + '/', { waitUntil: 'load' });
  const enter = button(page, `Continue as ${who}`);
  const box = textbox(page, 'Message');
  await enter.or(box).first().waitFor({ state: 'visible' }); // the first screen may be drawn after the page has loaded (calibration 6)
  if (await enter.isVisible()) await enter.click();
  await box.waitFor({ state: 'visible' });
}
async function send(page, text) {
  await page.waitForTimeout(300); // a person's pace after their last click (calibration 5)
  await textbox(page, 'Message').fill(text);
  await button(page, 'Send').click();
}
async function reply(page, bot, text, limit = 12000) {
  await messages(page, bot).filter({ hasText: text }).last().waitFor({ state: 'visible', timeout: limit });
}
async function ask(page, bot, text, answer, limit) {
  await send(page, text);
  await reply(page, bot, answer, limit);
}
async function isCurrent(locator) {
  const value = await locator.getAttribute('aria-current');
  return value !== null && value !== 'false';
}
async function openBot(page, name) {
  await button(navigation(page, 'Bots'), name).click();
  await page.waitForTimeout(300);
}
async function waitStatus(page, title, wanted, limit) {
  const pattern = new RegExp(wanted.join('|'));
  await taskStatus(page, title).filter({ hasText: pattern }).waitFor({ state: 'visible', timeout: limit });
  return (await taskStatus(page, title).innerText()).trim();
}
async function doneCount(page, title, text = 'Done:') {
  return ((await task(page, title).innerText()).split(text).length - 1);
}

// ---------------------------------------------------------------- setup and the secret
async function setupMode() {
  let server = await startServer('setup', { token: false });
  const page = await newPage();
  const bodies = [];
  page.on('response', async (answer) => { try { bodies.push(await answer.text()); } catch { /* a body that cannot be read */ } });
  await page.goto(server.base + '/', { waitUntil: 'load' });
  await attempt('setup-is-shown-without-a-token', async () => {
    const setup = region(page, 'Setup');
    try {
      await setup.waitFor({ state: 'visible', timeout: 2500 });
    } catch { // not on the first screen: the request lets the people come first (calibration 1)
      const enter = button(page, 'Continue as Maya');
      if (await enter.count()) await enter.click();
      await setup.waitFor({ state: 'visible' });
    }
    await textbox(page, 'Provider token').waitFor({ state: 'visible' });
  });
  await attempt('setup-refuses-a-wrong-token-and-lets-me-retry', async () => {
    await textbox(page, 'Provider token').fill('not-a-token');
    await button(page, 'Save token').click();
    await page.getByRole('alert').first().waitFor({ state: 'visible' });
    expect(await region(page, 'Setup').isVisible(), 'the Setup region went away after a refused token');
  });
  await attempt('setup-accepts-a-good-token', async () => {
    await textbox(page, 'Provider token').fill(TOKEN);
    await button(page, 'Save token').click();
    // accepted means the app can now be used: the people are offered, or the person already chosen can write
    const enter = button(page, 'Continue as Maya');
    const box = textbox(page, 'Message');
    await region(page, 'Setup').waitFor({ state: 'hidden', timeout: 4000 }).catch(() => {});
    await enter.or(box).first().waitFor({ state: 'visible' });
    if (await enter.isVisible()) await enter.click();
    await ask(page, 'Assistant', 'first words', 'You said: "first words"'); // calibration 2
  });
  await attempt('the-token-is-never-shown-again', async () => {
    await signIn(page, server.base, 'Maya');
    await ask(page, 'Assistant', 'hello after setup', 'You said: "hello after setup"');
    const front = await (await fetch(server.base + '/')).text();
    const seen = [await page.content(), front, ...bodies].join('\n');
    expect(!seen.includes(TOKEN), 'the provider token appears in a page or a response');
  });
  await server.stop();
  server = await startServer('setup', { token: false, data: server.dataDir });
  await attempt('the-saved-token-survives-a-restart', async () => {
    const again = await newPage();
    await again.goto(server.base + '/', { waitUntil: 'load' });
    await again.waitForTimeout(500); // let the first screen draw before looking (calibration 7)
    expect(await region(again, 'Setup').count() === 0, 'Setup is shown again after a restart although a token was saved');
    await signIn(again, server.base, 'Maya');
    await again.waitForTimeout(500);
    expect(await region(again, 'Setup').count() === 0, 'Setup is shown after continuing as a person although a token was saved'); // calibration 3
    await ask(again, 'Assistant', 'ping', 'You said: "ping"');
    await again.context().close();
  });
  await page.context().close();
  await server.stop();
}

// ---------------------------------------------------------------- conversation, bots, memory, records, changes
async function coreMode() {
  let server = await startServer('core');
  let page = await newPage();
  await attempt('continue-as-a-person', async () => { await signIn(page, server.base, 'Maya'); });
  await attempt('a-new-person-starts-with-a-bot-named-assistant', async () => {
    const bot = button(navigation(page, 'Bots'), 'Assistant');
    await bot.waitFor({ state: 'visible' });
    expect(await isCurrent(bot), 'the Assistant bot is not marked as current');
  });
  await attempt('a-message-gets-a-reply', async () => {
    await send(page, 'hello');
    await messages(page, 'Maya').filter({ hasText: 'hello' }).first().waitFor({ state: 'visible' });
    await reply(page, 'Assistant', 'You said: "hello"');
  });
  await attempt('a-follow-up-carries-the-conversation', async () => {
    await ask(page, 'Assistant', 'again', '2 message(s)');
    await ask(page, 'Assistant', 'what did I ask first', 'You first asked: "hello"');
  });
  await attempt('enter-sends-and-shift-enter-makes-a-new-line', async () => {
    const box = textbox(page, 'Message');
    await box.click();
    await page.keyboard.type('line one');
    await page.keyboard.press('Shift+Enter');
    await page.keyboard.type('line two');
    await page.keyboard.press('Enter');
    await reply(page, 'Assistant', 'line two');
    expect((await messages(page, 'Maya').filter({ hasText: 'line one' }).last().innerText()).includes('line two'), 'the two lines were not sent as one message');
    expect((await box.inputValue()) === '', 'the message box was not cleared after sending');
  });
  await attempt('a-reply-on-its-way-shows-a-status', async () => {
    await send(page, '[slow] slow question');
    await page.getByRole('status').filter({ hasText: /\S/ }).first().waitFor({ state: 'visible', timeout: 1300 });
    await reply(page, 'Assistant', 'You said: "slow question"');
  });
  await attempt('a-failed-reply-is-retried-without-a-second-message', async () => {
    await send(page, '[fail once] flaky question');
    await page.getByRole('alert').first().waitFor({ state: 'visible' });
    await button(page, 'Retry').click();
    await reply(page, 'Assistant', 'You said: "flaky question"');
    expect(await messages(page, 'Maya').filter({ hasText: 'flaky question' }).count() === 1, 'the message appears more than once after a retry');
  });
  await attempt('an-answer-comes-from-a-record-i-may-read', async () => {
    await ask(page, 'Assistant', 'what is the total of ORD-1002', 'The total of ORD-1002 is 80');
  });
  await attempt('a-clarifying-question-leads-to-the-exact-proposal', async () => {
    await ask(page, 'Assistant', 'update ORD-1004', 'Which field of ORD-1004');
    await send(page, 'the status to closed');
    const proposal = region(page, 'Proposed changes');
    await proposal.waitFor({ state: 'visible' });
    const text = await proposal.innerText();
    expect(text.includes('ORD-1004') && text.includes('status') && text.includes('closed'), 'the proposal does not state the change: ' + text.slice(0, 120));
  });
  await attempt('rejecting-a-proposal-writes-nothing', async () => {
    await button(page, 'Reject changes').click();
    await region(page, 'Change result').waitFor({ state: 'visible' });
    await ask(page, 'Assistant', 'what is the status of ORD-1004', 'The status of ORD-1004 is open');
  });
  await attempt('nothing-is-written-before-i-confirm', async () => {
    await ask(page, 'Assistant', 'set the status of ORD-1001 to closed', 'I propose one change');
    await region(page, 'Proposed changes').waitFor({ state: 'visible' });
    const other = await newPage();
    await signIn(other, server.base, 'Theo');
    await ask(other, 'Assistant', 'what is the status of ORD-1001', 'The status of ORD-1001 is open');
    await other.context().close();
  });
  await attempt('confirming-applies-the-change', async () => {
    await button(page, 'Confirm changes').click();
    await region(page, 'Change result').waitFor({ state: 'visible' });
    await ask(page, 'Assistant', 'what is the status of ORD-1001', 'The status of ORD-1001 is closed');
  });
  await attempt('confirming-twice-and-reloading-applies-it-once', async () => {
    await ask(page, 'Assistant', 'create an order for Zed Ltd totalling 70', 'I propose creating one order');
    const confirm = button(page, 'Confirm changes');
    await confirm.click();
    try { await confirm.click({ timeout: 400 }); } catch { /* the button may be gone after the first click, as it should */ }
    await page.reload({ waitUntil: 'load' });
    await textbox(page, 'Message').waitFor({ state: 'visible' });
    await ask(page, 'Assistant', 'how many orders can you see', 'I can see 4 order record(s)');
  });
  await attempt('a-new-bot-can-be-named-and-opens', async () => {
    await button(page, 'New bot').click();
    await textbox(page, 'Bot name').fill('Planner');
    await button(page, 'Save bot name').click();
    const bot = button(navigation(page, 'Bots'), 'Planner');
    await bot.waitFor({ state: 'visible' });
    expect(await isCurrent(bot), 'the new bot is not the open one');
  });
  await attempt('each-bot-has-its-own-conversation', async () => {
    await ask(page, 'Planner', 'hello planner', '(Planner has 1 message(s)');
  });
  await attempt('a-reload-returns-to-the-same-bot-and-conversation', async () => {
    await page.reload({ waitUntil: 'load' });
    await textbox(page, 'Message').waitFor({ state: 'visible' });
    expect(await isCurrent(button(navigation(page, 'Bots'), 'Planner')), 'after a reload the open bot is not Planner');
    await messages(page, 'Maya').filter({ hasText: 'hello planner' }).first().waitFor({ state: 'visible' });
  });
  await attempt('a-second-conversation-starts-empty-and-both-are-listed', async () => {
    await button(page, 'New conversation').click();
    const shownMessages = () => conversation(page).getByRole('article', { name: /^Message from / }).count(); // messages only (calibration 10)
    let shown = await shownMessages();
    for (let tries = 0; tries < 40 && shown > 0; tries += 1) { // wait for the empty conversation to be on screen (calibration 4)
      await page.waitForTimeout(200);
      shown = await shownMessages();
    }
    expect(shown === 0, `the new conversation still shows ${shown} message(s) after 8 s`);
    await ask(page, 'Planner', 'fresh start', '(Planner has 1 message(s)');
    expect(await navigation(page, 'Conversations').getByRole('button').count() >= 2, 'the Conversations navigation lists fewer than two conversations');
  });
  const memory = () => region(page, 'Memory');
  await attempt('what-a-bot-remembers-can-be-read', async () => {
    await ask(page, 'Planner', 'remember that I like tea', "I'll remember that I like tea");
    await memory().getByRole('listitem').filter({ hasText: 'I like tea' }).first().waitFor({ state: 'visible' });
  });
  await attempt('one-bot-does-not-know-what-another-remembers', async () => {
    await openBot(page, 'Assistant');
    expect(await memory().getByRole('listitem').filter({ hasText: 'I like tea' }).count() === 0, "the Assistant bot's Memory shows Planner's fact");
    await ask(page, 'Assistant', 'what do you remember', "I don't remember anything about you yet");
    await openBot(page, 'Planner');
  });
  await attempt('a-remembered-fact-can-be-corrected', async () => {
    await button(memory().getByRole('listitem').filter({ hasText: 'I like tea' }).first(), 'Edit memory').click();
    await textbox(page, 'Memory text').fill('I like green tea');
    await button(page, 'Save memory').click();
    await memory().getByRole('listitem').filter({ hasText: 'I like green tea' }).first().waitFor({ state: 'visible' });
    await ask(page, 'Planner', 'what do you remember', 'I like green tea');
  });
  await attempt('a-remembered-fact-can-be-forgotten', async () => {
    await button(memory().getByRole('listitem').filter({ hasText: 'green tea' }).first(), 'Forget').click();
    await memory().getByRole('listitem').filter({ hasText: 'green tea' }).first().waitFor({ state: 'detached' });
    await ask(page, 'Planner', 'what do you remember now', "I don't remember anything about you yet");
  });
  await attempt('asking-the-bot-to-forget-works-too', async () => {
    await ask(page, 'Planner', 'remember that my desk is 4B', "I'll remember that my desk is 4B");
    await memory().getByRole('listitem').filter({ hasText: '4B' }).first().waitFor({ state: 'visible' });
    await ask(page, 'Planner', 'forget my desk is 4B', "I've forgotten");
    await memory().getByRole('listitem').filter({ hasText: '4B' }).first().waitFor({ state: 'detached' });
  });
  const instructions = () => region(page, 'Saved instructions');
  await attempt('a-saved-instruction-can-be-used', async () => {
    await textbox(instructions(), 'Instruction name').fill('Brief');
    await textbox(instructions(), 'Instruction text').fill('Answer in one line.');
    await button(instructions(), 'Save instruction').click();
    await button(instructions(), 'Use Brief').click();
    await ask(page, 'Planner', 'who are you', 'My instructions: Answer in one line.');
  });
  await attempt('a-saved-instruction-can-be-changed', async () => {
    await button(instructions(), 'Edit Brief').click();
    await textbox(instructions(), 'Instruction text').fill('Answer in two lines.');
    await button(instructions(), 'Save instruction').click();
    await button(instructions(), 'Use Brief').click();
    await ask(page, 'Planner', 'who are you again', 'I am Planner');
    await ask(page, 'Planner', 'who are you', 'My instructions: Answer in two lines.');
  });
  await attempt('the-open-bot-can-be-renamed', async () => {
    await button(page, 'Rename bot').click();
    await textbox(page, 'Bot name').fill('Planner Two');
    await button(page, 'Save bot name').click();
    await button(navigation(page, 'Bots'), 'Planner Two').waitFor({ state: 'visible' });
    await ask(page, 'Planner Two', 'who are you', 'I am Planner Two');
  });
  const saved = () => region(page, 'Saved tasks');
  await attempt('a-saved-task-can-be-run', async () => {
    await textbox(saved(), 'Task name').fill('Weekly');
    await textbox(saved(), 'Task request').fill('long task: weekly report');
    await button(saved(), 'Save task').click();
    await button(saved(), 'Run Weekly').click();
    await task(page, 'weekly report').waitFor({ state: 'visible', timeout: 12000 });
  });
  await attempt('another-person-sees-none-of-it', async () => {
    await button(page, 'Switch person').click();
    await button(page, 'Continue as Theo').click();
    await textbox(page, 'Message').waitFor({ state: 'visible' });
    expect(await button(navigation(page, 'Bots'), 'Planner Two').count() === 0, "Theo sees Maya's bot");
    await ask(page, 'Assistant', 'what do you remember', "I don't remember anything about you yet");
    expect(await messages(page, 'Maya').count() === 0, "Theo's conversation shows Maya's messages");
  });
  await attempt('another-person-gets-no-answer-from-records-they-may-not-read', async () => {
    await ask(page, 'Assistant', 'what is the total of ORD-1002', "I can't see a record called ORD-1002");
    await ask(page, 'Assistant', 'how many orders can you see', 'I can see 2 order record(s)');
  });
  await page.context().close();
  await server.stop();
  server = await startServer('core', { data: server.dataDir });
  page = await newPage();
  await attempt('bots-conversations-and-changes-survive-a-restart', async () => {
    await signIn(page, server.base, 'Maya');
    await button(navigation(page, 'Bots'), 'Planner Two').waitFor({ state: 'visible' });
    await openBot(page, 'Assistant');
    await messages(page, 'Maya').filter({ hasText: 'hello' }).first().waitFor({ state: 'visible' });
    await ask(page, 'Assistant', 'what is the status of ORD-1001 now', 'You said');
    await ask(page, 'Assistant', 'what is the status of ORD-1001', 'The status of ORD-1001 is closed');
  });
  await page.context().close();
  await server.stop();
}

// ---------------------------------------------------------------- long tasks
async function tasksMode() {
  let server = await startServer('tasks');
  let page = await newPage();
  let onReturn = '';
  await signIn(page, server.base, 'Maya').catch(() => {});
  await attempt('a-long-task-runs-to-the-end', async () => {
    await ask(page, 'Assistant', 'long task: quarterly review', "I'll work on");
    await task(page, 'quarterly review').waitFor({ state: 'visible' });
    await waitStatus(page, 'quarterly review', ['Completed'], 15000);
    expect((await task(page, 'quarterly review').innerText()).includes('Done: Write the summary of quarterly review'), 'the finished steps are not shown');
  });
  await attempt('work-continues-while-the-app-is-closed', async () => {
    await ask(page, 'Assistant', 'long task: audit [long]', "I'll work on");
    await waitStatus(page, 'audit', ['Running'], 5000);
    const mine = page.context(); // come back in the same browser, as a person does (calibration 11)
    await page.close();
    await sleep(3200);
    page = await newPage(1440, 1000, mine);
    await signIn(page, server.base, 'Maya');
    for (let tries = 0; tries < 15 && !onReturn.includes('audit'); tries += 1) { // what the account says on coming back (calibration 8)
      onReturn = await region(page, 'Since you were away').first().innerText().catch(() => '');
      if (!onReturn.includes('audit')) await page.waitForTimeout(200);
    }
    await task(page, 'audit').waitFor({ state: 'visible' });
    expect(await doneCount(page, 'audit') >= 3, 'fewer than three steps were done while the page was closed');
    await waitStatus(page, 'audit', ['Completed'], 15000);
  });
  await attempt('coming-back-shows-what-happened-while-away', async () => {
    const away = region(page, 'Since you were away');
    await away.waitFor({ state: 'visible' });
    expect(onReturn.includes('audit') || (await away.innerText()).includes('audit'), 'the account of what happened does not name the task, on coming back or after');
  });
  await attempt('a-running-task-can-be-cancelled', async () => {
    await ask(page, 'Assistant', 'long task: cleanup [long]', "I'll work on");
    await waitStatus(page, 'cleanup', ['Running'], 5000);
    await button(task(page, 'cleanup'), 'Cancel task').click();
    await waitStatus(page, 'cleanup', ['Cancelled'], 6000);
    const atCancel = await doneCount(page, 'cleanup');
    await sleep(3000); // the step that was in flight may still finish and be shown (calibration 9)
    const before = await doneCount(page, 'cleanup');
    await sleep(2500);
    const after = await doneCount(page, 'cleanup');
    expect(before - atCancel <= 1, `more than the step in flight finished after the cancel (${atCancel} then ${before} of 8)`);
    expect(after === before && after < 8, `steps kept finishing after the cancel (${before} then ${after} of 8)`);
  });
  await attempt('a-failed-task-can-be-retried-without-redoing-finished-steps', async () => {
    await ask(page, 'Assistant', 'long task: export [fail step 2]', "I'll work on");
    await waitStatus(page, 'export', ['Failed'], 12000);
    await button(task(page, 'export'), 'Retry task').click();
    await waitStatus(page, 'export', ['Completed'], 15000);
    expect(await doneCount(page, 'export', 'Done: Collect what is known about export') === 1, 'the first step is shown as done more than once');
  });
  await attempt('a-follow-up-steers-the-running-task', async () => {
    await ask(page, 'Assistant', 'long task: migration [long]', "I'll work on");
    await waitStatus(page, 'migration', ['Running'], 5000);
    await ask(page, 'Assistant', 'add step: notify the team', "I'll add");
    await waitStatus(page, 'migration', ['Completed'], 25000);
    expect((await task(page, 'migration').innerText()).includes('Done: notify the team'), 'the added step was not done');
  });
  await attempt('a-restart-neither-loses-nor-repeats-a-task', async () => {
    await ask(page, 'Assistant', 'long task: backup [long]', "I'll work on");
    await task(page, 'backup').filter({ hasText: 'Done: Compare the options for backup' }).waitFor({ state: 'visible', timeout: 10000 });
    await page.context().close();
    await server.stop();
    server = await startServer('tasks', { data: server.dataDir });
    page = await newPage();
    await signIn(page, server.base, 'Maya');
    await task(page, 'backup').waitFor({ state: 'visible' });
    const state = await waitStatus(page, 'backup', ['Running', 'Completed', 'Interrupted'], 8000);
    if (state.includes('Interrupted')) await button(task(page, 'backup'), 'Retry task').click();
    await waitStatus(page, 'backup', ['Completed'], 25000);
    expect(await doneCount(page, 'backup', 'Done: Collect what is known about backup') === 1, 'a step finished before the restart is shown as done twice');
  }, 90000);
  await attempt('the-conversation-is-still-there-after-a-restart', async () => {
    await messages(page, 'Maya').filter({ hasText: 'long task: quarterly review' }).first().waitFor({ state: 'visible' });
  });
  await page.context().close();
  await server.stop();
}

// ---------------------------------------------------------------- everyday use
async function layoutMode() {
  const server = await startServer('layout');
  for (const width of [320, 390, 1440]) {
    const page = await newPage(width, 860);
    await attempt(`no-sideways-scrolling-at-${width}`, async () => {
      await signIn(page, server.base, 'Maya');
      const [content, view] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
      expect(content <= view + 1, `the page is ${content} pixels wide in a ${view}-pixel window`);
    });
    if (width < 1440) {
      await attempt(`writing-a-message-works-at-${width}`, async () => {
        await ask(page, 'Assistant', `hello at ${width}`, `You said: "hello at ${width}"`);
      });
    } else {
      await attempt('the-message-box-is-reachable-from-the-keyboard', async () => {
        await page.locator('body').click({ position: { x: 2, y: 2 } }).catch(() => {});
        let reached = false;
        for (let presses = 0; presses < 80 && !reached; presses += 1) {
          await page.keyboard.press('Tab');
          reached = await textbox(page, 'Message').evaluate((box) => box === document.activeElement);
        }
        expect(reached, 'eighty presses of Tab never reached the Message box');
        await page.keyboard.type('typed from the keyboard');
        await page.keyboard.press('Enter');
        await reply(page, 'Assistant', 'You said: "typed from the keyboard"');
      });
    }
    await page.context().close();
  }
  await server.stop();
}

// ---------------------------------------------------------------- the delivery's own tests
function ownTests() {
  return attempt('npm-test-passes', () => new Promise((resolve, reject) => {
    const child = spawn('npm', ['test'], { cwd: product, env: { ...process.env, PROVIDER_TOKEN: TOKEN }, detached: true });
    let text = '';
    child.stdout.on('data', (chunk) => { text += chunk; });
    child.stderr.on('data', (chunk) => { text += chunk; });
    const timer = setTimeout(() => { try { process.kill(-child.pid, 'SIGKILL'); } catch { /* gone */ } reject(new Error('npm test did not end within 240 s')); }, 240000);
    child.on('exit', (code) => {
      clearTimeout(timer);
      const passed = /^(?:ℹ|#) pass [1-9]/m.test(text);
      if (code === 0 && passed) resolve(); else reject(new Error(`npm test exited ${code}${passed ? '' : ' with no passing test'}`));
    });
  }), 250000);
}

(async () => {
  let playwright;
  try { playwright = require(process.env.PLAYWRIGHT_NODE_PATH || 'playwright'); } catch (error) { report.error = 'Playwright unavailable: ' + error; return; }
  try {
    browser = await playwright.chromium.launch({ headless: true,
      ...(process.env.BROWSER_EXECUTABLE_PATH ? { executablePath: process.env.BROWSER_EXECUTABLE_PATH } : {}) });
    report.browser = browser.version();
  } catch (error) { report.error = 'Browser unavailable: ' + error; return; }
  report.observed = true;
  const modes = { setup: setupMode, core: coreMode, tasks: tasksMode, layout: layoutMode, tests: ownTests };
  for (const name of ONLY) {
    try { await modes[name](); } catch (error) { report.notes.push(`${name}: ${String(error && error.message ? error.message : error).slice(0, 300)}`); }
  }
  report.complete = true;
})().catch((error) => { report.error = String(error); }).finally(async () => {
  if (browser) await browser.close().catch(() => {});
  report.passed = report.checks.filter((row) => row.pass).length;
  fs.writeFileSync(path.join(output, 'observation.json'), JSON.stringify(report, null, 2) + '\n');
  process.exitCode = report.observed && report.complete && report.checks.length > 0 && report.checks.every((row) => row.pass) ? 0 : 1;
});
