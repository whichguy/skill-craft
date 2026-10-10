#!/usr/bin/env python3
"""Versioned parent prompts for the external experiment, not the runtime skill."""
import argparse
from diagnostics import emit_diagnostics, evidence_reference, make_diagnostic
import hashlib
import json
import shlex
from pathlib import Path
import shutil

def make_packet_prompt(run, workers, mode):
    q = lambda path: shlex.quote(str(path))
    op = run/'operator'
    schedule = (f'Launch all {workers} native workers before collecting any final result.' if mode == 'parallel' else
                f'Launch and terminally collect one worker before launching the next; exactly {workers} workers total.')
    collected = ' '.join(f'--collected-worker {i}' for i in range(1,workers+1))
    return f'''Use Ask Agent from {run/'package/ask-agent/SKILL.md'} for this authorized worktree experiment. Read that card and {run/'manifest.json'} once. This is a fresh Grok-medium parent, with fresh general-purpose native background workers. The user explicitly authorizes helper-managed worktrees, patch delivery, native delegation, and local fixture integration.

Scope is this run directory {run}, including its caller, workspace-store, and operator evidence. Do not write temporary prompt copies elsewhere, modify global configuration, contact other services, commit, push, or publish. Native model calls are the requested service. Retain every worktree and all evidence for audit.

The caller is a linked worktree ahead of main with staged, unstaged, deleted and untracked inputs. Worker i owns only src/step_i.py and implements (i+1)*x+i*i. The trusted scripts verify package identity, original dirty layers, distinct child roots/indexes, probes, correct outputs, and guarded contribution integration. The user authorizes these tested scripts to replace mechanical route-appendix interpretation and repeated worker check commands. Detailed rationale and failure handling are at {op/'CONTRACT.md'}; read that file or implementation only to diagnose a reported failure. Script errors carry direct evidence references and stop this run.

Execute the following procedure:
1. Run python3 {q(op/'operations.py')} prepare-batch --run {q(run)} exactly once. Read its compact result.
2. Run python3 {q(op/'briefs.py')} --run {q(run)} exactly once. It validates current prepared state and retains dispatch-packet.json. Pass each native_arguments object directly to spawn_subagent in this parent; preserve its prompt, cwd, description and background values, with general-purpose type. The generated start/finish wrapper commands perform all mechanical worker checks; workers must implement their assigned source edit themselves. Do not paraphrase briefs or add manual serialization audits. The external auditor independently verifies the actual arguments. No script launches models.
3. Give a concise dispatch notice. {schedule} Use prepared cwd, background=true and no resume or inherited conversation. Keep every native handle. Never shell-launch a child model.
4. After dispatch begins, run python3 {q(op/'briefs.py')} --run {q(run)} --parent-oracle once. This creates independent expected results outside caller source. Do no child implementation in the parent.
5. Collect actual terminal results with get_command_or_subagent_output, using positive native waits when needed. Give return notices. Any failed/blocked worker stops integration; preserve evidence and report it. Do not silently retry or replace workers.
6. After all actual native terminal results, run python3 {q(op/'operations.py')} integrate-batch --run {q(run)} {collected} exactly once. These IDs assert collection; native history proves it separately. Read the compact summary. Full call output, failures and partial applies remain in integration-result.json. Stop on a failed gate; do not bypass, rollback or retry. Do not duplicate successful scripted checks.
7. Write {op/'parent-result.json'} with status and each worker's native handle, worktree, receipt, patch, package identity and integration result (you may reference exact retained setup/integration record fields). Return a concise result and evidence paths. Integration remains uncommitted. The external controller checks files after exit and audits native history; a process exit alone is not a pass. This tiny experiment measures coordination overhead, not production optimality.
'''

def make_compact_prompt(run, workers, mode):
    q = lambda path: shlex.quote(str(path))
    operations = run/'operator/operations.py'
    briefs = run/'operator/briefs.py'
    fixture = run/'operator/fixture.py'
    caller = run/'caller'
    collected = ' '.join(f'--collected-worker {i}' for i in range(1, workers + 1))
    schedule = (f'Launch all {workers} fresh native background workers before collecting any terminal result.'
                if mode == 'parallel' else
                f'Launch one fresh native worker and collect its terminal result before launching the next; exactly {workers} total.')
    order = ('Launch every worker before collecting any result.' if mode == 'parallel'
             else 'For this sequential control, fully collect each worker before launching the next.')
    return f'''Run the compact Ask Agent interface experiment from the selected frozen package at {run/'package/ask-agent/SKILL.md'}. Read that card. The scripts and independent auditor validate frozen run metadata from retained records; do not read the full manifest. This is a fresh Grok-medium parent and fresh general-purpose native background workers. The user authorizes local fixture worktree preparation, native delegation, patch integration, and retained audit evidence.

Keep all effects inside {run}, its caller {caller}, and child worktrees in {run/'workspace-store'}. Do not edit the source package, global configuration, credentials, or other user files; do not commit, push, publish, or contact external services. Retain all worktrees and evidence. This harness evaluates the compact API together with fixture instrumentation; it is not a pure production-speed comparison.

Every machine-readable CLI command below gets its own tool call and unmodified tool result: stdout must contain only that command's single JSON object. Never chain a command or append shell/Python debug or inspection output to a JSON-producing call. Trust the complete generated JSON; use retained records for diagnosis only after a command reports an error. Do not create temporary prompt copies or perform manual serialization audits.

Run the independent parent oracle: `python3 -B {q(briefs)} --run {q(run)} --parent-oracle`.
Prepare once with `python3 -B {q(operations)} prepare-batch --run {q(run)} --compact`. This invokes production ask_agent_task.py prepare for every assignment and retains the full result and exact binding JSON on disk. Read its JSON result; do not repeat successful preparation.
Build assignments once with `python3 -B {q(briefs)} --run {q(run)} --compact`. It validates each binding and retains one bounded native argument JSON file per worker. For each ID from 1 through {workers}, invoke `python3 -B {q(briefs)} --run {q(run)} --emit-worker ID` in its own tool call, read that complete single-worker JSON, and pass its exact `native_arguments` object directly to the native spawn tool. Do not emit all worker prompts in one Bash result, hand-edit a prompt, omit fields, or infer a binding.

Each compact assignment comes from the production task script's emitted prompt and exact binding. Its required start and finish wrapper each invoke the actual production `ask_agent_task.py worker-start` or `worker-finish` command exactly once with the unchanged `--binding` file. The wrapper retains those raw command results and fixture context/probe records. Do not ask a child to run an additional direct worker-start/worker-finish command; that would duplicate the production check. Each child must execute its assigned start wrapper before editing and finish wrapper after its edit, from the exact emitted `cwd`, then return its actual terminal result. Those wrapper checks are fixture instrumentation around the production command.

{schedule} {order} Use only host-native background worker spawn and terminal collection tools, with `background=true`, exact description/prompt/cwd, no resume, and fresh context. Never shell-launch models. Preserve exact task/write-set scope and all inherited dirty caller state. Shell commands must run from the assigned worktree; use absolute paths for file tools. Each child may edit only its own `src/step_ID.py`, defining `transform(x)=(ID+1)*x+ID*ID` for integers; run `python3 -B checks.py --worker ID` and report observed results. A worker must not change other files, commit, integrate, close, or delegate outside the selected card's rules.

After collecting all actual native terminal results, run `python3 -B {q(operations)} verify-return --run {q(run)} --worker ID` exactly once for every worker, using the retained compact binding. Only after all returned checks pass, run `python3 -B {q(operations)} integrate-batch --run {q(run)} {collected}` exactly once. The script applies only inspected immutable worker patches in ID order and runs the combined fixture oracle. Read its compact summary and retain full integration-result.json. Parent-supplied collection IDs are assertions; the independent native auditor verifies native lifecycle. Stop on any failed gate and retain partial work.

After integration run `python3 -B {q(fixture)} verify --run {q(run)}` and read the report. Write {run/'operator/parent-result.json'} as a small audit index with overall status and, for each worker, its ID, status, native handle, binding digest, and exact retained evidence record references. Keep full raw records in their existing files; do not repeat task, worktree, phase, or patch details. Return a concise result with evidence paths. Do not claim the harness proves production-scale speedup.'''

def make_prompt(run, workers, mode, treatment):
    run = Path(run).resolve()
    if treatment == 'packet':
        return make_packet_prompt(run, workers, mode)
    if treatment == 'compact':
        return make_compact_prompt(run, workers, mode)
    q = lambda path: shlex.quote(str(path))
    caller = run/'caller'
    card = run/'package/ask-agent/SKILL.md'
    fixture = run/'operator/fixture.py'
    hold_note = ('The configured hold in the start probe is deliberate overlap instrumentation. '
                 'Do not remove it or treat its elapsed time as useful computation.')
    tasks = '\n'.join(f'- Worker {i}: owns only src/step_{i}.py. Implement transform(x) = {i+1}*x + {i*i} for integers, then run python3 checks.py --worker {i}.' for i in range(1,workers+1))
    schedule = (f'Launch all {workers} fresh native background workers before collecting any required final result.' if mode == 'parallel' else
                f'Sequential control: launch one native worker, collect its terminal result, then launch the next; exactly {workers} total. Preserve isolation and all other requirements.')
    integration = f"""After all required native results, re-inspect every successful returned workspace with patch mode and verify each patch changes exactly its one owned source file. Recheck the source target and preserve its original index and inherited files. Integrate patches in worker-ID order using git -C TARGET -c core.autocrlf=false apply --check --binary --whitespace=nowarn PATCH, then the matching apply command without --check. Stop on a conflict; do not stash/reset/force or select one side silently. Integrate only baseline-relative worker contributions, not whole branch snapshots. Run python3 checks.py --all in caller and python3 {q(fixture)} verify --run {q(run)}. A zero process exit does not prove success: read verification.json."""
    extra = ''
    setup = f"""Prepare all of them while source writers are quiescent before any integration. Use packaged identity, capabilities, prepare --source {q(caller)} --store {q(run/'workspace-store')} --writers-quiescent, and prepared inspection. Retain the selected package identity and receipt per child. Do not hand-create child clones or silently choose the current-workspace route."""
    if treatment == 'batched':
        extra = """Experimental batching treatment: read applicable route references once. Batch independent read-only helper checks. Prepare workspaces in one sequential shell loop, retaining exact per-worker results. Inline compact complete assignments in native spawn arguments. After terminal collection, batch returned inspections and serial patch application, stopping on any failed check. Preserve every identity, context, inspection, oracle and handoff gate."""
    elif treatment == 'scripted':
        collected=' '.join(f'--collected-worker {i}' for i in range(1,workers+1))
        setup = f"""The user authorizes deterministic mechanical setup. Run python3 {q(run/'operator/operations.py')} prepare-batch --run {q(run)} exactly once. The script verifies package identities/capabilities, sequentially prepares all children while the source is quiescent, verifies no source drift, and performs every prepared inspection. Read its compact launch bindings and retain setup-result.json and helper logs. Dispatch those verified worktrees; do not create substitutes or repeat successful setup. Inspect implementation only to diagnose a failure."""
        integration = f"""After collecting all required actual terminal native outputs, run python3 {q(run/'operator/operations.py')} integrate-batch --run {q(run)} {collected} exactly once. These IDs assert collection; the independent native auditor verifies it separately. The script verifies selected package identities, every returned contribution and oracle, exact ownership, target/index stability, then applies immutable patches serially and runs the combined fixture oracle. Use its compact printed summary; the full integration-result.json remains available for diagnosis. On failure preserve evidence and partial applies and stop; do not bypass or retry a failed gate. Do not repeat successful mechanical checks manually. INTEGRATED means filesystem gates passed; the external controller still performs post-exit and native audits."""
        extra = """Experimental scripted workflow: read route references once. Use the tested setup/integration interfaces and frozen probes. Keep native assignments compact while including the objective, owned path, Current learnings, verified package identity, pinned revisions, worktree/receipt, shell cwd rule, exact check-context and probe commands, patch inspection and inline return. Pass actual bindings inline, not a prompt transport file. Declare only .experiment-local/owner.txt as the probe artifact. Keep all evidence and correctness gates."""
    parent_work = f"After confirmed launches, do useful independent parent work: calculate the expected composition over [-7,-1,0,1,9,100] with the formulas above and save the expected values in {run/'operator/parent-expected.json'}, outside the caller."
    return f'''Run a bounded side experiment using ask-agent, selected explicitly from {card}. Read that card. Read its applicable managed-worktree references. This is an explicit request for workspace_route: helper-managed and delivery_mode: patch. Use this frozen selected package, not another installed copy. The experiment is authorized to prepare isolated worktrees, invoke native child agents, edit the assigned fixture files, and integrate verified contributions into {caller}. No approval is needed for those local effects.

Scope: fixture repo {caller}, helper store {run/'workspace-store'}, operator evidence {run/'operator'}, and child worktrees created in that store. Do not edit source repositories, global settings, plugins, credentials or other user files; do not push, publish, or contact external services. The Grok host provides the requested model service. This run is a fresh session, not a resume.

Read {run/'manifest.json'} for the frozen starting state. This caller is a linked Git worktree ahead of main, with staged, unstaged, and untracked inputs. All {workers} child snapshots must derive from exactly this initial dirty caller. {setup}

Known work:
{tasks}

Each worker receives a fresh self-contained native assignment, Current learnings, package identity, actual worktree/receipt, patch delivery clause, pinned target {caller} and HEAD, and this exact probe/check contract:
1. Before any edits, run the selected helper check-context --receipt RECEIPT from the actual assigned child worktree. Use native startup cwd binding where exposed and explicit cwd on all shell operations. Use absolute paths for file tools.
2. From that worktree run: python3 {q(fixture)} probe --run {q(run)} --worker ID --phase start. {hold_note}
3. Implement only its owned src/step_ID.py. Other workers exist but are in separate worktrees: do not inspect, edit, copy, or revert their work. Preserve inherited dirty inputs, index and HEAD. No commits or broad staging. Run python3 checks.py --worker ID.
4. From the same worktree run: python3 {q(fixture)} probe --run {q(run)} --worker ID --phase finish.
5. Inspect returned patch delivery with the selected helper. Declare only .experiment-local/owner.txt as the probe artifact; no other ignored worker artifacts are allowed. Return an inline self-contained native handoff with actual package identity, worktree/branch, receipt, checks, patch path, target, and integration-pending state. Do not write a handoff file. After the finish probe, make no further worker filesystem writes; the trusted helper may retain its inspection records in the external store. Leave worktree and evidence intact. Do not write outside this worker except that the trusted probe writes its own operator receipt.

{schedule}
Use native general-purpose workers with background=true and their prepared cwd, no resume or inherited parent conversation. Use the host's native launch and get_command_or_subagent_output tools; never shell-launch child models. Carry original user authorization in the assignment. Give a concise batch dispatch notice and return notices. Acknowledge that the same relative owner marker with different values is an intentional collision probe for filesystem separation, not a security boundary.

{parent_work} Do not implement child code in the parent. Collect actual terminal native outputs before returning; if a worker is failed/blocked, preserve its work and distinguish it from successful workers. Do not silently replace or retry a failed child. Use positive native wait durations when necessary, not shell sleep polling.

{integration}

Retain all worker worktrees, branches, receipts, patches, and ignored artifacts for operator audit; do not close or remove them during this experiment. Retention for audit is the requested final state. Write {run/'operator/parent-result.json'} with overall status, each worker ID, native handle, task, actual root, branch, receipt, immutable patch, package identity, check result, integration state, and blocker if any. Return a concise final result with the integrated uncommitted target changes and evidence paths. This is a microbenchmark; do not claim optimality or production-scale speedup.
{extra}'''

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--workers',type=int,choices=[3,5],required=True)
    p.add_argument('--mode',choices=['parallel','sequential'],default='parallel');p.add_argument('--treatment',choices=['baseline','batched','scripted','packet','compact'],default='baseline')
    a=p.parse_args(argv);path=Path(a.run)/'operator/parent-prompt.txt'
    if path.with_name('launch.json').exists():
        p.error('An attempt was already launched; its prompt and apparatus are immutable')
    manifest=json.loads((Path(a.run)/'manifest.json').read_text())
    if a.workers!=manifest['workers'] or a.mode!=manifest['mode']:
        p.error('Prompt worker count/mode must match the frozen manifest')
    for name in ['fixture.py','operations.py','native_trace.py','suite.py','controller.py','prompts.py','diagnostics.py','CONTRACT.md','briefs.py','worker_phase.py']:
        shutil.copy2(Path(__file__).with_name(name), path.with_name(name))
    path.write_text(make_prompt(a.run,a.workers,a.mode,a.treatment))
    scope = ('compact API plus fixture instrumentation; production prepare/start/finish/verify-return and guarded integration with one native assignment emitted at a time; not a pure production speed comparison'
             if a.treatment == 'compact' else
             'scripted bundles preparation, integration and compact guidance; packet also generates exact compact worker briefs, scripts worker phases and substitutes the script contract for route appendix reading; not a setup-only causal comparison')
    version = 1 if a.treatment == 'compact' else 4
    path.with_name('treatment.json').write_text(json.dumps({'treatment':a.treatment,'version':version,'workers':a.workers,'mode':a.mode,'prompts_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':scope},indent=2)+'\n')
    print(path)
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError,ValueError,KeyError) as exc:
        emit_diagnostics([make_diagnostic(code='PROMPT_FREEZE_FAILED',severity='error',phase='prompt-freeze',
            expected='An unlaunched fixture with matching worker count and mode, and readable apparatus files',
            observed={'exception':type(exc).__name__,'detail':str(exc)},
            rationale='A prompt and its frozen apparatus must describe the same fixture before dispatch.',
            rationale_ref='CONTRACT.md#phase-sequence',evidence=[evidence_reference(Path(__file__))],
            recovery='Inspect the exact exception and fixture manifest; do not launch partial apparatus.',
            retry_safety='Repair preparation only before launch; a launched run is immutable.')])
        raise SystemExit(2)
