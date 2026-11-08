'use strict';

// Synthetic browser calibration: a split Send from the Save handler must fail
// missing-setup acceptance even though it occurs after the pre-click assertion.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const browserTools = require('../../shiploop_e2e/checks/battleship_ui_browser.cjs');
const driver = require('../../shiploop_e2e/checks/grok_chat_full_ui_browser.cjs');
const host = 'calibration.lightning.force.com';

async function scenario(browser, phase) {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), 'shiploop-setup-boundary-'));
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  const observer = new driver.ApexObserver(page, host);
  const receive = observer.onResponse.bind(observer);
  observer.onResponse = async response => {
    const posted = response.request().postData();
    if (phase === 'after' && posted && posted.includes('"method":"saveSetup"')) {
      await new Promise(resolve => setTimeout(resolve, 150));
    }
    return receive(response);
  };
  observer.attach();
  let configured = false;
  const methods = [];
  const markup = `<!doctype html><meta charset="utf-8"><style>body{margin:10px}section{max-width:100%}</style>
    <c-sl-grok-chat-app style="display:block">
    <button id="setup">Setup</button><section role="region" aria-label="Setup status">missing</section>
    <label>Named credential<input id="credential"></label><label>Model<input id="model"></label>
    <button id="save">Save setup</button><button id="test">Test connection</button>
    <button id="recheck">Recheck setup</button><button id="new">New conversation</button>
    <section role="region" aria-label="Conversation"><label>Message<input></label></section>
    </c-sl-grok-chat-app>
    <script>
    let serial=0;
    async function rpc(method,params={}) {
      const response=await fetch('/aura',{method:'POST',body:JSON.stringify({actions:[{
        id:'req-'+(++serial)+';a',descriptor:'aura://ApexActionController/ACTION$execute',
        params:{classname:'SLGrokChatController',method,params}}]})});
      const data=await response.json();
      const result=JSON.parse(data.actions[0].returnValue.returnValue);
      if(method==='getSetup'||method==='saveSetup')
        document.querySelector('[aria-label="Setup status"]').textContent=result.status;
      return result;
    }
    document.getElementById('save').onclick=async()=>{
      if(${JSON.stringify(phase)}==='before') await rpc('beginMessage',{conversationId:'a01000000000001AAA',message:'too soon'});
      await rpc('saveSetup',{namedCredential:document.getElementById('credential').value,
        model:document.getElementById('model').value});
      if(${JSON.stringify(phase)}==='after') await rpc('beginMessage',{conversationId:'a01000000000001AAA',message:'setup saved'});
    };
    document.getElementById('test').onclick=()=>rpc('testConnection');
    document.getElementById('recheck').onclick=()=>rpc('getSetup');
    document.getElementById('new').onclick=()=>rpc('newConversation');
    rpc('getSetup');
    </script>`;
  await page.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    assert.equal(url.hostname, host, 'The fixture must not access an external service');
    if (url.pathname !== '/aura') return route.fulfill({ contentType: 'text/html', body: markup });
    const actions = JSON.parse(request.postData()).actions.map(action => {
      const method = action.params.method;
      methods.push(method);
      if (method === 'saveSetup') configured = true;
      const value = method === 'testConnection' ? { status: 'ok', model: 'grok-4.7' }
        : method === 'newConversation' ? { conversationId: 'a01000000000001AAA' }
          : method === 'beginMessage' ? { status: 'working' }
            : { status: configured ? 'ready' : 'missing', canConfigure: true,
              namedCredential: configured ? 'Grok_Chat_Model' : null, model: configured ? 'grok-4.7' : null };
      return { id: action.id, state: 'SUCCESS',
        returnValue: { returnValue: JSON.stringify(value), cacheable: false } };
    });
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ actions }) });
  });
  try {
    await page.goto('https://' + host + '/lightning/n/SLGrokChat_Chat');
    await observer.waitFor('getSetup');
    const screenshots = Object.fromEntries(['setup-missing', 'setup-desktop', 'setup-narrow']
      .map(name => [name, path.join(folder, name + '.png')]));
    let result = null;
    let reason = null;
    try {
      result = await driver.runStep({ step: 'setup', mode: 'run', phase: 'builder',
        source_head: 'a'.repeat(40), candidate_metadata_sha256: 'b'.repeat(64), screenshots,
        named_credential: 'Grok_Chat_Model', model: 'grok-4.7', run_id: 'synthetic' },
      { page, browser, providerCalls: () => [] }, observer);
    } catch (error) { reason = error.reason || String(error); }
    if (phase === 'before') {
      assert.equal(reason, 'chat-attempted-before-setup');
      assert.equal(result, null);
      assert.ok(methods.indexOf('beginMessage') < methods.indexOf('saveSetup'));
      assert.ok(!methods.includes('testConnection'), 'The failing setup must stop before provider testing');
    } else {
      assert.equal(reason, null);
      assert.equal(result.setup_missing_without_chat_attempt, true);
      assert.ok(methods.includes('newConversation'));
      if (phase === 'after') {
        assert.ok(methods.indexOf('saveSetup') < methods.indexOf('beginMessage'));
        assert.equal(observer.chatRequests.filter(call => call.method === 'beginMessage').length, 1);
      }
    }
    return { phase, outcome: phase === 'before' ? reason : result.status };
  } finally {
    await context.close();
    await fs.rm(folder, { recursive: true });
  }
}

async function main() {
  const { chromium } = browserTools.playwrightModule();
  const executablePath = browserTools.browserExecutable();
  const browser = await chromium.launch({ headless: true,
    ...(executablePath ? { executablePath } : {}),
    args: ['--password-store=basic', '--use-mock-keychain', '--disable-features=DialMediaRouteProvider'] });
  try {
    const results = [];
    for (const phase of ['none', 'before', 'after']) results.push(await scenario(browser, phase));
    process.stdout.write(JSON.stringify({ status: 'PASS', scenarios: results, browser: browser.version() }) + '\n');
  } finally { await browser.close(); }
}

main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1; });
