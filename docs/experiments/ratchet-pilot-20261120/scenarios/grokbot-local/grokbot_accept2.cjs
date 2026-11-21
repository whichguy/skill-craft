/* Second held-out yardstick for the grokbot-local scenario. No model session is shown this file.
 *
 *   PLAYWRIGHT_NODE_PATH=<playwright module> BROWSER_EXECUTABLE_PATH=<chromium> \
 *     node grokbot_accept2.cjs PRODUCT OUTPUT [FIXTURE]
 *
 * grokbot_accept.cjs probes what REQUEST.md names. This file probes sentences of the request, and of the two README
 * files the request points at, that the first does not: where things are kept, awkward moments (a reload during a
 * slow or failed reply, the same proposal in two windows, a proposal whose record has changed), returning to the
 * right discussion, changing and deleting what was saved, three people, tasks side by side and after a restart, the
 * account on coming back, and the narrow and the wide window.
 *
 * Every check records the sentence it comes from and a tier: "stated" when that sentence says it, "implied" when
 * the check is my reading of it. The two tiers are counted apart. PRODUCT is a built copy of the app, OUTPUT
 * receives observation.json and the server logs, FIXTURE is the folder every run started from (default: the one
 * beside this file). Each mode runs on a free port with an empty data folder of its own; checks in one mode share
 * that mode's state. A message is written at a person's pace, as in the first yardstick after its calibration.
 *
 * Calibration, 2026-11-20 (the journal lists what was observed):
 *   A. `signIn` waits until the first screen has drawn (the first yardstick's correction 6), found on the Ratchet
 *      arm's first build.
 *   B. Found on the ShipLoop arm's build, which runs one task a conversation and says so when asked for a second:
 *      every check that needs two or three tasks at once now starts each in a conversation of its own, and opens
 *      the conversation that holds a task before looking for it (an app may list only the open conversation's
 *      tasks). The request does not say several tasks run in one conversation, and provider/README.md speaks of
 *      "their running task in this conversation".
 *   C. The account on coming back is read on coming back (for up to three seconds after signing in), on a server of
 *      its own whose steps take 1200 ms, so that one task has finished, one has failed and one still runs while the
 *      page is closed.
 *   D. Two blind spots that planted defects exposed (one defect a check, on copies of the bare build) were closed:
 *      the instructions check now also asks a bot that existed before the instruction was used, and the long-word
 *      check now measures the word itself and not only the page.
 *   E. Waiting for a new conversation to be empty counts messages only. The ShipLoop arm's build draws its task
 *      cards inside the Conversation region, and the first version counted those as messages and never saw an
 *      empty conversation.
 */
'use strict';
const crypto = require('node:crypto');
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');
const { spawn } = require('node:child_process');

const [productArg, outputArg, fixtureArg] = process.argv.slice(2);
const product = path.resolve(productArg);
const output = path.resolve(outputArg);
const fixture = path.resolve(fixtureArg || path.join(__dirname, 'fixture'));
const TOKEN = 'sk-local-Yardstick00029';
const ONLY = (process.env.GROKBOT_MODES || 'files,conversations,saved,people,changes,tasks,layout,kept').split(',');
const report = { product, yardstick: 2, started: new Date().toISOString(), observed: false, complete: false, checks: [], notes: [] };
fs.mkdirSync(output, { recursive: true });
let browser;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
function expect(condition, note) {
  if (!condition) throw new Error(note);
}
async function attempt(id, tier, from, run, limit = 60000) {
  let timer;
  try {
    await Promise.race([run(), new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`no result within ${limit / 1000} s`)), limit); })]);
    report.checks.push({ id, tier, from, pass: true });
  } catch (error) {
    report.checks.push({ id, tier, from, pass: false, note: String(error && error.message ? error.message : error).split('\n')[0].slice(0, 300) });
  } finally {
    clearTimeout(timer);
  }
}

// ---------------------------------------------------------------- the app's own folder, before and after
const sha = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
function listing(root) {
  const found = {};
  const walk = (folder) => {
    for (const entry of fs.readdirSync(folder, { withFileTypes: true })) {
      if (entry.name === '.git') continue;
      const full = path.join(folder, entry.name);
      if (entry.isDirectory()) walk(full);
      else found[path.relative(root, full)] = entry.isFile() ? sha(full) : 'not a file';
    }
  };
  walk(root);
  return found;
}
const before = listing(product);

// ---------------------------------------------------------------- the server under test
function freePort() {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => { const { port } = probe.address(); probe.close(() => resolve(port)); });
  });
}
async function startServer(name, { data, stepMs = 700 } = {}) {
  const port = await freePort();
  const dataDir = data || path.join(output, `data-${name}`);
  fs.mkdirSync(dataDir, { recursive: true });
  const env = { ...process.env, PORT: String(port), DATA_DIR: dataDir, PROVIDER_TOKEN: TOKEN, STANDIN_SLOW_MS: '1500', STANDIN_STEP_MS: String(stepMs) };
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
const theirs = (page, me = 'Maya') => conversation(page).getByRole('article', { name: new RegExp(`^Message from (?!${me}$).+`) });
const task = (page, title) => page.getByRole('article', { name: `Task: ${title}`, exact: true });
const taskStatus = (page, title) => task(page, title).getByRole('status', { name: 'Task status', exact: true });

async function newPage(width = 1440, height = 1000, context) {
  const page = await (context || await browser.newContext({ viewport: { width, height }, reducedMotion: 'reduce' })).newPage();
  page.setDefaultTimeout(8000);
  page.setDefaultNavigationTimeout(15000);
  page.on('dialog', (dialog) => { dialog.accept().catch(() => {}); }); // an app may ask "are you sure" before a delete
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
async function switchTo(page, who) {
  await button(page, 'Switch person').click();
  await button(page, `Continue as ${who}`).click();
  await textbox(page, 'Message').waitFor({ state: 'visible' });
  await page.waitForTimeout(400);
}
async function send(page, text) {
  await page.waitForTimeout(300); // a person's pace after their last click
  await textbox(page, 'Message').fill(text);
  await button(page, 'Send').click();
}
async function reply(page, text, { limit = 12000, me = 'Maya' } = {}) {
  await theirs(page, me).filter({ hasText: text }).last().waitFor({ state: 'visible', timeout: limit });
}
async function ask(page, text, answer, options) {
  await send(page, text);
  await reply(page, answer, options);
}
async function openBot(page, name) {
  await button(navigation(page, 'Bots'), name).click();
  await page.waitForTimeout(300);
}
async function newBot(page, name) {
  await button(page, 'New bot').click();
  await textbox(page, 'Bot name').fill(name);
  await button(page, 'Save bot name').click();
  await button(navigation(page, 'Bots'), name).waitFor({ state: 'visible' });
  await page.waitForTimeout(300);
}
async function newConversation(page) {
  await button(page, 'New conversation').first().click();
  const shownMessages = () => conversation(page).getByRole('article', { name: /^Message from / }).count(); // an app may draw task cards there too (calibration E)
  let shown = await shownMessages();
  for (let tries = 0; tries < 40 && shown > 0; tries += 1) {
    await page.waitForTimeout(200);
    shown = await shownMessages();
  }
  expect(shown === 0, `the new conversation still shows ${shown} message(s) after 8 s`);
}
/** The buttons of the Conversations navigation that are conversations: every button there but New conversation. */
async function conversationButtons(page) {
  const nav = navigation(page, 'Conversations');
  await nav.getByRole('button', { name: 'New conversation', exact: true }).evaluateAll((found) => found.forEach((each) => each.setAttribute('data-yardstick-new', '1')));
  const rows = await nav.getByRole('button').evaluateAll((found) => found.map((each, index) => ({
    index,
    isNew: each.hasAttribute('data-yardstick-new'),
    current: each.getAttribute('aria-current') !== null && each.getAttribute('aria-current') !== 'false',
    text: (each.innerText || '').trim(),
  })));
  return rows.filter((row) => !row.isNew);
}
/** Bring a task's article onto the screen: an app may list only the open conversation's tasks (calibration B). */
async function showTask(page, title) {
  if (await task(page, title).count()) return;
  const listed = (await conversationButtons(page)).length;
  for (let turn = 0; turn < listed; turn += 1) {
    const rows = await conversationButtons(page);
    if (!rows[turn]) break;
    await navigation(page, 'Conversations').getByRole('button').nth(rows[turn].index).click();
    await page.waitForTimeout(500);
    if (await task(page, title).count()) return;
  }
  throw new Error(`no conversation shows the task "${title}"`);
}
async function waitStatus(page, title, wanted, limit) {
  const pattern = new RegExp(wanted.join('|'));
  await taskStatus(page, title).filter({ hasText: pattern }).waitFor({ state: 'visible', timeout: limit });
  return (await taskStatus(page, title).innerText()).trim();
}
async function doneCount(page, title, text = 'Done:') {
  return ((await task(page, title).innerText()).split(text).length - 1);
}

// ---------------------------------------------------------------- what is delivered
async function filesMode() {
  await attempt('the-stand-in-is-delivered-as-it-was', 'stated', 'use it as it is for every reply and do not change it', async () => {
    for (const name of ['provider/standin.js', 'provider/README.md']) {
      expect(fs.existsSync(path.join(product, name)), `${name} is missing`);
      expect(sha(path.join(product, name)) === sha(path.join(fixture, name)), `${name} is not the file the project started with`);
    }
  });
  await attempt('no-npm-dependencies', 'stated', 'It is a Node.js app with no npm dependencies', async () => {
    const manifest = JSON.parse(fs.readFileSync(path.join(product, 'package.json'), 'utf8'));
    const named = ['dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies'].filter((key) => manifest[key] && Object.keys(manifest[key]).length);
    expect(named.length === 0, `package.json lists ${named.join(', ')}`);
    expect(!fs.existsSync(path.join(product, 'node_modules')), 'a node_modules folder is delivered');
  });
}

// ---------------------------------------------------------------- returning to the right discussion, awkward moments
async function conversationsMode() {
  const server = await startServer('conversations');
  const page = await newPage();
  await signIn(page, server.base, 'Maya').catch(() => {});
  const returning = 'keep multiple saved conversations, returning to the right bot and discussion without losing my place';
  await attempt('opening-an-earlier-conversation-returns-to-it', 'stated', returning, async () => {
    await ask(page, 'alpha one', 'You said: "alpha one"');
    await newConversation(page);
    await ask(page, 'beta two', '(Assistant has 1 message(s)');
    const others = (await conversationButtons(page)).filter((row) => !row.current);
    const pick = others.find((row) => row.text.includes('alpha one')) || (others.length === 1 ? others[0] : null);
    expect(pick, `cannot tell which of ${others.length} other buttons in the Conversations navigation is the first conversation`);
    await navigation(page, 'Conversations').getByRole('button').nth(pick.index).click();
    await messages(page, 'Maya').filter({ hasText: 'alpha one' }).first().waitFor({ state: 'visible' });
    expect(await messages(page, 'Maya').filter({ hasText: 'beta two' }).count() === 0, "the first conversation shows the second one's message");
    await ask(page, 'what did I ask first', 'You first asked: "alpha one"');
  });
  await attempt('the-open-conversation-is-the-one-marked-current', 'stated', "A navigation named Conversations lists the open bot's conversations as buttons, with the open one marked as current", async () => {
    const rows = await conversationButtons(page);
    const marked = rows.filter((row) => row.current);
    expect(marked.length === 1, `${marked.length} of ${rows.length} conversation buttons are marked as current`);
    const other = rows.find((row) => !row.current);
    expect(other, 'only one conversation is listed');
    await navigation(page, 'Conversations').getByRole('button').nth(other.index).click();
    await messages(page, 'Maya').filter({ hasText: 'beta two' }).first().waitFor({ state: 'visible' });
    await page.waitForTimeout(300);
    const after = await conversationButtons(page);
    const now = after.filter((row) => row.current);
    expect(now.length === 1, `${now.length} conversation buttons are marked as current after opening the other one`);
    const told = new Set(after.map((row) => row.text)).size > 1; // the titles tell the two apart
    expect(!told || now[0].text !== marked[0].text, 'the mark stayed on the conversation that was left');
  });
  await attempt('each-bot-returns-to-its-own-discussion', 'stated', returning, async () => {
    await ask(page, 'beta again', 'You said: "beta again"');
    await newBot(page, 'Second');
    await ask(page, 'gamma three', '(Second has 1 message(s)');
    await openBot(page, 'Assistant');
    await messages(page, 'Maya').filter({ hasText: 'beta again' }).first().waitFor({ state: 'visible' });
    expect(await messages(page, 'Maya').filter({ hasText: 'gamma three' }).count() === 0, "the Assistant bot shows the Second bot's message");
    await openBot(page, 'Second');
    await messages(page, 'Maya').filter({ hasText: 'gamma three' }).first().waitFor({ state: 'visible' });
    expect(await messages(page, 'Maya').filter({ hasText: 'beta again' }).count() === 0, "the Second bot shows the Assistant bot's message");
  });
  const recover = 'If something fails or is interrupted, help me recover without guessing or losing the conversation';
  await attempt('a-reload-during-a-slow-reply-loses-nothing', 'stated', recover, async () => {
    await send(page, '[slow] slow one');
    await page.waitForTimeout(400);
    await page.reload({ waitUntil: 'load' });
    await textbox(page, 'Message').waitFor({ state: 'visible' });
    const mine = messages(page, 'Maya').filter({ hasText: 'slow one' });
    await mine.first().waitFor({ state: 'visible' });
    const answer = theirs(page).filter({ hasText: 'You said: "slow one"' });
    try {
      await answer.first().waitFor({ state: 'visible', timeout: 7000 });
    } catch {
      const retry = button(page, 'Retry');
      expect(await retry.count() > 0, 'after the reload the reply never came and nothing offers to try again');
      await retry.first().click();
      await answer.first().waitFor({ state: 'visible', timeout: 9000 });
    }
    expect(await mine.count() === 1, `my message is shown ${await mine.count()} times`);
    expect(await answer.count() === 1, `the reply is shown ${await answer.count()} times`);
  });
  await attempt('a-failed-reply-can-still-be-retried-after-a-reload', 'stated', `a button named Retry tries again without sending my message a second time. ${recover}`, async () => {
    await send(page, '[fail once] flaky two');
    await page.getByRole('alert').first().waitFor({ state: 'visible' });
    await page.reload({ waitUntil: 'load' });
    const box = textbox(page, 'Message');
    await box.waitFor({ state: 'visible' });
    await page.waitForTimeout(500);
    const mine = messages(page, 'Maya').filter({ hasText: 'flaky two' });
    const answer = theirs(page).filter({ hasText: 'You said: "flaky two"' });
    if (await answer.count() === 0) {
      if (await mine.count() === 0) { // an app may hand the words back in the box rather than keep an unanswered message
        expect((await box.inputValue()).includes('flaky two'), 'after the reload the failed message is gone from the conversation and from the message box');
        await button(page, 'Send').click();
      } else {
        const retry = button(page, 'Retry');
        try { await retry.first().waitFor({ state: 'visible', timeout: 4000 }); } catch { throw new Error('after the reload the failed message is shown and nothing offers to try again'); }
        await retry.first().click();
      }
      await answer.first().waitFor({ state: 'visible', timeout: 9000 });
    }
    expect(await mine.count() === 1, `my message is shown ${await mine.count()} times`);
  });
  await page.context().close();
  await server.stop();
}

// ---------------------------------------------------------------- what was saved can be changed and removed
async function savedMode() {
  const server = await startServer('saved');
  const page = await newPage();
  await signIn(page, server.base, 'Maya').catch(() => {});
  const instructions = () => region(page, 'Saved instructions');
  const saved = () => region(page, 'Saved tasks');
  const editing = 'Edit <name> puts it back into those two textboxes, to change and save again under the same name';
  await attempt('editing-puts-an-instruction-back-into-its-two-textboxes', 'stated', editing, async () => {
    await textbox(instructions(), 'Instruction name').fill('Brief');
    await textbox(instructions(), 'Instruction text').fill('Answer in one line.');
    await button(instructions(), 'Save instruction').click();
    await button(instructions(), 'Use Brief').waitFor({ state: 'visible' });
    await textbox(instructions(), 'Instruction name').fill('');
    await textbox(instructions(), 'Instruction text').fill('');
    await button(instructions(), 'Edit Brief').click();
    await page.waitForTimeout(300);
    const name = await textbox(instructions(), 'Instruction name').inputValue();
    const text = await textbox(instructions(), 'Instruction text').inputValue();
    expect(name === 'Brief' && text === 'Answer in one line.', `after Edit Brief the textboxes hold "${name}" and "${text}"`);
    await textbox(instructions(), 'Instruction text').fill('Answer in two lines.');
    await button(instructions(), 'Save instruction').click();
    await page.waitForTimeout(500);
    const entries = await button(instructions(), 'Use Brief').count();
    expect(entries === 1, `saving again under the same name left ${entries} entries named Brief`);
  });
  await attempt('instructions-belong-to-the-bot-that-uses-them', 'stated', "Using one makes it the open bot's instructions from the next reply on", async () => {
    await newBot(page, 'Other'); // a bot that exists before the instruction is used (calibration D)
    await openBot(page, 'Assistant');
    await button(instructions(), 'Use Brief').click();
    await ask(page, 'who are you', /My instructions: Answer in (one|two) lines?\./);
    await openBot(page, 'Other');
    await ask(page, 'who are you', 'I am Other. I have no special instructions');
    await newBot(page, 'Third'); // and one made afterwards
    await ask(page, 'who are you', 'I am Third. I have no special instructions');
  });
  await attempt('a-saved-instruction-can-be-deleted', 'stated', 'Each saved one has buttons named Use <name>, Edit <name> and Delete <name>', async () => {
    await textbox(instructions(), 'Instruction name').fill('Temp');
    await textbox(instructions(), 'Instruction text').fill('Temporary.');
    await button(instructions(), 'Save instruction').click();
    await button(instructions(), 'Use Temp').waitFor({ state: 'visible' });
    const kept = await button(instructions(), 'Use Brief').count();
    await button(instructions(), 'Delete Temp').click();
    await button(instructions(), 'Use Temp').waitFor({ state: 'hidden' });
    await page.reload({ waitUntil: 'load' });
    await textbox(page, 'Message').waitFor({ state: 'visible' });
    await page.waitForTimeout(400);
    expect(await button(instructions(), 'Use Temp').count() === 0, 'the deleted instruction is back after a reload');
    expect(await button(instructions(), 'Use Brief').count() === kept, 'deleting one instruction removed another');
  });
  await attempt('a-saved-task-can-be-changed-under-the-same-name', 'stated', `${editing}. Running one sends its request in the open conversation`, async () => {
    await textbox(saved(), 'Task name').fill('Daily');
    await textbox(saved(), 'Task request').fill('who are you');
    await button(saved(), 'Save task').click();
    await button(saved(), 'Run Daily').waitFor({ state: 'visible' });
    await textbox(saved(), 'Task name').fill('');
    await textbox(saved(), 'Task request').fill('');
    await button(saved(), 'Edit Daily').click();
    await page.waitForTimeout(300);
    const name = await textbox(saved(), 'Task name').inputValue();
    const request = await textbox(saved(), 'Task request').inputValue();
    expect(name === 'Daily' && request === 'who are you', `after Edit Daily the textboxes hold "${name}" and "${request}"`);
    await textbox(saved(), 'Task request').fill('what do you remember');
    await button(saved(), 'Save task').click();
    await page.waitForTimeout(500);
    const entries = await button(saved(), 'Run Daily').count();
    expect(entries === 1, `saving again under the same name left ${entries} tasks named Daily`);
    await button(saved(), 'Run Daily').click();
    await reply(page, "I don't remember anything about you yet");
    await messages(page, 'Maya').filter({ hasText: 'what do you remember' }).first().waitFor({ state: 'visible' });
  });
  await attempt('a-saved-task-can-be-deleted', 'stated', 'Each saved one has buttons named Run <name>, Edit <name> and Delete <name>', async () => {
    await button(saved(), 'Run Daily').first().waitFor({ state: 'visible' });
    await button(saved(), 'Delete Daily').first().click();
    await button(saved(), 'Run Daily').first().waitFor({ state: 'hidden' });
    await page.reload({ waitUntil: 'load' });
    await textbox(page, 'Message').waitFor({ state: 'visible' });
    await page.waitForTimeout(400);
    expect(await button(saved(), 'Run Daily').count() === 0, 'the deleted task is back after a reload');
  });
  await attempt('after-enter-the-next-message-can-be-typed-at-once', 'implied', 'Make everyday use comfortable on a desktop, in a narrow window, and with the keyboard', async () => {
    await textbox(page, 'Message').click();
    await page.keyboard.type('first by keyboard');
    await page.keyboard.press('Enter');
    await reply(page, 'You said: "first by keyboard"');
    await page.waitForTimeout(300);
    await page.keyboard.type('second by keyboard'); // no click: the words must land in the message box
    await page.keyboard.press('Enter');
    await reply(page, 'You said: "second by keyboard"');
  });
  await page.context().close();
  await server.stop();
}

// ---------------------------------------------------------------- three people
async function peopleMode() {
  const server = await startServer('people');
  const page = await newPage();
  await signIn(page, server.base, 'Maya').catch(() => {});
  await attempt('what-i-saved-and-what-my-bot-remembers-is-not-shown-to-another-person', 'stated', "My information should stay separate from another user's", async () => {
    const instructions = region(page, 'Saved instructions');
    await textbox(instructions, 'Instruction name').fill('Mine');
    await textbox(instructions, 'Instruction text').fill('Private to Maya.');
    await button(instructions, 'Save instruction').click();
    await button(instructions, 'Use Mine').waitFor({ state: 'visible' });
    await ask(page, 'remember that my code is 7411', "I'll remember that my code is 7411");
    await region(page, 'Memory').getByRole('listitem').filter({ hasText: '7411' }).first().waitFor({ state: 'visible' });
    await switchTo(page, 'Theo');
    expect(await button(page, 'Use Mine').count() === 0, "Theo is shown Maya's saved instruction");
    expect(await region(page, 'Memory').getByRole('listitem').filter({ hasText: '7411' }).count() === 0, "Theo is shown what Maya's bot remembers");
    await ask(page, 'what do you remember', "I don't remember anything about you yet", { me: 'Theo' });
  });
  await attempt('a-third-person-is-answered-only-from-their-own-records', 'stated', 'accurate answers grounded in records I am allowed to read (records/README.md: a person may read only the records that list them as a reader)', async () => {
    await switchTo(page, 'Ana');
    await ask(page, 'how many orders can you see', 'I can see 1 order record(s)', { me: 'Ana' });
    await ask(page, 'how many accounts can you see', 'I can see 2 account record(s)', { me: 'Ana' });
    await ask(page, 'what is the tier of ACC-2002', "I can't see a record called ACC-2002", { me: 'Ana' });
  });
  await attempt('coming-back-as-myself-i-find-my-things', 'stated', 'What I see, and what my bots remember, belongs to the person I continued as', async () => {
    await switchTo(page, 'Maya');
    await button(region(page, 'Saved instructions'), 'Use Mine').waitFor({ state: 'visible' });
    await region(page, 'Memory').getByRole('listitem').filter({ hasText: '7411' }).first().waitFor({ state: 'visible' });
    await messages(page, 'Maya').filter({ hasText: 'remember that my code is 7411' }).first().waitFor({ state: 'visible' });
  });
  await page.context().close();
  await server.stop();
}

// ---------------------------------------------------------------- changes at awkward moments
async function changesMode() {
  const server = await startServer('changes');
  const page = await newPage();
  await signIn(page, server.base, 'Maya').catch(() => {});
  await attempt('a-change-can-be-confirmed-from-the-keyboard', 'stated', 'Make everyday use comfortable on a desktop, in a narrow window, and with the keyboard', async () => {
    await ask(page, 'set the status of ORD-1004 to closed', 'I propose one change');
    const confirm = button(page, 'Confirm changes');
    await confirm.waitFor({ state: 'visible' });
    await confirm.focus();
    await page.keyboard.press('Enter');
    await region(page, 'Change result').waitFor({ state: 'visible' });
    await ask(page, 'what is the status of ORD-1004', 'The status of ORD-1004 is closed');
  });
  await attempt('confirming-in-two-windows-applies-it-once', 'stated', 'Repeating an action or reloading at an awkward moment should not accidentally apply it twice', async () => {
    await ask(page, 'create an order for Dup Co totalling 55', 'I propose creating one order');
    const first = button(page, 'Confirm changes');
    await first.waitFor({ state: 'visible' });
    const twin = await newPage(1440, 1000, page.context()); // the same person in a second window
    await signIn(twin, server.base, 'Maya');
    const second = button(twin, 'Confirm changes');
    const offered = await second.first().waitFor({ state: 'visible', timeout: 3000 }).then(() => true, () => false);
    await first.click();
    if (offered) await second.first().click({ timeout: 2000 }).catch(() => {});
    await page.waitForTimeout(1000);
    await twin.close();
    await page.reload({ waitUntil: 'load' });
    await textbox(page, 'Message').waitFor({ state: 'visible' });
    await send(page, 'how many orders can you see');
    const line = theirs(page).filter({ hasText: /I can see \d+ order record\(s\)/ }).last();
    await line.waitFor({ state: 'visible', timeout: 12000 });
    const seen = Number((await line.innerText()).match(/I can see (\d+) order record/)[1]);
    expect(seen === 4, `Maya sees ${seen} orders after one new order was confirmed${offered ? ' in two windows' : ''}; 4 is right`);
  });
  await attempt('a-proposal-whose-record-has-changed-is-not-applied-blindly', 'implied', 'I want to see the exact proposed changes before deciding ... and I should understand what actually happened', async () => {
    await ask(page, 'set the total of ORD-1001 to 150', 'I propose one change');
    await region(page, 'Proposed changes').waitFor({ state: 'visible' });
    const other = await newPage();
    await signIn(other, server.base, 'Theo');
    await ask(other, 'set the total of ORD-1001 to 999', 'I propose one change', { me: 'Theo' });
    await button(other, 'Confirm changes').click();
    await region(other, 'Change result').waitFor({ state: 'visible' });
    await ask(other, 'what is the total of ORD-1001', 'The total of ORD-1001 is 999', { me: 'Theo' });
    const shown = (await region(page, 'Proposed changes').innerText().catch(() => '')).replace(/\s+/g, ' ');
    const confirm = button(page, 'Confirm changes');
    if (await confirm.count()) { await confirm.first().click().catch(() => {}); await page.waitForTimeout(1000); }
    await newConversation(other);
    await send(other, 'what is the total of ORD-1001');
    const line = theirs(other, 'Theo').filter({ hasText: /The total of ORD-1001 is \d+/ }).last();
    await line.waitFor({ state: 'visible', timeout: 12000 });
    const total = Number((await line.innerText()).match(/The total of ORD-1001 is (\d+)/)[1]);
    await other.context().close();
    expect(total === 999 || shown.includes('999'), `the proposal read "${shown.slice(0, 90)}" and confirming it set the total to ${total} over another person's 999`);
  });
  await page.context().close();
  await server.stop();
}

// ---------------------------------------------------------------- long tasks side by side, after a restart, on coming back
async function tasksMode() {
  let server = await startServer('tasks');
  let page = await newPage();
  await signIn(page, server.base, 'Maya').catch(() => {});
  await attempt('a-finished-task-no-longer-offers-cancel', 'stated', 'a button named Cancel task while it runs', async () => {
    await ask(page, 'long task: short one', 'I\'ll work on "short one"');
    await waitStatus(page, 'short one', ['Completed'], 15000);
    const cancel = button(task(page, 'short one'), 'Cancel task');
    expect(await cancel.count() === 0 || await cancel.first().isDisabled(), 'a completed task still offers Cancel task');
  });
  await attempt('a-steered-task-does-all-its-steps-and-the-added-one', 'stated', 'provider/README.md: steer: add that step to the end of their running task in this conversation', async () => {
    await ask(page, 'long task: migration [long]', 'I\'ll work on "migration"');
    await waitStatus(page, 'migration', ['Running'], 5000);
    await ask(page, 'add step: notify the team', "I'll add");
    await waitStatus(page, 'migration', ['Completed'], 25000);
    const done = await doneCount(page, 'migration');
    expect((await task(page, 'migration').innerText()).includes('Done: notify the team'), 'the added step was not done');
    expect(done === 9, `the steered task shows ${done} finished steps; its 8 and the added one make 9`);
  });
  await attempt('cancelling-one-task-leaves-another-running', 'implied', 'A region named Tasks shows each long task ... steer ongoing work with a follow-up or cancel it', async () => {
    await newConversation(page); // each task in a conversation of its own (calibration B)
    await ask(page, 'long task: second job [long]', 'I\'ll work on "second job"');
    await waitStatus(page, 'second job', ['Running'], 5000);
    await newConversation(page);
    await ask(page, 'long task: first job [long]', 'I\'ll work on "first job"');
    await waitStatus(page, 'first job', ['Running'], 5000);
    await button(task(page, 'first job'), 'Cancel task').click();
    await waitStatus(page, 'first job', ['Cancelled'], 6000);
    await showTask(page, 'second job');
    await waitStatus(page, 'second job', ['Completed'], 30000);
    const done = await doneCount(page, 'second job');
    expect(done === 8, `the task that was not cancelled shows ${done} of its 8 steps`);
  });
  await attempt('a-cancelled-task-stays-cancelled-after-a-restart', 'implied', 'an honest account of what finished, what is still happening ... what has already happened', async () => {
    await showTask(page, 'first job');
    const earlier = await doneCount(page, 'first job');
    await page.context().close();
    await server.stop();
    server = await startServer('tasks', { data: server.dataDir });
    page = await newPage();
    await signIn(page, server.base, 'Maya');
    await showTask(page, 'first job');
    await task(page, 'first job').waitFor({ state: 'visible' });
    const state = await waitStatus(page, 'first job', ['Running', 'Completed', 'Failed', 'Cancelled', 'Interrupted'], 8000);
    expect(state.includes('Cancelled'), `after a restart the cancelled task reads "${state}"`);
    await sleep(2000);
    const later = await doneCount(page, 'first job');
    expect(later === earlier, `a cancelled task went from ${earlier} to ${later} finished steps after a restart`);
  }, 90000);
  await page.context().close().catch(() => {});
  await server.stop();
  // a server of its own with slower steps: while the page is closed one task finishes, one fails and one still runs
  server = await startServer('away', { stepMs: 1200 });
  page = await newPage();
  await signIn(page, server.base, 'Maya').catch(() => {});
  await attempt('coming-back-names-what-finished-what-runs-and-what-failed', 'stated', 'a region named Since you were away tells me what finished, what is still running and what needs my attention', async () => {
    await ask(page, 'long task: big survey [long]', 'I\'ll work on "big survey"'); // 8 steps, 9.6 s
    await newConversation(page);
    await ask(page, 'long task: quick note', 'I\'ll work on "quick note"'); // 3 steps, 3.6 s
    await newConversation(page);
    await ask(page, 'long task: export [fail step 2]', 'I\'ll work on "export"'); // fails 2.4 s from here
    await page.context().close();
    await sleep(4500);
    page = await newPage();
    await signIn(page, server.base, 'Maya');
    const titles = ['big survey', 'export', 'quick note'];
    let text = '';
    for (let tries = 0; tries < 15; tries += 1) { // what the account says on coming back (calibration C)
      text = await region(page, 'Since you were away').first().innerText().catch(() => '');
      if (titles.every((title) => text.includes(title))) break;
      await page.waitForTimeout(200);
    }
    const missing = titles.filter((title) => !text.includes(title));
    expect(missing.length === 0, `on coming back the account does not name: ${missing.join(', ')} (it reads "${text.replace(/\s+/g, ' ').slice(0, 140)}")`);
  });
  await page.context().close().catch(() => {});
  await server.stop();
}

// ---------------------------------------------------------------- the wide and the narrow window
async function layoutMode() {
  const server = await startServer('layout');
  const wide = await newPage(1440, 1000);
  await signIn(wide, server.base, 'Maya').catch(() => {});
  await attempt('at-1440-everything-named-is-on-the-main-screen', 'stated', 'At a desktop width (1440 pixels) everything named here is on the main screen without my having to open a menu', async () => {
    await ask(wide, 'remember that I like tea', "I'll remember that I like tea"); // so that Memory and Tasks have something to show
    await ask(wide, 'long task: tidy', 'I\'ll work on "tidy"');
    await task(wide, 'tidy').waitFor({ state: 'visible' });
    const missing = [];
    for (const name of ['Conversation', 'Saved instructions', 'Saved tasks', 'Memory', 'Tasks']) if (!(await region(wide, name).first().isVisible())) missing.push(`region ${name}`);
    for (const name of ['Bots', 'Conversations']) if (!(await navigation(wide, name).first().isVisible())) missing.push(`navigation ${name}`);
    for (const name of ['New bot', 'Rename bot', 'New conversation', 'Send', 'Save instruction', 'Save task', 'Switch person']) if (!(await button(wide, name).first().isVisible())) missing.push(`button ${name}`);
    for (const name of ['Message', 'Instruction name', 'Instruction text', 'Task name', 'Task request']) if (!(await textbox(wide, name).first().isVisible())) missing.push(`textbox ${name}`);
    expect(missing.length === 0, `not on the main screen: ${missing.join(', ')}`);
  });
  await wide.context().close();
  const narrow = await newPage(320, 640);
  await signIn(narrow, server.base, 'Maya').catch(() => {});
  await attempt('at-320-the-newest-reply-and-the-message-box-are-in-view', 'stated', 'in a narrow window you may fold parts away, as long as reading the conversation and writing a message stay in view', async () => {
    await ask(narrow, 'narrow hello', 'You said: "narrow hello"');
    await narrow.waitForTimeout(500);
    const view = narrow.viewportSize();
    const box = await textbox(narrow, 'Message').boundingBox();
    expect(box && box.y >= -1 && box.y + box.height <= view.height + 1 && box.x >= -1 && box.x + box.width <= view.width + 1,
      `after a reply the Message box is not wholly inside a ${view.width} by ${view.height} window (${box ? `top ${Math.round(box.y)}, bottom ${Math.round(box.y + box.height)}` : 'not shown'})`);
    const last = await theirs(narrow).filter({ hasText: 'narrow hello' }).last().boundingBox();
    expect(last && last.y < view.height && last.y + last.height > 0, 'after a reply the newest reply is outside the window');
  });
  await attempt('a-long-unbroken-message-does-not-widen-the-page-at-320', 'implied', 'Make everyday use comfortable on a desktop, in a narrow window, and with the keyboard', async () => {
    const word = 'W'.repeat(240);
    await ask(narrow, word, 'You said: "WWWWWWWWWWWWWWWWWWWW');
    await narrow.waitForTimeout(300);
    const [content, width] = await narrow.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
    expect(content <= width + 1, `the page is ${content} pixels wide in a ${width}-pixel window`);
    // the word itself must wrap inside the window: a pane that scrolls sideways hides it as well (calibration D)
    const right = await theirs(narrow).filter({ hasText: 'WWWWWWWWWWWWWWWWWWWW' }).last().evaluate((article) => {
      const range = document.createRange();
      range.selectNodeContents(article);
      return Math.round(range.getBoundingClientRect().right);
    });
    expect(right <= width + 1, `the long word runs to ${right} pixels in a ${width}-pixel window`);
  });
  await narrow.context().close();
  await server.stop();
}

// ---------------------------------------------------------------- where things were kept, after all of the above
async function keptMode() {
  await attempt('everything-kept-lives-under-the-data-folder', 'stated', 'everything it keeps lives under the folder named by the DATA_DIR environment variable', async () => {
    const after = listing(product);
    const changed = [...new Set([...Object.keys(before), ...Object.keys(after)])].filter((name) => before[name] !== after[name]).sort();
    expect(changed.length === 0, `the app's own folder changed while it ran: ${changed.slice(0, 8).join(', ')}${changed.length > 8 ? ', ...' : ''}`);
  });
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
  const modes = { files: filesMode, conversations: conversationsMode, saved: savedMode, people: peopleMode, changes: changesMode, tasks: tasksMode, layout: layoutMode, kept: keptMode };
  for (const name of ONLY) {
    try { await modes[name](); } catch (error) { report.notes.push(`${name}: ${String(error && error.message ? error.message : error).slice(0, 300)}`); }
  }
  report.complete = true;
})().catch((error) => { report.error = String(error); }).finally(async () => {
  if (browser) await browser.close().catch(() => {});
  report.passed = report.checks.filter((row) => row.pass).length;
  report.stated = { passed: report.checks.filter((row) => row.tier === 'stated' && row.pass).length, of: report.checks.filter((row) => row.tier === 'stated').length };
  report.implied = { passed: report.checks.filter((row) => row.tier === 'implied' && row.pass).length, of: report.checks.filter((row) => row.tier === 'implied').length };
  fs.writeFileSync(path.join(output, 'observation.json'), JSON.stringify(report, null, 2) + '\n');
  process.exitCode = report.observed && report.complete && report.checks.length > 0 && report.checks.every((row) => row.pass) ? 0 : 1;
});
