'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');

const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'dispatcher-package-')));
const repo = path.resolve(__dirname, '..');
const copied = path.join(root, 'copied-skill');
const unrelated = path.join(root, 'unrelated-cwd');
fs.cpSync(path.join(repo, 'skills/plan-dispatcher'), copied, {recursive: true});
fs.mkdirSync(unrelated);
const helper = path.join(copied, 'scripts/dispatch.js');
const STATE_FILE = 'plan-dispatcher-state.json';
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const save = value => {
  const file = path.join(root, crypto.randomUUID() + '.json');
  fs.writeFileSync(file, JSON.stringify(value)); return file;
};
const evidence = value => {const file = save(value); return {path:file, sha256:digest(fs.readFileSync(file))};};
function cli(op, run, input, fails = false) {
  let inputFile;
  if (input !== undefined) {
    inputFile = op === 'report' ? path.join(run,'artifacts',input.attempt,'envelope.json') : save(input);
    if (op === 'report') fs.writeFileSync(inputFile,JSON.stringify(input));
  }
  const child = spawnSync(process.execPath, [helper, op, run, ...(inputFile === undefined ? [] : [inputFile])],
    {cwd:unrelated, encoding:'utf8', timeout:15000});
  assert.ifError(child.error);
  if (fails) {assert.notEqual(child.status, 0); return JSON.parse(child.stderr);}
  assert.equal(child.status, 0, child.stderr); assert.equal(child.stderr, ''); return JSON.parse(child.stdout);
}
function followNext(response, run) {
  assert.deepEqual(response.next_argv,[process.execPath,helper,'next',run]);
  const child=spawnSync(response.next_argv[0],response.next_argv.slice(1),
    {cwd:unrelated,encoding:'utf8',timeout:15000});
  assert.ifError(child.error);assert.equal(child.status,0,child.stderr);assert.equal(child.stderr,'');
  const next=JSON.parse(child.stdout);
  assert.deepEqual(next.next_argv,response.next_argv);
  assert.equal(typeof next.instruction,'string');assert.match(next.instruction,/\S/);
  return next;
}
function followInstruction(response, run) {
  assert.equal(typeof response.instruction,'string');assert.match(response.instruction,/\S/);
  return followNext(response,run);
}
function assertTaskOnlyReport(response) {
  assert.match(response.instruction,/return this exact response, including its next_argv, to the parent dispatcher phase/i);
  assert.match(response.instruction,/do not execute next_argv, navigate the graph, perform dispatcher acceptance verification of this receipt, settle/i);
  assert.doesNotMatch(response.instruction,/do not execute next_argv, navigate the graph, verify(?:,| or)/i);
  assert.doesNotMatch(response.instruction,/acknowledge (?:the )?task label|pending-job|independently check|before acceptance/i);
}
function assertParentVerification(action, {mainContext = false} = {}) {
  assert.equal(action.action,'verify');
  assert.match(action.instruction,/parent dispatcher phase owns this returned report/i);
  assert.match(action.instruction,/acknowledge (?:its )?task label and reported outcome/i);
  assert.match(action.instruction,/read the returned summary, its declared supporting files, and the evidence needed for the current decision/i);
  assert.match(action.instruction,/preserve relevant findings, open questions and surviving evidence locators in the existing parent handoff/i);
  assert.match(action.instruction,/if the enclosing workflow archives results, use those archived locations after import/i);
  assert.match(action.instruction,/definition.of.done|definition-of-done/i);
  assert.match(action.instruction,/before settlement|only then settle/i);
  assert.match(action.instruction,/Check the returned per-item receipt \(the result artifact's `criteria`\) against each definition_of_done item, and independently rerun or inspect each item's confirmation/);
  assert.match(action.instruction,/Reject when a confirmable item failed or was not confirmed, naming the items/);
  assert.match(action.instruction,/`inspected` or `unconfirmable` whose `Confirm by:` required execution[^.]*: treat it as BLOCKED for planning, not as accepted/);
  assert.match(action.instruction,/BLOCKED result with a proven-unachievable item goes back to planning[^.]*not to a blind retry/);
  if (mainContext) {
    assert.match(action.instruction,/all task-owned commands have finished/i);
    assert.match(action.instruction,/distinct main-context verification phase/i);
    assert.match(action.instruction,/do not wait for a native task/i);
  } else {
    assert.match(action.instruction,/pending-job entry/i);
    assert.match(action.instruction,/confirm native completion and that the worker has stopped/i);
  }
}
function assertExitCriteria(instructions) {
  assert.match(instructions,/Exit criteria: the definition_of_done items are your exit criteria/);
  assert.match(instructions,/record for each item the command or inspection that confirms it and what counts as a pass/);
  assert.match(instructions,/Use the item's `Confirm by:` method when it has one/);
  assert.match(instructions,/Never download, install, or fetch a tool, runtime, or dependency to confirm an item/);
  assert.match(instructions,/leave that check failing and report the discrepancy/);
  assert.match(instructions,/After your last edit to any file, rerun every check in one pass; only that pass counts/);
  assert.match(instructions,/change the work, not the check/);
  assert.match(instructions,/\u2192 SUCCEEDED; an item proven unachievable \u2192 BLOCKED; the same check still failing after 3 genuine fix attempts \u2192 FAILED/);
  assert.match(instructions,/with the existing behavior kept at the conflict point/);
  assert.match(instructions,/every item confirmed or inspected, or reported `unconfirmable` when its definition_of_done text already says `Confirm by: unconfirmable here`, and none failed \u2192 SUCCEEDED/);
  assert.match(instructions,/authority that is absent, for an item the plan did not already mark `Confirm by: unconfirmable here`/);
  assert.match(instructions,/Missing input means BLOCKED; never guess/);
  assert.match(instructions,/report actual checks and output artifact or commit identity/i);
  assert.match(instructions,/`criteria` array with one entry per definition_of_done item, each `\{criterion, check, observed, level\}`/);
  assert.match(instructions,/`confirmed`, `inspected`, `failed`, `not_run`, or `unconfirmable`/);
  assert.match(instructions,/`discrepancies` and `recommendations`/);
  assert.doesNotMatch(instructions,/Achieve the definition of done/);
}
const contract = id => ({task:`Implement ${id}`, ready:[`Inputs for ${id} verified`], done:[`${id} independently checked`]});
const graph = () => ({version:1, steps:[{id:'B',deps:[],contract:contract('B')},{id:'C',deps:[],contract:contract('C')},{id:'D',deps:['B','C'],contract:contract('D')}]});
const singleGraph = () => ({version:1,steps:[{id:'B',deps:[],contract:contract('B')}]});
const cascadeGraph = () => ({version:1, steps:[
  {id:'A',deps:[],contract:contract('A')},
  {id:'B',deps:['A'],contract:contract('B')},
  {id:'C',deps:['A'],contract:contract('C')},
  {id:'D',deps:['B'],contract:contract('D')},
  {id:'E',deps:['B'],contract:contract('E')},
  {id:'J',deps:['C','D','E'],contract:contract('J')},
]});
function initialize(g=graph()) {
  const dir=path.join(root,crypto.randomUUID()); const view=cli('init',dir,{owner:'parent',graph:g}); return {dir,view};
}
function context() {
  const workspace=path.join(root,crypto.randomUUID());fs.mkdirSync(workspace);
  return {workspace,write_scope:['src/result.cjs'],resources:[],ready_evidence:evidence({checked:true})};
}
function complete(dir, attempt, status='SUCCEEDED', passed=true) {
  const launched=cli('start',dir,{owner:'parent',attempt,context:context()});
  cli('launched',dir,{owner:'parent',attempt,handle:'fixture-'+attempt});
  fs.writeFileSync(launched.packet.outputs.artifact, JSON.stringify({actual:42}));
  const envelope={run_id:launched.run_id,step:launched.step,attempt,status,evidence:{path:launched.packet.outputs.artifact,sha256:digest(fs.readFileSync(launched.packet.outputs.artifact))}};
  fs.writeFileSync(launched.packet.outputs.envelope,JSON.stringify(envelope));
  const before=fs.readFileSync(path.join(dir, STATE_FILE));
  const argv=launched.packet.report_argv;
  const child=spawnSync(argv[0],argv.slice(1),{cwd:unrelated,encoding:'utf8',timeout:15000});
  assert.ifError(child.error);assert.equal(child.status,0,child.stderr);
  const receipt=JSON.parse(child.stdout);
  assert.deepEqual(fs.readFileSync(path.join(dir, STATE_FILE)),before);
  const verification={receipt_sha256:receipt.sha256,passed,reason:'Independent fixture result inspection',evidence:evidence({actual:42,passed})};
  const result=cli('settle',dir,{owner:'parent',attempt,verification});
  return {result,envelope,verification};
}
let count=0,success=false;
function test(name, fn) {fn();count++;console.log('PASS '+name);}
try {
  test('portable card has required discovery fields and all package references resolve',()=>{
    const card=fs.readFileSync(path.join(copied,'SKILL.md'),'utf8');
    const front=card.match(/^---\n([\s\S]*?)\n---\n/);assert.ok(front);
    assert.match(front[1],/^name: plan-dispatcher$/m);assert.match(front[1],/^description: >-$/m);
    const keys=front[1].split('\n').filter(line=>/^\S/.test(line)).map(line=>line.split(':')[0]);
    assert.ok(keys.every(key=>['name','description','version','author','license','platforms','metadata'].includes(key)));
    for(const link of card.matchAll(/\]\((references\/[^)#]+)(?:#[^)]+)?\)/g)) {
      assert.equal(fs.statSync(path.join(copied,link[1])).isFile(),true);
    }
    assert.equal(fs.statSync(helper).isFile(),true);
  });
  test('generic provenance cannot substitute inherited or non-array packet bindings',()=>{
    const bindings=[{need:'repository exists',from:null}];
    for(const [inputs,expected] of [[{},[]],[{toString:bindings},bindings],[{toString:'opaque provenance'},[]]]) {
      const g={version:1,source:{inputs},steps:[{id:'toString',deps:[],contract:contract('toString')}]};
      const {dir}=initialize(g),claimed=cli('claim',dir,{owner:'parent',steps:['toString']});
      assert.deepEqual(claimed.packets[0].input_bindings,expected);
      const recovered=cli('packet',dir,{attempt:claimed.claims[0].attempt}).packet;
      assert.deepEqual(recovered.input_bindings,expected);
      assert.deepEqual(recovered,claimed.packets[0]);
    }
  });
  test('copied package outside checkout rejects missing contracts and relative run paths',()=>{
    const invalid=path.join(root,'invalid');
    assert.match(cli('init',invalid,{owner:'parent',graph:{version:1,steps:[{id:'B',deps:[]}]}},true).error,/contract/);
    assert.equal(fs.existsSync(invalid),false);
    assert.match(cli('init','relative',{owner:'parent',graph:graph()},true).error,/absolute/);
    assert.match(cli('next',root,{unexpected:true},true).error,/no input/);
    assert.match(cli('nonsense',root,{},true).error,/unknown operation/);
  });
  test('next and claim remain advisory until start and reject unknown request fields',()=>{
    const {dir,view}=initialize();assert.deepEqual(view.ready,['B','C']);assert.equal(view.complete,false);
    const claimAction=view.actions.find(a=>a.action==='claim');
    assert.deepEqual(claimAction.steps,['B','C']);
    assert.match(claimAction.instruction,/serial capacity one for main-context work/);
    assert.match(claimAction.instruction,/fill every available slot before waiting/);
    assert.match(cli('claim',dir,{owner:'parent',steps:['B'],extra:true},true).error,/expected fields/);
    const claimed=cli('claim',dir,{owner:'parent',steps:['B']});assert.equal(claimed.action,'prepare');
    assert.equal(claimed.packets[0].context,null);assert.equal(claimed.packets[0].native_handle,null);
    assert.equal(Object.hasOwn(claimed.packets[0],'executor'),false);
    assert.deepEqual(cli('next',dir).ready,['C']);assert.equal(cli('next',dir).active[0].recovery,'start');
  });
  test('Ask-Agent full-capability-gated Git preparation stays parent-owned through one native launch',()=>{
    const {dir}=initialize(singleGraph());
    const claimed=cli('claim',dir,{owner:'parent',steps:['B']});
    assert.match(claimed.instruction,/Every Ask-Agent delegation binds the selected package, runs capabilities --skill-card ABS/i);
    assert.match(claimed.instruction,/schema shiploop-chain-ask-agent-managed-worktree\/v1 with the full current capability set/i);
    assert.match(claimed.instruction,/the capability set is the gate, not a version number/i);
    assert.doesNotMatch(claimed.instruction,/semantic version|>=\s*0\.6/i);
    for(const capability of ['helper-managed-worktree','prepared-inspection','returned-commit-delivery','fingerprint-bound-close','ignored-output-report']) assert.match(claimed.instruction,new RegExp(capability));
    assert.match(claimed.instruction,/For every Git claim, including main-context work.*helper prepare, inspect --phase prepared, then start/i);
    assert.match(claimed.instruction,/preparation receipt.*parent pending-job record/i);
    assert.match(claimed.instruction,/Standalone Dispatcher uses ready_evidence; ShipLoop preserves caller ready_evidence.*attempt-bound preparation\/allocation record/i);
    assert.match(claimed.instruction,/Non-Git work retains its existing generic context under the same compatible selected package and does not invoke managed workspace preparation/i);
    const assigned=context();
    const started=cli('start',dir,{owner:'parent',attempt:claimed.claims[0].attempt,context:assigned});
    assert.equal(started.action,'launch');
    assert.deepEqual(Object.keys(started.packet.context).sort(),['ready_evidence','resources','workspace','write_scope']);
    assert.match(started.instruction,/first action=launch permits direct native launch only with the same declared capability response.*full current capability set.*ignored-output-report\).*selected package binding, identity, preparation receipt, frozen context\.workspace and complete assignment/i);
    assert.match(started.instruction,/complete returned worker packet unchanged.*compact Current learnings block/i);
    assert.match(started.instruction,/Markdown heading and short labeled bullets/i);
    assert.match(started.instruction,/say explicitly if none are relevant/i);
    assert.match(started.instruction,/retain the effective assignment and launch identity in the existing parent record or retained handoff, durably outside the worker workspace/i);
    const workerGuidance=started.packet.instructions.join(' ');
    assert.match(workerGuidance,/already-started native worker for this attempt.*execute in this workspace/i);
    assert.match(workerGuidance,/available tools, skills, permissions and execution facilities within the assigned task authorization/i);
    assert.match(workerGuidance,/bounded worker, not the Ask-Agent parent: do not rerun preparation or create a worktree/i);
    assert.match(workerGuidance,/check-context --receipt.*observed command cwd and Git root; both must match context\.workspace/i);
    assert.match(workerGuidance,/self-contained handoff.*material discoveries.*corrected assumptions.*decisions.*concise rationale.*checks actually performed.*unresolved questions/i);
    assert.match(workerGuidance,/state when there are no material new findings/i);
    assert.doesNotMatch(workerGuidance,/Parent launch contract|Parent status contract|Before becoming waiting-only|current-session wakeup|pending-job record/i);
    const protocol=fs.readFileSync(path.join(copied,'references/protocol.md'),'utf8');
    assert.match(protocol,/Every Ask-Agent delegation selects a compatible package before execution/i);
    assert.match(protocol,/shiploop-chain-ask-agent-managed-worktree\/v1[\s\S]*fingerprint-bound-close[\s\S]*ignored-output-report/i);
    assert.doesNotMatch(protocol,/at least `?0\.6\.0|>=\s*0\.6/i);
    assert.match(protocol,/Non-Git tasks use the same compatible selected package[\s\S]*without managed workspace preparation/i);
    assert.doesNotMatch(protocol,/Ask-Agent 0\.4|legacy caller-prepared/i);
    assert.match(protocol,/replacement attempt needs a fresh[\s\S]*preparation receipt before it can start/i);
  });
  test('ready and reserved work precede collection of an already running worker',()=>{
    const {dir}=initialize();
    const b=cli('claim',dir,{owner:'parent',steps:['B']}).claims[0];
    cli('start',dir,{owner:'parent',attempt:b.attempt,context:context()});
    assert.deepEqual(cli('next',dir).actions.map(a=>a.action),['claim','reconcile']);
    cli('launched',dir,{owner:'parent',attempt:b.attempt,handle:'running-B'});
    const ready=cli('next',dir);
    assert.deepEqual(ready.actions.map(a=>a.action),['claim','collect']);
    assert.deepEqual(ready.actions[0].steps,['C']);
    const c=cli('claim',dir,{owner:'parent',steps:['C']}).claims[0];
    const reserved=cli('next',dir);
    assert.deepEqual(reserved.actions.map(a=>a.action),['start','collect']);
    assert.equal(reserved.actions[0].attempt,c.attempt);
    assert.equal(reserved.actions[1].attempt,b.attempt);
    assert.deepEqual(reserved.ready,[]);
  });
  test('ready work precedes native verification while serial resume retains priority',()=>{
    const {dir}=initialize();
    const b=cli('claim',dir,{owner:'parent',steps:['B']}).claims[0];
    const started=cli('start',dir,{owner:'parent',attempt:b.attempt,context:context()});
    cli('launched',dir,{owner:'parent',attempt:b.attempt,handle:'returned-B'});
    fs.writeFileSync(started.packet.outputs.artifact,JSON.stringify({actual:'B'}));
    cli('report',dir,{run_id:started.run_id,step:'B',attempt:b.attempt,status:'SUCCEEDED',
      evidence:{path:started.packet.outputs.artifact,sha256:digest(fs.readFileSync(started.packet.outputs.artifact))}});
    const reported=cli('next',dir);
    assert.deepEqual(reported.actions.map(a=>a.action),['claim','verify']);
    assert.deepEqual(reported.actions[0].steps,['C']);
    assert.equal(reported.actions[1].attempt,b.attempt);
    assert.deepEqual(reported.accepted,[],'a native return is not acceptance');

    const serial=initialize();
    const local=cli('claim',serial.dir,{owner:'parent',steps:['B']}).claims[0];
    cli('start',serial.dir,{owner:'parent',attempt:local.attempt,context:context(),
      executor:{kind:'main-context',id:'serial-parent'}});
    const resumed=cli('next',serial.dir);
    assert.deepEqual(resumed.actions.map(a=>a.action),['resume','claim']);
    assert.equal(resumed.actions[0].attempt,local.attempt);
  });
  test('every successful run operation returns an actionable instruction and exact continuation',()=>{
    const directDir=path.join(root,crypto.randomUUID());
    const direct=require(helper).run('init',directDir,{owner:'direct-parent',graph:singleGraph()});
    assert.deepEqual(direct.next_argv,[process.execPath,helper,'next',directDir]);
    assert.equal(typeof direct.instruction,'string');assert.match(direct.instruction,/\S/);
    const {dir,view:init}=initialize(singleGraph());
    assert.deepEqual(followInstruction(init,dir).ready,['B']);

    const contextCheck=cli('check-context',dir,{step:'B'});
    assert.match(contextCheck.instruction,/read-only planning-context check/i);
    assert.match(contextCheck.instruction,/preserve the reported availability or blocker/i);
    assert.deepEqual(followInstruction(contextCheck,dir).ready,['B']);

    let owner='parent';
    const claimed=cli('claim',dir,{owner,steps:['B']});
    assert.match(claimed.instruction,/only these exact claims/i);
    assert.match(claimed.instruction,/packet alone never launches work/i);
    assert.equal(followInstruction(claimed,dir).active[0].recovery,'start');
    const attempt=claimed.claims[0].attempt;
    const claimedPacket=cli('packet',dir,{attempt});
    assert.match(claimedPacket.instruction,/read-only packet inspection/i);
    assert.match(claimedPacket.instruction,/does not authorize a launch/i);
    assert.equal(followInstruction(claimedPacket,dir).active[0].recovery,'start');
    const assigned=context();
    const started=cli('start',dir,{owner,attempt,context:assigned});
    assert.equal(started.action,'launch');
    assert.match(started.instruction,/launch authorization is exactly once/i);
    assert.equal(followInstruction(started,dir).active[0].recovery,'reconcile');
    const recovered=cli('packet',dir,{attempt});
    assert.equal(recovered.action,'inspect');
    assert.equal(followInstruction(recovered,dir).active[0].recovery,'reconcile');
    const replayStart=cli('start',dir,{owner,attempt,context:assigned});
    assert.equal(replayStart.action,'reconcile');
    assert.match(replayStart.instruction,/does not authorize another launch/i);
    assert.equal(followInstruction(replayStart,dir).active[0].recovery,'reconcile');

    const launched=cli('launched',dir,{owner,attempt,handle:'fixture-'+attempt});
    assert.equal(followInstruction(launched,dir).active[0].recovery,'collect');
    const taken=cli('takeover',dir,{oldOwner:owner,newOwner:'parent-2',confirmed_stopped:true,reason:'fixture parent handoff'});
    owner='parent-2';
    assert.match(taken.instruction,/execute the exact returned next_argv and obey its new actions/i);
    assert.equal(followInstruction(taken,dir).active[0].recovery,'collect');

    const publish = (packet, status) => {
      fs.writeFileSync(packet.outputs.artifact,JSON.stringify({actual:status}));
      const envelope={run_id:packet.run_id,step:packet.step,attempt:packet.attempt,status,
        evidence:{path:packet.outputs.artifact,sha256:digest(fs.readFileSync(packet.outputs.artifact))}};
      fs.writeFileSync(packet.outputs.envelope,JSON.stringify(envelope));
      const child=spawnSync(packet.report_argv[0],packet.report_argv.slice(1),
        {cwd:unrelated,encoding:'utf8',timeout:15000});
      assert.ifError(child.error);assert.equal(child.status,0,child.stderr);assert.equal(child.stderr,'');
      return JSON.parse(child.stdout);
    };
    const reported=publish(started.packet,'FAILED');
    assert.match(reported.instruction,/actual inbox receipt response/i);
    assertTaskOnlyReport(reported);
    const reportNext=followInstruction(reported,dir);
    assertParentVerification(reportNext.actions.find(action=>action.attempt===attempt));
    const receipt=cli('receipt',dir,{attempt});
    assert.match(receipt.instruction,/read-only immutable receipt lookup/i);
    assert.match(receipt.instruction,/does not confirm worker completion/i);
    assert.equal(followInstruction(receipt,dir).active[0].recovery,'verify');
    const rejected=cli('settle',dir,{owner,attempt,verification:{receipt_sha256:reported.sha256,passed:false,
      reason:'fixture verifier rejected',evidence:evidence({passed:false})}});
    assert.equal(rejected.step,'B');
    assert.equal(rejected.attempt.attempt,attempt);
    assert.equal(followInstruction(rejected,dir).active[0].recovery,'retry');
    const retried=cli('retry',dir,{owner,attempt,confirmed_stopped:true,reason:'fixture worker stopped'});
    assert.match(retried.instruction,/execute the exact returned next_argv and obey its new actions/i);
    assert.deepEqual(followInstruction(retried,dir).ready,['B']);

    const replacement=cli('claim',dir,{owner,steps:['B']});
    assert.equal(followInstruction(replacement,dir).active[0].recovery,'start');
    const replacementAttempt=replacement.claims[0].attempt;
    const replacementStart=cli('start',dir,{owner,attempt:replacementAttempt,context:context()});
    assert.equal(replacementStart.action,'launch');
    assert.equal(followInstruction(replacementStart,dir).active[0].recovery,'reconcile');
    const replacementLaunch=cli('launched',dir,{owner,attempt:replacementAttempt,handle:'fixture-'+replacementAttempt});
    assert.equal(followInstruction(replacementLaunch,dir).active[0].recovery,'collect');
    const acceptedReport=publish(replacementStart.packet,'SUCCEEDED');
    assert.equal(followInstruction(acceptedReport,dir).active[0].recovery,'verify');
    const complete=cli('settle',dir,{owner,attempt:replacementAttempt,verification:{receipt_sha256:acceptedReport.sha256,passed:true,
      reason:'fixture verifier accepted',evidence:evidence({passed:true})}});
    assert.equal(complete.complete,true);
    assert.equal(followInstruction(complete,dir).complete,true);
  });
  test('cold start packet carries exact task, attempt, ownership and helper binding',()=>{
    const {dir}=initialize(),claim=cli('claim',dir,{owner:'parent',steps:['B']});
    const attempt=claim.claims[0].attempt, assigned=context();
    const started=cli('start',dir,{owner:'parent',attempt,context:assigned});
    assert.equal(started.action,'launch');assert.equal(started.packet.step,'B');
    assert.deepEqual(started.packet.definition_of_ready,contract('B').ready);
    assert.deepEqual(started.packet.definition_of_done,contract('B').done);
    assert.equal(started.packet.context.workspace,fs.realpathSync(assigned.workspace));
    assert.deepEqual(started.packet.context.write_scope,assigned.write_scope);
    const instructions=started.packet.instructions.join('\n');
    assert.match(instructions,/Further native delegation must preserve/);
    assert.match(instructions,/collect all delegates before reporting completion/);
    assert.match(instructions,/already-started native worker for this attempt.*execute in this workspace/i);
    assert.match(instructions,/available tools, skills, permissions and execution facilities/);
    assert.match(instructions,/do not rerun preparation or create a worktree/i);
    assert.match(instructions,/For a non-Git assignment, use the assigned generic workspace and write scope without managed workspace preparation/i);
    assert.match(instructions,/self-contained handoff.*material discoveries.*corrected assumptions.*concise rationale/i);
    assertExitCriteria(instructions);
    assert.equal(Object.hasOwn(started.packet,'prior_attempts'),false);
    assert.doesNotMatch(instructions,/prior_attempts/);
    assert.doesNotMatch(instructions,/Parent launch contract|Parent status contract|fresh general-purpose native worker by default|native observation timeout|current-session wakeup|pending-job record/i);
    assert.match(instructions,/return the actual report response and its next_argv to the parent dispatcher/i);
    assert.match(instructions,/Do not execute that next_argv or navigate the graph/i);
    assert.match(started.instruction,/fresh general-purpose native context/);
    assert.match(started.instruction,/Current learnings/i);
    assert.match(started.instruction,/effective assignment and launch identity.*existing parent record or retained handoff.*durably outside the worker workspace/i);
    assert.equal(started.packet.helper,helper);assert.deepEqual(started.packet.report_argv.slice(0,4),[process.execPath,helper,'report',dir]);
    assert.equal(started.packet.report_argv.at(-1),started.packet.outputs.envelope);
    assert.equal(fs.statSync(started.packet.outputs.directory).isDirectory(),true);
    assert.match(cli('report',dir,{run_id:started.run_id,step:'B',attempt,status:'SUCCEEDED',evidence:evidence({actual:42})},true).error,/outputs.artifact/);
    const recovered=cli('packet',dir,{attempt});assert.equal(recovered.action,'inspect');
    assert.deepEqual(recovered.packet,started.packet);
    assert.equal(cli('start',dir,{owner:'parent',attempt,context:assigned}).action,'reconcile');
    assert.equal(cli('next',dir).active[0].recovery,'reconcile');
  });
  test('emitted recovery guidance separates a report receipt from native completion',()=>{
    const {dir}=initialize(),claim=cli('claim',dir,{owner:'parent',steps:['B']}).claims[0];
    const started=cli('start',dir,{owner:'parent',attempt:claim.attempt,context:context()});
    const launched=cli('launched',dir,{owner:'parent',attempt:claim.attempt,handle:'fixture-pending'});
    assert.match(launched.instruction,/Confirmed native launch/);
    assert.match(launched.instruction,/parent next action/);
    assert.match(launched.instruction,/pending-job record/);
    const collecting=cli('next',dir).actions.find(action=>action.attempt===claim.attempt);
    assert.equal(collecting.action,'collect');
    assert.match(collecting.instruction,/only from native events or collection/);
    assert.match(collecting.instruction,/observation timeout is not completion/);
    assert.match(collecting.instruction,/current-session wakeup/);
    assert.match(collecting.instruction,/never a completion substitute/);
    fs.writeFileSync(started.packet.outputs.artifact,JSON.stringify({actual:'reported-not-collected'}));
    const reported=cli('report',dir,{run_id:started.run_id,step:'B',attempt:claim.attempt,status:'SUCCEEDED',
      evidence:{path:started.packet.outputs.artifact,sha256:digest(fs.readFileSync(started.packet.outputs.artifact))}});
    assert.match(reported.instruction,/actual inbox receipt response/);
    assert.match(reported.instruction,/not native completion, acceptance, or integration/);
    assertTaskOnlyReport(reported);
    const verifying=cli('next',dir).actions.find(action=>action.attempt===claim.attempt);
    assertParentVerification(verifying);
  });
  test('waiting-only recovery supplies status choices without completing or changing the native task',()=>{
    const {dir}=initialize(),claim=cli('claim',dir,{owner:'parent',steps:['B']}).claims[0];
    const started=cli('start',dir,{owner:'parent',attempt:claim.attempt,context:context()});
    cli('launched',dir,{owner:'parent',attempt:claim.attempt,handle:'fixture-still-running'});
    const before=fs.readFileSync(path.join(dir, STATE_FILE));
    const recovered=cli('packet',dir,{attempt:claim.attempt}).packet;
    const view=cli('next',dir),collecting=view.actions.find(action=>action.attempt===claim.attempt);
    for(const guidance of [collecting.instruction]) {
      assert.match(guidance,/Before becoming waiting-only.*native timed collection/);
      assert.match(guidance,/equivalent visible native progress.*current-session wakeup/);
      assert.match(guidance,/user cadence\/quiet preference/);
      assert.match(guidance,/observation timeout.*combined visible pending-job update.*worker keeps running/);
      assert.match(guidance,/no periodic mechanism.*disclose.*before becoming idle.*continue native completion collection/);
      assert.match(guidance,/wakeup is never a completion substitute/);
      assert.match(guidance,/do not create custom timers or external recurring tasks/);
    }
    for(const workerGuidance of [started.packet.instructions.join(' '),recovered.instructions.join(' ')]) {
      assert.match(workerGuidance,/return the actual report response and its next_argv to the parent dispatcher/i);
      assert.doesNotMatch(workerGuidance,/Before becoming waiting-only|native timed collection|current-session wakeup|combined visible pending-job update|custom timers or external recurring tasks/i);
    }
    assert.equal(collecting.action,'collect');assert.equal(view.complete,false);
    assert.deepEqual(fs.readFileSync(path.join(dir, STATE_FILE)),before);
  });
  test('output setup failure leaves claim startable; report rejects an unassigned envelope path',()=>{
    const {dir}=initialize(),claim=cli('claim',dir,{owner:'parent',steps:['B']}).claims[0];
    const assigned=context();fs.writeFileSync(path.join(dir,'artifacts'),'blocked namespace');
    const before=fs.readFileSync(path.join(dir, STATE_FILE));
    assert.match(cli('start',dir,{owner:'parent',attempt:claim.attempt,context:assigned},true).error,/real directory/);
    assert.deepEqual(fs.readFileSync(path.join(dir, STATE_FILE)),before);
    assert.equal(cli('next',dir).active[0].recovery,'start');
    fs.unlinkSync(path.join(dir,'artifacts'));
    const started=cli('start',dir,{owner:'parent',attempt:claim.attempt,context:assigned});
    assert.equal(started.action,'launch');
    const alternate=save({...started.packet.report_envelope,status:'BLOCKED'});
    const child=spawnSync(process.execPath,[helper,'report',dir,alternate],{encoding:'utf8'});
    assert.notEqual(child.status,0);assert.match(JSON.parse(child.stderr).error,/outputs.envelope/);
  });
  test('accepted dependency packets include result and verifier evidence; join waits for both',()=>{
    const {dir}=initialize(),claims=cli('claim',dir,{owner:'parent',steps:['B','C']}).claims;
    const b=complete(dir,claims.find(c=>c.step==='B').attempt);
    assert.deepEqual(b.result.ready,[]);
    const c=complete(dir,claims.find(c=>c.step==='C').attempt);
    assert.deepEqual(c.result.ready,['D']);
    const joined=cli('claim',dir,{owner:'parent',steps:['D']});
    const deps=joined.packets[0].dependencies;
    assert.deepEqual(deps.map(d=>d.step),['B','C']);
    assert.deepEqual(deps[0].result,b.envelope.evidence);assert.deepEqual(deps[0].verification,b.verification.evidence);
    const final=complete(dir,joined.claims[0].attempt);assert.equal(final.result.complete,true);
  });
  test('settlement recomputes a cascade frontier without reoffering reservations',()=>{
    const {dir}=initialize(cascadeGraph());
    const claimActions = view => view.actions.filter(action=>action.action==='claim').map(({action,steps})=>({action,steps}));
    const launch = claim => {
      const started=cli('start',dir,{owner:'parent',attempt:claim.attempt,context:context()});
      cli('launched',dir,{owner:'parent',attempt:claim.attempt,handle:'fixture-'+claim.attempt});
      return started;
    };
    const publish = (started, claim) => {
      fs.writeFileSync(started.packet.outputs.artifact,JSON.stringify({actual:claim.step}));
      const envelope={run_id:started.run_id,step:claim.step,attempt:claim.attempt,status:'SUCCEEDED',
        evidence:{path:started.packet.outputs.artifact,sha256:digest(fs.readFileSync(started.packet.outputs.artifact))}};
      const receipt=cli('report',dir,envelope);
      const verification={receipt_sha256:receipt.sha256,passed:true,reason:'Independent fixture result inspection',
        evidence:evidence({actual:claim.step,passed:true})};
      return {receipt,verification};
    };

    const a=cli('claim',dir,{owner:'parent',steps:['A']}).claims[0];
    const aPublished=publish(launch(a),a);
    const receiptOnly=cli('next',dir);
    assert.deepEqual(receiptOnly.ready,[]);
    assert.deepEqual(claimActions(receiptOnly),[]);
    assert.deepEqual(receiptOnly.active.map(({step,recovery})=>({step,recovery})),[{step:'A',recovery:'verify'}]);
    const afterA=cli('settle',dir,{owner:'parent',attempt:a.attempt,verification:aPublished.verification});
    assert.equal(afterA.outcome,'accepted');
    assert.equal(afterA.step,'A');
    assert.equal(afterA.attempt.attempt,a.attempt);
    assert.deepEqual(afterA.ready,['B','C']);
    assert.deepEqual(claimActions(afterA),[{action:'claim',steps:['B','C']}]);

    const b=cli('claim',dir,{owner:'parent',steps:['B']}).claims[0];
    const afterBClaim=cli('next',dir);
    assert.deepEqual(afterBClaim.ready,['C']);
    assert.deepEqual(claimActions(afterBClaim),[{action:'claim',steps:['C']}]);
    const c=cli('claim',dir,{owner:'parent',steps:['C']}).claims[0];
    const cStarted=launch(c);

    const bDone=complete(dir,b.attempt);
    assert.equal(bDone.result.outcome,'accepted');
    assert.equal(bDone.result.step,'B');
    assert.equal(bDone.result.attempt.attempt,b.attempt);
    assert.deepEqual(bDone.result.ready,['D','E']);
    assert.deepEqual(claimActions(bDone.result),[{action:'claim',steps:['D','E']}]);
    assert.deepEqual(bDone.result.actions.map(a=>a.action),['claim','collect']);
    assert.deepEqual(bDone.result.active.map(({step,recovery})=>({step,recovery})),[{step:'C',recovery:'collect'}]);
    const replay=cli('settle',dir,{owner:'parent',attempt:b.attempt,verification:bDone.verification});
    assert.equal(replay.step,'B');
    assert.equal(replay.attempt.attempt,b.attempt);
    assert.deepEqual(replay.accepted,['A','B']);
    assert.deepEqual(replay.ready,['D','E']);
    assert.deepEqual(claimActions(replay),[{action:'claim',steps:['D','E']}]);

    const d=cli('claim',dir,{owner:'parent',steps:['D']}).claims[0];
    const afterDClaim=cli('next',dir);
    assert.deepEqual(afterDClaim.ready,['E']);
    assert.deepEqual(claimActions(afterDClaim),[{action:'claim',steps:['E']}]);
    const dDone=complete(dir,d.attempt);
    assert.deepEqual(dDone.result.ready,['E']);
    assert.deepEqual(claimActions(dDone.result),[{action:'claim',steps:['E']}]);

    const e=cli('claim',dir,{owner:'parent',steps:['E']}).claims[0];
    const eDone=complete(dir,e.attempt);
    assert.deepEqual(eDone.result.ready,[]);
    assert.deepEqual(claimActions(eDone.result),[]);
    assert.deepEqual(eDone.result.active.map(({step,recovery})=>({step,recovery})),[{step:'C',recovery:'collect'}]);

    const cPublished=publish(cStarted,c);
    const beforeJoin=cli('next',dir);
    assert.deepEqual(beforeJoin.ready,[]);
    assert.deepEqual(claimActions(beforeJoin),[]);
    const afterC=cli('settle',dir,{owner:'parent',attempt:c.attempt,verification:cPublished.verification});
    assert.equal(afterC.step,'C');
    assert.equal(afterC.attempt.attempt,c.attempt);
    assert.deepEqual(afterC.ready,['J']);
    assert.deepEqual(claimActions(afterC),[{action:'claim',steps:['J']}]);
    const j=cli('claim',dir,{owner:'parent',steps:['J']}).claims[0];
    assert.equal(complete(dir,j.attempt).result.complete,true);
  });
  test('copied public CLI rejects shared resources without losing the second claim',()=>{
    const {dir}=initialize();const claims=cli('claim',dir,{owner:'parent',steps:['B','C']}).claims;
    const b=claims.find(c=>c.step==='B'),c=claims.find(c=>c.step==='C');
    const left={...context(),resources:['shared-database']};
    const right={...context(),resources:['shared-database']};
    cli('start',dir,{owner:'parent',attempt:b.attempt,context:left});
    const before=fs.readFileSync(path.join(dir, STATE_FILE));
    assert.match(cli('start',dir,{owner:'parent',attempt:c.attempt,context:right},true).error,/resource|conflict/i);
    assert.deepEqual(fs.readFileSync(path.join(dir, STATE_FILE)),before);
    assert.equal(cli('next',dir).active.find(a=>a.step==='C').recovery,'start');
    assert.equal(cli('start',dir,{owner:'parent',attempt:c.attempt,context:{...right,resources:['isolated-database']}}).action,'launch');
  });
  test('rejected worker success stays blocked until a confirmed stopped fresh retry',()=>{
    const {dir}=initialize(),claim=cli('claim',dir,{owner:'parent',steps:['B']}).claims[0];
    const rejected=complete(dir,claim.attempt,'SUCCEEDED',false);
    assert.equal(rejected.result.outcome,'rejected');assert.deepEqual(rejected.result.ready,['C']);
    assert.match(cli('retry',dir,{owner:'parent',attempt:claim.attempt,confirmed_stopped:false,reason:'not confirmed'},true).error,/confirmed_stopped/);
    cli('retry',dir,{owner:'parent',attempt:claim.attempt,confirmed_stopped:true,reason:'fixture execution has exited'});
    const fresh=cli('claim',dir,{owner:'parent',steps:['B']}).claims[0];assert.notEqual(fresh.attempt,claim.attempt);
    assert.match(cli('report',dir,rejected.envelope,true).error,/stale/);
  });
  test('a retried step packet carries prior attempts oldest first; a first attempt has none',()=>{
    const {dir}=initialize(singleGraph()),first=cli('claim',dir,{owner:'parent',steps:['B']}).claims[0];
    const firstStart=cli('start',dir,{owner:'parent',attempt:first.attempt,context:context()});
    assert.equal(Object.hasOwn(firstStart.packet,'prior_attempts'),false);
    assert.doesNotMatch(firstStart.packet.instructions.join(' '),/prior_attempts/);
    cli('launched',dir,{owner:'parent',attempt:first.attempt,handle:'fixture-'+first.attempt});
    // Retried without a report: no receipt or verification evidence exists.
    cli('retry',dir,{owner:'parent',attempt:first.attempt,confirmed_stopped:true,reason:'worker exited without a report'});
    const second=cli('claim',dir,{owner:'parent',steps:['B']});
    assert.deepEqual(second.packets[0].prior_attempts,[{attempt:first.attempt,status:'NOT_REPORTED',
      reason:'worker exited without a report',result:null,verification:null}]);
    const rejected=complete(dir,second.claims[0].attempt,'SUCCEEDED',false);
    assert.equal(rejected.result.outcome,'rejected');
    assert.match(cli('next',dir).actions.find(a=>a.action==='retry').instruction,/prior_attempts/);
    cli('retry',dir,{owner:'parent',attempt:second.claims[0].attempt,confirmed_stopped:true,reason:'fixture execution has exited'});
    const third=cli('claim',dir,{owner:'parent',steps:['B']}).claims[0];
    const expected=[
      {attempt:first.attempt,status:'NOT_REPORTED',reason:'worker exited without a report',result:null,verification:null},
      {attempt:second.claims[0].attempt,status:'SUCCEEDED',reason:'Independent fixture result inspection',
        result:rejected.envelope.evidence,verification:rejected.verification.evidence},
    ];
    const started=cli('start',dir,{owner:'parent',attempt:third.attempt,context:context()});
    assert.deepEqual(started.packet.prior_attempts,expected);
    assert.deepEqual(cli('packet',dir,{attempt:third.attempt}).packet,started.packet);
    const instructions=started.packet.instructions;
    const priorIndex=instructions.findIndex(text=>/prior_attempts lists this step's earlier attempts, oldest first/.test(text));
    assert.ok(priorIndex>0);
    assert.match(instructions[priorIndex-1],/`criteria` array/);
    assert.match(instructions[priorIndex],/read those results and each reason, and address the named failing items first/);
    assert.match(instructions[priorIndex],/verify each listed result and verification hash/);
    // The projection is read-only: persisted state is unchanged by packet reads.
    const before=fs.readFileSync(path.join(dir, STATE_FILE));
    cli('packet',dir,{attempt:third.attempt});
    assert.deepEqual(fs.readFileSync(path.join(dir, STATE_FILE)),before);
    // A main-context retry carries the same list.
    const serial=initialize(singleGraph()),claim=cli('claim',serial.dir,{owner:'parent',steps:['B']}).claims[0];
    const executor={kind:'main-context',id:'retry-main'};
    const entered=cli('start',serial.dir,{owner:'parent',attempt:claim.attempt,context:context(),executor});
    fs.writeFileSync(entered.packet.outputs.artifact,JSON.stringify({criteria:[{criterion:'B independently checked',check:'node test',observed:'1 failing',level:'failed'}]}));
    const receipt=cli('report',serial.dir,{run_id:entered.run_id,step:'B',attempt:claim.attempt,status:'FAILED',
      evidence:{path:entered.packet.outputs.artifact,sha256:digest(fs.readFileSync(entered.packet.outputs.artifact))}});
    const verification={receipt_sha256:receipt.sha256,passed:false,reason:'failed item: B independently checked',evidence:evidence({passed:false})};
    cli('settle',serial.dir,{owner:'parent',attempt:claim.attempt,verification});
    cli('retry',serial.dir,{owner:'parent',attempt:claim.attempt,confirmed_stopped:true,reason:'serial task finished'});
    const retried=cli('claim',serial.dir,{owner:'parent',steps:['B']}).claims[0];
    const resumed=cli('start',serial.dir,{owner:'parent',attempt:retried.attempt,context:context(),executor});
    assert.deepEqual(resumed.packet.prior_attempts,[{attempt:claim.attempt,status:'FAILED',reason:'failed item: B independently checked',
      result:receipt.envelope.evidence,verification:verification.evidence}]);
    assert.match(resumed.packet.instructions.join(' '),/prior_attempts lists this step's earlier attempts/);
    // A reported attempt retried before settlement keeps its receipt but has no verification.
    const unsettled=initialize(singleGraph()),reported=cli('claim',unsettled.dir,{owner:'parent',steps:['B']}).claims[0];
    const launchedReported=cli('start',unsettled.dir,{owner:'parent',attempt:reported.attempt,context:context()});
    cli('launched',unsettled.dir,{owner:'parent',attempt:reported.attempt,handle:'fixture-'+reported.attempt});
    fs.writeFileSync(launchedReported.packet.outputs.artifact,JSON.stringify({actual:42}));
    const unsettledReceipt=cli('report',unsettled.dir,{run_id:launchedReported.run_id,step:'B',attempt:reported.attempt,status:'FAILED',
      evidence:{path:launchedReported.packet.outputs.artifact,sha256:digest(fs.readFileSync(launchedReported.packet.outputs.artifact))}});
    cli('retry',unsettled.dir,{owner:'parent',attempt:reported.attempt,confirmed_stopped:true,reason:'stopped before settlement'});
    const afterUnsettled=cli('claim',unsettled.dir,{owner:'parent',steps:['B']});
    assert.deepEqual(afterUnsettled.packets[0].prior_attempts,[{attempt:reported.attempt,status:'FAILED',reason:'stopped before settlement',
      result:unsettledReceipt.envelope.evidence,verification:null}]);
  });
  test('early receipt recovery preserves native completion before settlement and resource release',()=>{
    const {dir}=initialize(),claims=cli('claim',dir,{owner:'parent',steps:['B','C']}).claims;
    const b=claims.find(c=>c.step==='B'),c=claims.find(c=>c.step==='C');
    const left={...context(),resources:['shared-database']},right={...context(),resources:['shared-database']};
    const started=cli('start',dir,{owner:'parent',attempt:b.attempt,context:left});
    cli('launched',dir,{owner:'parent',attempt:b.attempt,handle:'fixture-awaiting-native-collection'});
    fs.writeFileSync(started.packet.outputs.artifact,JSON.stringify({actual:42}));
    const envelope={run_id:started.run_id,step:'B',attempt:b.attempt,status:'SUCCEEDED',
      evidence:{path:started.packet.outputs.artifact,sha256:digest(fs.readFileSync(started.packet.outputs.artifact))}};
    const receipt=cli('report',dir,envelope);
    const before=fs.readFileSync(path.join(dir, STATE_FILE));
    const view=cli('next',dir),action=view.actions.find(a=>a.attempt===b.attempt);
    assert.equal(action.action,'verify');
    const recovered=cli('packet',dir,{attempt:b.attempt}).packet;
    // Parent verification retains completion/settlement prerequisites; the worker
    // keeps only bounded task collection and report-return obligations.
    assert.match(action.instruction,/confirm.*native completion.*worker.*stopped.*before.*settl/i);
    assert.match(action.instruction,/releas.*(?:workspace|resource)/i);
    const workerGuidance=recovered.instructions.join(' ');
    assert.match(workerGuidance,/collect all delegates before reporting completion/i);
    assert.match(workerGuidance,/return the actual report response and its next_argv to the parent dispatcher/i);
    assert.doesNotMatch(workerGuidance,/confirm.*native completion.*worker.*stopped.*before.*settl/i);
    assert.doesNotMatch(workerGuidance,/releas.*(?:workspace|resource)/i);
    assert.deepEqual(fs.readFileSync(path.join(dir, STATE_FILE)),before);
    assert.match(cli('start',dir,{owner:'parent',attempt:c.attempt,context:right},true).error,/resource/);
    // Native liveness is a caller precondition; this fixture only exercises the
    // protocol and resource gate, not actual host termination detection.
    cli('settle',dir,{owner:'parent',attempt:b.attempt,verification:{receipt_sha256:receipt.sha256,
      passed:true,reason:'Fixture caller completed collection and done checks',
      evidence:evidence({actual:42,collection:'simulated stopped confirmation'})}});
    assert.equal(cli('start',dir,{owner:'parent',attempt:c.attempt,context:right}).action,'launch');
  });
  test('serial main-context start is handle-free, packeted, and separately verified',()=>{
    const {dir}=initialize(),claim=cli('claim',dir,{owner:'parent',steps:['B']}).claims[0];
    const assigned=context(),executor={kind:'main-context',id:'shiploop-serial-main'};
    const started=cli('start',dir,{owner:'parent',attempt:claim.attempt,context:assigned,executor});
    assert.equal(started.action,'execute');assert.equal(started.status,'running');assert.equal(started.handle,null);
    assert.deepEqual(started.executor,executor);assert.equal(started.packet.native_handle,null);assert.deepEqual(started.packet.executor,executor);
    assert.match(started.instruction,/same capability-gated helper-prepared frozen context and receipt recorded before start/i);
    assert.match(started.instruction,/do not repeat package binding, capability\/identity checks, preparation, or worktree allocation/i);
    for(const guidance of [started.instruction,cli('next',dir).actions.find(a=>a.attempt===claim.attempt).instruction]) {
      assert.match(guidance,/current main (?:context|conversation)|current conversation/i);
      assert.match(guidance,/do not call ask-agent/i);
      assert.match(guidance,/native worker|native completion/i);
    }
    const serialWorkerGuidance=started.packet.instructions.join(' ');
    assert.match(serialWorkerGuidance,/performing this bounded task in the current conversation/i);
    assert.doesNotMatch(serialWorkerGuidance,/current dispatcher must confirm it may resume or complete/i);
    assert.doesNotMatch(serialWorkerGuidance,/Parent status presentation|Before becoming waiting-only|current-session wakeup|pending-job record/i);
    assert.match(started.instruction,/report handoff ends this bounded task phase/i);
    assert.match(started.instruction,/return the actual report response, including its next_argv, to the dispatcher phase/i);
    assert.match(started.instruction,/same conversation.*distinct verification phase/i);
    assert.match(started.instruction,/do not execute next_argv, navigate the graph, perform dispatcher acceptance verification of the resulting receipt, or settle/i);
    assert.doesNotMatch(started.instruction,/do not execute next_argv, navigate the graph, verify(?:,| or)/i);
    assert.doesNotMatch(started.instruction,/perform a distinct verification phase before settlement/i);
    assert.match(serialWorkerGuidance,/return the actual report response and its next_argv to the parent dispatcher loop/i);
    assert.match(serialWorkerGuidance,/do not execute that next_argv, navigate the graph, perform dispatcher acceptance verification of the receipt, or settle/i);
    assert.doesNotMatch(serialWorkerGuidance,/do not execute that next_argv, navigate the graph, verify(?:,| or)/i);
    assert.equal(cli('next',dir).actions.find(a=>a.attempt===claim.attempt).action,'resume');
    assert.equal(cli('start',dir,{owner:'parent',attempt:claim.attempt,context:assigned,executor}).action,'reconcile');
    const before=fs.readFileSync(path.join(dir, STATE_FILE));
    assert.match(cli('start',dir,{owner:'parent',attempt:claim.attempt,context:assigned,executor:{...executor,id:'other-main'}},true).error,/execution identity/i);
    assert.match(cli('launched',dir,{owner:'parent',attempt:claim.attempt,handle:'synthetic'},true).error,/main-context/i);
    assert.deepEqual(fs.readFileSync(path.join(dir, STATE_FILE)),before);
    fs.writeFileSync(started.packet.outputs.artifact,JSON.stringify({actual:42}));
    const receipt=cli('report',dir,{run_id:started.run_id,step:'B',attempt:claim.attempt,status:'SUCCEEDED',
      evidence:{path:started.packet.outputs.artifact,sha256:digest(fs.readFileSync(started.packet.outputs.artifact))}});
    assert.match(receipt.instruction,/For a main-context attempt, make that handoff within the same conversation/i);
    assert.deepEqual(receipt.next_argv,[process.execPath,helper,'next',dir]);
    assertTaskOnlyReport(receipt);
    const verify=cli('next',dir).actions.find(a=>a.attempt===claim.attempt);
    assertParentVerification(verify,{mainContext:true});
    assert.match(verify.instruction,/separate agent is not required/i);
    const settled=cli('settle',dir,{owner:'parent',attempt:claim.attempt,verification:{receipt_sha256:receipt.sha256,
      passed:true,reason:'Independent serial fixture check',evidence:evidence({actual:42,passed:true})}});
    assert.equal(settled.outcome,'accepted');assert.deepEqual(settled.accepted,['B']);
    assert.deepEqual(settled.attempt.executor,executor);assert.equal(settled.attempt.handle,null);
  });
  test('serial verification task keeps local done checks separate from receipt acceptance',()=>{
    const verificationGraph={version:1,steps:[{id:'V',deps:[],contract:{
      task:'Run the assigned verification checks',
      ready:['Verification target is available'],
      done:['Task-local verification evidence is recorded'],
    }}]};
    const {dir}=initialize(verificationGraph),claim=cli('claim',dir,{owner:'parent',steps:['V']}).claims[0];
    const executor={kind:'main-context',id:'verification-task-main'};
    const started=cli('start',dir,{owner:'parent',attempt:claim.attempt,context:context(),executor});
    const taskInstructions=started.packet.instructions.join(' ');
    assert.equal(started.packet.task,'Run the assigned verification checks');
    assert.deepEqual(started.packet.definition_of_done,['Task-local verification evidence is recorded']);
    assertExitCriteria(taskInstructions);
    assert.equal(started.packet.prior_attempts,undefined);
    assert.match(started.instruction,/perform dispatcher acceptance verification of the resulting receipt/i);
    assert.doesNotMatch(started.instruction,/do not execute next_argv, navigate the graph, verify(?:,| or)/i);
    fs.writeFileSync(started.packet.outputs.artifact,JSON.stringify({checked:'task-local verification'}));
    const receipt=cli('report',dir,{run_id:started.run_id,step:'V',attempt:claim.attempt,status:'SUCCEEDED',
      evidence:{path:started.packet.outputs.artifact,sha256:digest(fs.readFileSync(started.packet.outputs.artifact))}});
    assertTaskOnlyReport(receipt);
    assertParentVerification(cli('next',dir).actions.find(action=>action.attempt===claim.attempt),{mainContext:true});
  });
  test('accepted evidence drift refuses a ready frontier in a cold public invocation',()=>{
    const {dir}=initialize(),claim=cli('claim',dir,{owner:'parent',steps:['B']}).claims[0];
    const done=complete(dir,claim.attempt);fs.writeFileSync(done.envelope.evidence.path,'changed');
    assert.match(cli('next',dir,undefined,true).error,/SHA-256|evidence|hash/i);
  });
  success=true;
  console.log(`plan-dispatcher-cli.test.js: ${count} groups passed (copied package, no native agents)`);
} finally {
  if(success) fs.rmSync(root,{recursive:true,force:true});
  else console.error('Retained failed dispatcher fixtures: '+root);
}
