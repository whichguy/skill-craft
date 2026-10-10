#!/usr/bin/env python3
"""Test-only managed-worktree setup and patch integration; no native lifecycle proof."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import diagnostics
import fixture

REQUIRED_CAPABILITIES = {'helper-managed-worktree','prepared-inspection','returned-commit-delivery',
                         'fingerprint-bound-close','ignored-output-report'}
OWNER_MARKER = '.experiment-local/owner.txt'


def _write_immutable_patch(path, payload):
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444)
    try:
        view=memoryview(payload)
        while view:
            written=os.write(descriptor,view)
            view=view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.chmod(path,0o444)


def _compact_return_error(code, message, expected, observed):
    error=fixture.FixtureError(f'[{code}] {message}')
    error.diagnostic_code=code
    error.diagnostic_phase='compact-verify-return'
    error.diagnostic_expected=expected
    error.diagnostic_observed=observed
    raise error


def _compact_return_binding(run, manifest, setup, worker, worker_id):
    package_root=Path(manifest['paths']['package']).resolve(strict=True)
    expected_binding=run/'operator/compact-bindings'/f'worker-{worker_id}.json'
    supplied=Path(str(worker.get('compact_binding_path',''))).expanduser()
    binding_path=supplied.resolve(strict=True)
    if binding_path!=expected_binding.resolve() or supplied.is_symlink() or not binding_path.is_file():
        _compact_return_error('COMPACT_RETURN_BINDING_INVALID','binding path is not the retained worker binding',
                              {'binding_path':str(expected_binding.resolve())},
                              {'binding_path':str(binding_path),'symlink':supplied.is_symlink()})
    try:
        binding=json.loads(binding_path.read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:
        _compact_return_error('COMPACT_RETURN_BINDING_INVALID','cannot read compact binding JSON',
                              {'readable_json':str(binding_path)},
                              {'error':f'{type(exc).__name__}: {exc}'})
    if not isinstance(binding,dict) or not all(isinstance(binding.get(key),dict) for key in ('package','workspace','task')):
        _compact_return_error('COMPACT_RETURN_BINDING_INVALID','compact binding has incomplete package, workspace, or task objects',
                              {'package':True,'workspace':True,'task':True},
                              {'binding_type':type(binding).__name__})
    task=next((item for item in manifest.get('task_assignments',[]) if item.get('worker_id')==worker_id),None)
    identity=setup.get('package_identity',{})
    bound_package=binding.get('package',{}) if isinstance(binding,dict) else {}
    bound_workspace=binding.get('workspace',{}) if isinstance(binding,dict) else {}
    bound_task=binding.get('task',{}) if isinstance(binding,dict) else {}
    expected_script=package_root/'scripts/ask_agent_task.py'
    try:
        task_script=Path(str(bound_package.get('task_script',''))).resolve(strict=True)
        resolved_expected_script=expected_script.resolve(strict=True)
        script_hash=fixture.sha256_file(expected_script)
        package_hash=fixture.package_tree_sha256(package_root)
    except (OSError,ValueError) as exc:
        _compact_return_error('COMPACT_RETURN_BINDING_INVALID','frozen package task script is unavailable',
                              {'task_script':str(expected_script)}, {'error':f'{type(exc).__name__}: {exc}'})
    binding_without_digest={key:value for key,value in binding.items() if key!='binding_sha256'}
    digest=hashlib.sha256(json.dumps(binding_without_digest,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('utf-8')).hexdigest()
    expected_result=(f"src/step_{worker_id}.py defines transform(x)=({int(worker_id)}+1)*x+"
                     f"{int(worker_id)}*{int(worker_id)} for every integer.")
    checks={
        'binding_schema':binding.get('schema')=='ask-agent.task.binding.v1' and binding.get('status')=='READY_TO_LAUNCH',
        'binding_digest':binding.get('binding_sha256')==digest==worker.get('compact_binding_sha256'),
        'package_tree_matches_manifest':package_hash==manifest.get('source',{}).get('package_tree_sha256'),
        'package_tree_matches_setup':package_hash==setup.get('frozen_package_tree_sha256_before_preparation')==setup.get('frozen_package_tree_sha256_after_preparation'),
        'selected_card_matches':bound_package.get('skill_card')==identity.get('skill_card') and bound_package.get('resolved_skill_card')==identity.get('resolved_skill_card'),
        'card_hash_matches':bound_package.get('skill_card_sha256')==identity.get('skill_card_sha256'),
        'helper_matches':bound_package.get('resolved_helper')==identity.get('resolved_helper') and bound_package.get('helper_sha256')==identity.get('helper_sha256'),
        'task_script_is_frozen_path':task_script==resolved_expected_script and package_root in task_script.parents,
        'task_script_hash_matches':bound_package.get('task_script_sha256')==script_hash,
        'worker_task_matches':task is not None and bound_task.get('objective')==task.get('assignment')
        and bound_task.get('expected_result')==expected_result and bound_task.get('mode')=='edit'
        and bound_task.get('write_set')==[worker.get('path')],
        'workspace_matches_setup':bound_workspace.get('route')=='worktree'
        and bound_workspace.get('source')==manifest['paths']['caller']
        and bound_workspace.get('root')==worker.get('worktree')
        and bound_workspace.get('launch_cwd')==worker.get('worktree')
        and bound_workspace.get('receipt')==worker.get('receipt')
        and bound_workspace.get('baseline')==worker.get('prepared_inspection',{}).get('baseline')
        and bound_workspace.get('branch')==worker.get('branch')
        and bound_workspace.get('prepared_fingerprint')==worker.get('prepared_inspection',{}).get('fingerprint'),
    }
    if not all(checks.values()):
        _compact_return_error('COMPACT_RETURN_BINDING_INVALID',
                              f'worker {worker_id} binding differs from the frozen package, task, or workspace',
                              {key:True for key in checks},checks)
    return binding_path,binding,task_script


def verify_compact_return(run, worker_id):
    """Run and retain the production compact return check for one worker."""
    run=Path(run).resolve()
    manifest=fixture.load_manifest(run)
    setup=json.loads((run/'operator/setup-result.json').read_text(encoding='utf-8'))
    worker_id=str(worker_id)
    workers={worker.get('worker_id'):worker for worker in setup.get('workers',[]) if isinstance(worker,dict)}
    worker=workers.get(worker_id)
    if setup.get('treatment')!='compact' or worker is None:
        error=fixture.FixtureError(f'[COMPACT_RETURN_BINDING_INVALID] no compact setup exists for worker {worker_id}')
        error.diagnostic_code='COMPACT_RETURN_BINDING_INVALID'
        error.diagnostic_phase='compact-verify-return'
        raise error
    binding_path,binding,task_script=_compact_return_binding(run,manifest,setup,worker,worker_id)
    record_dir=run/'operator/compact-returns'
    record_path=record_dir/f'worker-{worker_id}.json'
    record_dir.mkdir(exist_ok=True)
    if record_path.exists():
        _compact_return_error('COMPACT_RETURN_ALREADY_ATTEMPTED',
                              f'retained compact return evidence exists: {record_path}',
                              {'one_attempt_per_worker':True},{'evidence_path':str(record_path)})
    argv=[sys.executable,'-B',str(task_script),'verify-return','--binding',str(binding_path)]
    started=time.time()
    record={'schema':'ask-agent.compact-command/v1','phase':'verify-return','worker_id':worker_id,
            'binding_path':str(binding_path.resolve()),'binding_sha256':binding['binding_sha256'],
            'argv':argv,'cwd':str(Path(manifest['paths']['caller']).resolve()),'started_epoch':started,
            'exit_code':None,'stdout':'','stderr':'','status':'RUNNING'}
    try:
        proc=subprocess.run(argv,cwd=record['cwd'],capture_output=True,text=True,check=False)
        record.update({'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'status':'COMPLETED'})
        try:
            record['result']=json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            record['json_parse_error']=f'{type(exc).__name__}: {exc}'
    except OSError as exc:
        record.update({'status':'FAILED_TO_START','error':f'{type(exc).__name__}: {exc}'})
    record['elapsed_s']=time.time()-started
    result=record.get('result')
    workspace_evidence=result.get('workspace_evidence',{}) if isinstance(result,dict) else {}
    inspection=workspace_evidence.get('inspection',{}) if isinstance(workspace_evidence,dict) else {}
    passed=(record.get('exit_code')==0 and isinstance(result,dict)
            and result.get('status')=='READY_FOR_PARENT_ACCEPTANCE'
            and result.get('command')=='verify-return'
            and result.get('binding_sha256')==binding['binding_sha256']
            and isinstance(inspection,dict) and inspection.get('status')=='returned'
            and inspection.get('receipt')==worker['receipt']
            and inspection.get('worktree')==worker['worktree']
            and inspection.get('contribution_paths')==[worker['path']])
    record['status']='PASSED' if passed else 'FAILED'
    record['evidence_path']=str(record_path.resolve())
    fixture.write_exclusive_json(record_path,record)
    if not passed:
        error=fixture.FixtureError(f'[COMPACT_RETURN_CHECK_FAILED] worker {worker_id} compact verify-return did not confirm its bound contribution; evidence: {record_path}')
        error.diagnostic_code='COMPACT_RETURN_CHECK_FAILED'
        error.diagnostic_phase='compact-verify-return'
        error.diagnostic_expected={'status':'READY_FOR_PARENT_ACCEPTANCE','binding_sha256':binding['binding_sha256'],
                                   'receipt':worker['receipt'],'worktree':worker['worktree'],'contribution_paths':[worker['path']]}
        error.diagnostic_observed={'exit_code':record.get('exit_code'),'result':result,'error':record.get('error'),
                                   'evidence_path':str(record_path)}
        raise error
    return {'status':'PASSED','worker_id':worker_id,'binding_sha256':binding['binding_sha256'],
            'evidence_path':str(record_path.resolve()),'contribution_paths':inspection['contribution_paths']}


def _require_compact_returns(run, setup, expected_ids):
    if setup.get('treatment')!='compact':
        return
    records=[]
    issues=[]
    manifest=fixture.load_manifest(run)
    caller=str(Path(manifest['paths']['caller']).resolve())
    for worker_id in expected_ids:
        worker=next((item for item in setup.get('workers',[]) if item.get('worker_id')==worker_id),None)
        path=run/'operator/compact-returns'/f'worker-{worker_id}.json'
        binding_path=Path(worker.get('compact_binding_path','')) if worker else Path()
        if worker is None:
            issues.append({'worker_id':worker_id,'error':'compact setup worker is missing','path':str(path)})
            continue
        try:
            _,binding,task_script=_compact_return_binding(run,manifest,setup,worker,worker_id)
            record=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError,TypeError,fixture.FixtureError) as exc:
            issues.append({'worker_id':worker_id,'error':f'{type(exc).__name__}: {exc}','path':str(path)})
            continue
        result=record.get('result')
        workspace_evidence=result.get('workspace_evidence',{}) if isinstance(result,dict) else {}
        inspection=workspace_evidence.get('inspection',{}) if isinstance(workspace_evidence,dict) else {}
        try:
            stdout_result=json.loads(record.get('stdout',''))
        except (TypeError,ValueError):
            stdout_result=None
        valid=(isinstance(result,dict) and isinstance(inspection,dict)
               and record.get('status')=='PASSED' and record.get('exit_code')==0
               and record.get('schema')=='ask-agent.compact-command/v1' and record.get('phase')=='verify-return'
               and record.get('worker_id')==worker_id
               and record.get('evidence_path')==str(path.resolve())
               and record.get('command_status') in (None,'COMPLETED')
               and record.get('binding_path')==str(binding_path.resolve())
               and record.get('argv')==[sys.executable,'-B',str(task_script),'verify-return','--binding',str(binding_path.resolve())]
               and record.get('cwd')==caller and stdout_result==result
               and record.get('binding_sha256')==binding.get('binding_sha256')==worker.get('compact_binding_sha256')
               and result.get('status')=='READY_FOR_PARENT_ACCEPTANCE'
               and result.get('command')=='verify-return'
               and result.get('binding_sha256')==binding.get('binding_sha256')
               and inspection.get('status')=='returned'
               and inspection.get('receipt')==worker.get('receipt')
               and inspection.get('worktree')==worker.get('worktree')
               and inspection.get('contribution_paths')==[worker.get('path')])
        records.append({'worker_id':worker_id,'valid':valid,'evidence_path':str(path.resolve())})
        if not valid:
            issues.append({'worker_id':worker_id,'record_status':record.get('status'),
                           'exit_code':record.get('exit_code'),'binding_sha256':record.get('binding_sha256'),
                           'result_status':result.get('status') if isinstance(result,dict) else None,
                           'evidence_path':str(path)})
    if issues:
        error=fixture.FixtureError('[COMPACT_VERIFY_RETURN_REQUIRED] every worker must have a successful bound compact verify-return before integration')
        error.diagnostic_code='COMPACT_VERIFY_RETURN_REQUIRED'
        error.diagnostic_phase='integration-preflight'
        error.diagnostic_expected={'worker_ids':expected_ids,'all_compact_returns_passed':True}
        error.diagnostic_observed={'records':records,'issues':issues}
        raise error

def prepare_batch(run, *, compact=False):
    run = Path(run).resolve()
    manifest = fixture.load_manifest(run)
    source = Path(manifest['paths']['caller'])
    package = Path(manifest['paths']['package'])
    card = package/'SKILL.md'
    helper = package/'scripts/ask_agent_workspace.py'
    output = run/'operator/setup-result.json'
    log_dir = run/'operator/setup-calls'
    if output.exists() or log_dir.exists():
        raise fixture.FixtureError(
            f'[SETUP_ALREADY_ATTEMPTED] expected one setup attempt; observed existing evidence {output} or {log_dir}; '
            'retain receipts and inspect before using a fresh run'
        )
    # Exclusive mkdir reserves this setup attempt; an existing directory fails.
    log_dir.mkdir()
    start=time.time()
    calls=[]
    compact_prepare_dir=run/'operator/compact-prepare'
    compact_binding_dir=run/'operator/compact-bindings'
    if compact:
        compact_prepare_dir.mkdir()
        compact_binding_dir.mkdir()
    result={'status':'PREPARING','phase':'preflight','source':str(source),'source_head':manifest['caller_snapshot']['head'],
            'treatment':'compact' if compact else 'scripted',
            'started_epoch':start,'workers':[],'calls':calls,
            'operations_script_sha256':fixture.sha256_file(Path(__file__).resolve()),
            'frozen_package_tree_sha256_before_preparation':None,
            'frozen_package_tree_sha256_after_preparation':None,
            'retry_semantics':'One setup attempt per run; failed attempts retain receipts and logs and must not be rerun.'}
    def save():
        output.write_text(json.dumps(result,indent=2)+'\n')
    def command_call(label,argv,cwd=source):
        result['phase']=label
        began=time.time()
        proc=subprocess.run(argv,cwd=cwd,capture_output=True,text=True)
        record={'label':label,'argv':argv,'started_epoch':began,'elapsed_s':time.time()-began,
                'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr}
        path=log_dir/f'{len(calls)+1:02d}-{label}.json'
        path.write_text(json.dumps(record,indent=2)+'\n')
        calls.append({'label':label,'evidence':str(path),'elapsed_s':record['elapsed_s'],'exit_code':proc.returncode});save()
        if proc.returncode:
            raise fixture.FixtureError(f'Selected helper failed at {label}; evidence: {path}')
        return json.loads(proc.stdout)
    def helper_call(label,*args):
        return command_call(label,[sys.executable,'-B',str(helper),*args])
    save()
    reference_identity=None
    phase='preflight'
    try:
        phase='frozen_package_before_setup';result['phase']=phase
        package_digest_before=fixture.package_tree_sha256(package)
        result['frozen_package_tree_sha256_before_preparation']=package_digest_before
        if package_digest_before!=manifest['source']['package_tree_sha256']:
            raise fixture.FixtureError('Frozen package changed before preparation')
        phase='caller_snapshot_before_setup';result['phase']=phase
        before=fixture.capture_repo_state(source)
        baseline=manifest['caller_snapshot']
        state_fields=('root','branch','head','index_entries','cached_diff_sha256','unstaged_dirty_diffs','working_tree','status')
        if any(before[k]!=baseline[k] for k in state_fields):
            raise fixture.FixtureError('Caller drifted from the frozen input')
        for worker in manifest['task_assignments']:
            identifier=worker['worker_id']
            phase=f'identity-{identifier}';result['phase']=phase
            identity=helper_call(f'identity-{identifier}','identity','--skill-card',str(card))
            if identity.get('status')!='verified':
                raise fixture.FixtureError('Package identity was not verified')
            if reference_identity is None:
                reference_identity=identity
                result['package_identity']=identity
            elif identity!=reference_identity:
                raise fixture.FixtureError('Package identity changed across workers')
            phase=f'capabilities-{identifier}';result['phase']=phase
            capabilities=helper_call(f'capabilities-{identifier}','capabilities','--skill-card',str(card))
            if capabilities.get('schema')!='shiploop-chain-ask-agent-managed-worktree/v1' or not REQUIRED_CAPABILITIES.issubset(set(capabilities.get('capabilities',[]))):
                raise fixture.FixtureError('Selected package lacks required managed-worktree capabilities')
            phase=f'prepare-{identifier}';result['phase']=phase
            compact_result=None
            if compact:
                task_script=package/'scripts/ask_agent_task.py'
                task=worker
                request={
                    'objective':task['assignment'],
                    'expected_result':f"src/step_{identifier}.py defines transform(x)=({int(identifier)}+1)*x+{int(identifier)}*{int(identifier)} for every integer.",
                    'source':str(source),'workspace':'worktree','mode':'edit','write_set':[task['path']],
                    'current_learnings':'This fixture preserves the caller snapshot and gives this worker one owned source module.',
                    'authorization':'The parent authorizes preparation of this isolated fixture worktree and the assigned source edit.',
                    'writers_quiescent':True,'exclusive_writer':False,'store':str(run/'workspace-store'),
                }
                request_path=compact_prepare_dir/f'worker-{identifier}.request.json'
                fixture.write_exclusive_json(request_path,request)
                compact_result=command_call(
                    f'compact-prepare-{identifier}',
                    [sys.executable,'-B',str(task_script),'prepare','--skill-card',str(card),
                     '--request',str(request_path)],
                )
                if compact_result.get('status')!='READY_TO_LAUNCH' or not isinstance(compact_result.get('binding'),dict):
                    raise fixture.FixtureError(f'Compact prepare did not return a ready binding for worker {identifier}')
                binding=compact_result['binding']
                binding_path=compact_binding_dir/f'worker-{identifier}.json'
                fixture.write_exclusive_json(binding_path,binding)
                fixture.write_exclusive_json(compact_prepare_dir/f'worker-{identifier}.result.json',compact_result)
                bound=binding.get('workspace',{})
                if manifest.get('seed_compact_ignore_controls'):
                    omitted=bound.get('ignored_dependencies_omitted')
                    if (not isinstance(omitted,list) or 'unrelated-ignored-input.txt' not in omitted
                            or '.claspignore' in omitted):
                        raise fixture.FixtureError(
                            f'Compact prepare did not report the expected ignored inputs for worker {identifier}'
                        )
                if (binding.get('schema')!='ask-agent.task.binding.v1'
                        or binding.get('status')!='READY_TO_LAUNCH'
                        or binding.get('task',{}).get('write_set')!=[task['path']]
                        or binding.get('package',{}).get('resolved_skill_card')!=str(card.resolve())
                        or bound.get('route')!='worktree'
                        or bound.get('source')!=str(source)
                        or bound.get('launch_cwd')!=bound.get('root')
                        or not all(isinstance(bound.get(key),str) and Path(bound[key]).is_absolute()
                                   for key in ('root','receipt','baseline'))):
                    raise fixture.FixtureError(f'Compact binding does not match worker {identifier} assignment and source')
                preparation={'status':'prepared','worktree':bound['root'],'branch':bound['branch'],
                             'receipt':bound['receipt'],'baseline':bound['baseline']}
                prepared_inspection={
                    'status':'prepared','phase':'prepared','receipt':bound['receipt'],'worktree':bound['root'],
                    'branch':bound['branch'],'baseline':bound['baseline'],
                    'fingerprint':bound['prepared_fingerprint'],'changed_paths':[],'contribution_paths':[],
                }
            else:
                preparation=helper_call(f'prepare-{identifier}','prepare','--source',str(source),'--store',str(run/'workspace-store'),
                                         '--label',f'worker-{identifier}','--writers-quiescent')
            if preparation.get('status')!='prepared':
                raise fixture.FixtureError('Helper did not return a prepared workspace')
            worker_result={'worker_id':identifier,'path':worker['path'],
                           'worktree':preparation['worktree'],'branch':preparation['branch'],
                           'receipt':preparation['receipt'],'package_identity':identity}
            if compact:
                worker_result.update({
                    'prepared_inspection':prepared_inspection,
                    'compact_binding_path':str(binding_path.resolve()),
                    'compact_binding_sha256':binding['binding_sha256'],
                    'compact_prepare_result_path':str((compact_prepare_dir/f'worker-{identifier}.result.json').resolve()),
                })
            result['workers'].append(worker_result)
            save()
        phase='prepared_roots_check';result['phase']=phase
        roots={w['worktree'] for w in result['workers']}
        if len(roots)!=manifest['workers'] or str(source) in roots:
            raise fixture.FixtureError('Preparation did not produce distinct child worktrees')
        for worker in result['workers']:
            if compact:
                continue
            phase=f"inspect-prepared-{worker['worker_id']}";result['phase']=phase
            inspected=helper_call(f"inspect-{worker['worker_id']}",'inspect','--receipt',worker['receipt'],'--phase','prepared')
            worker['prepared_inspection']=inspected
            save()
            expected_binding={key:worker[key] for key in ('receipt','worktree','branch')}
            if inspected.get('status')!='prepared' or inspected.get('phase')!='prepared':
                raise fixture.FixtureError('Helper did not confirm a prepared inspection')
            if any(inspected.get(key)!=value for key,value in expected_binding.items()):
                raise fixture.FixtureError('Prepared inspection binding differs from its receipt')
            if inspected.get('changed_paths')!=[] or inspected.get('contribution_paths')!=[]:
                raise fixture.FixtureError('Prepared inspection reports unexpected changes')
        phase='caller_snapshot_after_setup';result['phase']=phase
        after=fixture.capture_repo_state(source)
        if any(after[k]!=before[k] for k in state_fields):
            raise fixture.FixtureError('Caller changed during batch preparation; do not dispatch')
        phase='frozen_package_after_setup';result['phase']=phase
        package_digest_after=fixture.package_tree_sha256(package)
        result['frozen_package_tree_sha256_after_preparation']=package_digest_after
        if package_digest_after!=manifest['source']['package_tree_sha256']:
            raise fixture.FixtureError('Frozen package changed during preparation')
        result['phase']='prepared';result['status']='PREPARED'
    except Exception as exc:
        result['status']='FAILED';result['phase']=phase;result['error']=f'{type(exc).__name__}: {exc}'
        last_call=calls[-1] if calls else None
        result['failure']={
            'code':'SETUP_FAILED','phase':phase,'message':str(exc),
            'expected':{'status':'PREPARED','worker_count':manifest['workers'],
                        'frozen_source_unchanged':True},
            'observed':{'error':f'{type(exc).__name__}: {exc}','last_helper_call':last_call},
            'evidence_path':last_call['evidence'] if last_call else str(output),
            'applied_worker_ids':[],
            'retry_semantics':result['retry_semantics'],
        }
        result['error_code']='SETUP_FAILED'
        raise
    finally:
        if result['frozen_package_tree_sha256_after_preparation'] is None:
            try:
                result['frozen_package_tree_sha256_after_preparation']=fixture.package_tree_sha256(package)
            except Exception as digest_exc:
                result['frozen_package_tree_digest_error']=f'{type(digest_exc).__name__}: {digest_exc}'
        result['elapsed_s']=time.time()-start;save()
    return {k:v for k,v in result.items() if k!='calls'}


def integrate_batch(run, collected_worker_ids):
    """Apply validated worker patches after an explicit parent collection assertion.

    The supplied ids are assertions only; a separate native-trace auditor must
    establish the actual launch, wait, and collection lifecycle.
    """
    run=Path(run).resolve()
    manifest=fixture.load_manifest(run)
    expected_ids=[task['worker_id'] for task in manifest['task_assignments']]
    if not isinstance(collected_worker_ids,(list,tuple)):
        error=fixture.FixtureError(
            f'[PARENT_COLLECTION_ASSERTION_INVALID] expected a repeated worker-id list for {expected_ids}; '
            f'observed {collected_worker_ids!r}; no integration files were written'
        )
        error.diagnostic_code='PARENT_COLLECTION_ASSERTION_INVALID'
        error.diagnostic_phase='argument_validation'
        error.diagnostic_expected={'manifest_worker_ids_exactly_once':expected_ids}
        error.diagnostic_observed={'provided_value':repr(collected_worker_ids)}
        raise error
    asserted_ids=list(collected_worker_ids)
    if (any(not isinstance(worker_id,str) for worker_id in asserted_ids)
            or len(asserted_ids)!=len(expected_ids)
            or len(set(asserted_ids))!=len(asserted_ids)
            or set(asserted_ids)!=set(expected_ids)):
        error=fixture.FixtureError(
            f'[PARENT_COLLECTION_ASSERTION_INVALID] expected every manifest id exactly once: {expected_ids}; '
            f'observed {asserted_ids!r}; no integration files were written'
        )
        error.diagnostic_code='PARENT_COLLECTION_ASSERTION_INVALID'
        error.diagnostic_phase='argument_validation'
        error.diagnostic_expected={'manifest_worker_ids_exactly_once':expected_ids}
        error.diagnostic_observed={'collected_worker_ids':asserted_ids}
        raise error

    setup_for_preflight=json.loads((run/'operator/setup-result.json').read_text(encoding='utf-8'))
    _require_compact_returns(run,setup_for_preflight,expected_ids)

    output=run/'operator/integration-result.json'
    log_dir=run/'operator/integration-calls'
    patch_dir=run/'operator/integration-patches'
    if output.exists() or log_dir.exists():
        raise fixture.FixtureError(
            f'[INTEGRATION_ALREADY_ATTEMPTED] expected one integration attempt; observed existing evidence '
            f'{output} or {log_dir}; inspect it before creating a fresh run'
        )
    # Exclusive mkdir reserves this integration attempt; a second invocation cannot overwrite evidence.
    log_dir.mkdir()
    start=time.time()
    result={
        'schema_version':1,
        'run_id':manifest['run_id'],
        'status':'PREPARING',
        'phase':'preflight',
        'started_epoch':start,
        'elapsed_s':None,
        'source':manifest['paths']['caller'],
        'source_head':manifest['caller_snapshot']['head'],
        'parent_asserted_collected_worker_ids':asserted_ids,
        'integration_worker_ids':[task['worker_id'] for task in sorted(
            manifest['task_assignments'],key=lambda task:int(task['worker_id']))],
        'native_lifecycle_note':(
            'Parent-supplied worker ids are assertions, not proof of native event ordering or collection; '
            'the separate native-trace auditor owns that evidence.'
        ),
        'actions':[],
        'integrity_checks':{},
        'patches':[],
        'applied_worker_ids':[],
        'fixture_verification':None,
        'retry_semantics':(
            'This run permits one integration attempt. Failures retain receipts, immutable patch copies, '
            'logs, and any applied modules; do not rerun or auto-rollback. Reconcile evidence before using a fresh run.'
        ),
    }
    result_path=output
    failure_context={}

    def save():
        result['elapsed_s']=time.time()-start
        result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')

    def save_action(record):
        number=len(result['actions'])+1
        evidence=log_dir/f'{number:03d}-{record["label"]}.json'
        record['evidence']=str(evidence)
        evidence.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        result['actions'].append(record)
        save()

    def run_action(label,argv,*,cwd=None):
        result['phase']=label
        began=time.time()
        try:
            completed=subprocess.run(
                argv,cwd=str(cwd) if cwd is not None else None,
                capture_output=True,text=True,
            )
        except Exception as exc:
            record={
                'label':label,'argv':argv,'started_epoch':began,'elapsed_s':time.time()-began,
                'exit_code':None,'stdout':'','stderr':'','error':f'{type(exc).__name__}: {exc}',
            }
            save_action(record)
            raise fixture.FixtureError(f'{label} could not complete: {exc}') from exc
        record={
            'label':label,'argv':argv,'started_epoch':began,'elapsed_s':time.time()-began,
            'exit_code':completed.returncode,'stdout':completed.stdout,'stderr':completed.stderr,
        }
        save_action(record)
        if completed.returncode:
            failure_context.update({
                'code':(
                    'PATCH_CONFLICT' if label.startswith('patch-check')
                    else 'PATCH_APPLY_FAILED' if label.startswith('patch-apply')
                    else 'HELPER_ACTION_FAILED' if label.startswith(('identity-','inspect-returned-'))
                    else 'INTEGRATION_ACTION_FAILED'
                ),
                'phase':label,
                'expected':'exit_code == 0',
                'observed':{'exit_code':completed.returncode,'stdout':completed.stdout,'stderr':completed.stderr},
                'evidence_path':result['actions'][-1]['evidence'],
            })
            raise fixture.FixtureError(f'{label} failed with exit {completed.returncode}: {completed.stderr.strip()}')
        return completed.stdout

    def require_check(name,passed,details,message,*,code='INTEGRITY_CHECK_FAILED',expected=None):
        began=time.time()
        result['phase']=name
        result['integrity_checks'][name]={'passed':bool(passed),'details':details}
        record={
            'label':f'check-{name}','argv':['integrity-check',name],
            'started_epoch':began,'elapsed_s':time.time()-began,
            'exit_code':0 if passed else 1,
            'stdout':json.dumps(details,sort_keys=True),'stderr':'' if passed else message,
        }
        save_action(record)
        if not passed:
            failure_context.update({
                'code':code,'phase':name,
                'expected':expected if expected is not None else message,
                'observed':details,
                'evidence_path':result['actions'][-1]['evidence'],
            })
            raise fixture.FixtureError(message)

    def target_state(accepted_ids,contributions):
        state=fixture.capture_repo_state(source)
        baseline=manifest['caller_snapshot']
        expected_files=dict(baseline['working_tree']['files'])
        expected_status=dict(baseline['status'])
        for worker_id in accepted_ids:
            contribution=contributions[worker_id]
            expected_files[contribution['path']]=f"sha256:{contribution['module_sha256']}"
            expected_status[contribution['path']]=' M'
        actual_files=state['working_tree']['files']
        file_differences=sorted(
            path for path in set(expected_files)|set(actual_files)
            if expected_files.get(path)!=actual_files.get(path)
        )
        checks={
            'root':state['root']==baseline['root'],
            'common_dir':state['common_dir']==baseline['common_dir'],
            'branch':state['branch']==baseline['branch'],
            'head':state['head']==baseline['head'],
            'index_path':state['index_path']==baseline['index_path'],
            'index_entries':state['index_entries']==baseline['index_entries'],
            'index_tree':state['index_tree']==baseline['index_tree'],
            'cached_diff_sha256':state['cached_diff_sha256']==baseline['cached_diff_sha256'],
            'unstaged_dirty_diffs':state['unstaged_dirty_diffs']==baseline['unstaged_dirty_diffs'],
            'working_tree_files':not file_differences,
            'working_tree_directories':state['working_tree']['directories']==baseline['working_tree']['directories'],
            'status':state['status']==expected_status,
        }
        details={
            'accepted_worker_ids':list(accepted_ids),
            'file_differences':file_differences,
            'expected_status':expected_status,
            'actual_status':state['status'],
            'expected_index_tree':baseline['index_tree'],
            'actual_index_tree':state['index_tree'],
            'expected_index_entries_sha256':baseline['index_entries_sha256'],
            'actual_index_entries_sha256':state['index_entries_sha256'],
            'raw_index_sha256_informational':{
                'expected':baseline['index_raw_sha256'],
                'actual':state['index_raw_sha256'],
                'unchanged':baseline['index_raw_sha256']==state['index_raw_sha256'],
            },
        }
        return state,checks,details

    save()
    contributions={}
    try:
        patch_dir.mkdir()
        setup_path=run/'operator/setup-result.json'
        setup=json.loads(setup_path.read_text(encoding='utf-8'))
        expected_ids_set=set(expected_ids)
        setup_workers=setup.get('workers')
        setup_worker_ids=(
            [worker.get('worker_id') for worker in setup_workers]
            if isinstance(setup_workers,list) else []
        )
        setup_check=(
            setup.get('status')=='PREPARED'
            and setup.get('source')==str(Path(manifest['paths']['caller']).resolve())
            and setup.get('source_head')==manifest['caller_snapshot']['head']
            and len(setup_worker_ids)==len(expected_ids)
            and len(set(setup_worker_ids))==len(setup_worker_ids)
            and set(setup_worker_ids)==expected_ids_set
        )
        require_check(
            'prepared_setup_result_bound',setup_check,
            {'status':setup.get('status'),'source':setup.get('source'),'source_head':setup.get('source_head'),
             'worker_ids':setup_worker_ids},
            'Setup result is missing, failed, or not bound to this frozen run',
        )

        setup_by_id={worker['worker_id']:worker for worker in setup_workers}
        source=Path(manifest['paths']['caller']).resolve()
        package=Path(manifest['paths']['package']).resolve()
        helper=package/'scripts/ask_agent_workspace.py'
        card=package/'SKILL.md'
        package_digest=fixture.package_tree_sha256(package)
        package_check=(
            package_digest==manifest['source']['package_tree_sha256']
            and setup.get('frozen_package_tree_sha256_before_preparation')==package_digest
            and setup.get('frozen_package_tree_sha256_after_preparation')==package_digest
        )
        require_check(
            'frozen_package_hash_verified',package_check,
            {'manifest':manifest['source']['package_tree_sha256'],'setup_before':setup.get('frozen_package_tree_sha256_before_preparation'),
             'setup_after':setup.get('frozen_package_tree_sha256_after_preparation'),'actual':package_digest},
            'Frozen helper package hash does not match setup and fixture manifests',
        )
        source_before=fixture.capture_repo_state(source)
        baseline=manifest['caller_snapshot']
        source_baseline_match=all(source_before.get(key)==baseline.get(key) for key in (
            'root','common_dir','index_path','branch','head','index_entries','index_tree',
            'index_entries_sha256','cached_diff_sha256','unstaged_dirty_diffs','status','working_tree',
        ))
        require_check(
            'frozen_source_before_collection',source_baseline_match,
            {'root':source_before['root'],'branch':source_before['branch'],'head':source_before['head'],
             'index_tree':source_before['index_tree'],'index_entries_sha256':source_before['index_entries_sha256'],
             'status':source_before['status'],'working_tree':source_before['working_tree']},
            'Caller HEAD, semantic index, or dirty working tree drifted from the frozen input',
            code='FROZEN_SOURCE_DRIFT',
            expected={'head':baseline['head'],'index_tree':baseline['index_tree'],
                      'index_entries_sha256':baseline['index_entries_sha256'],'status':baseline['status']},
        )

        reference_identity=setup.get('package_identity')
        identity_check=(
            isinstance(reference_identity,dict)
            and reference_identity.get('status')=='verified'
            and all(setup_by_id[worker_id].get('package_identity')==reference_identity for worker_id in expected_ids)
        )
        require_check(
            'prepared_identity_records_match',identity_check,
            {'worker_ids':expected_ids,'identity':reference_identity},
            'Setup package identities are incomplete or inconsistent',
        )

        ordered_tasks=sorted(manifest['task_assignments'],key=lambda task:int(task['worker_id']))
        for task in ordered_tasks:
            worker_id=task['worker_id']
            setup_worker=setup_by_id[worker_id]
            identity_stdout=run_action(
                f'identity-{worker_id}',
                [sys.executable,'-B',str(helper),'identity','--skill-card',str(card)],
                cwd=source,
            )
            identity=json.loads(identity_stdout)
            identity_matches=(
                isinstance(identity,dict)
                and identity.get('status')=='verified'
                and identity==reference_identity
                and identity==setup_worker['package_identity']
                and identity.get('helper_sha256')==fixture.sha256_file(helper)
                and identity.get('skill_card_sha256')==fixture.sha256_file(card)
            )
            require_check(
                f'worker_{worker_id}_identity_reverified',identity_matches,
                {'worker_id':worker_id,'identity':identity},
                f'Worker {worker_id} identity no longer matches the prepared frozen package',
                code='PACKAGE_IDENTITY_MISMATCH',expected=reference_identity,
            )

            inspect_stdout=run_action(
                f'inspect-returned-{worker_id}',
                [sys.executable,'-B',str(helper),'inspect','--receipt',setup_worker['receipt'],
                 '--phase','returned','--delivery-mode','patch','--artifact',OWNER_MARKER],
                cwd=source,
            )
            inspected=json.loads(inspect_stdout)
            task_path=task['path']
            delivery=inspected.get('delivery') if isinstance(inspected,dict) else None
            evidence_record=inspected.get('evidence') if isinstance(inspected,dict) else None
            inspect_binding=(
                isinstance(inspected,dict)
                and inspected.get('status')=='returned'
                and inspected.get('phase')=='returned'
                and all(inspected.get(key)==setup_worker.get(key) for key in ('receipt','worktree','branch'))
                and inspected.get('contribution_paths')==[task_path]
                and inspected.get('artifacts')==[OWNER_MARKER]
                and isinstance(inspected.get('changed_paths'),list)
                and task_path in inspected.get('changed_paths',[])
                and isinstance(delivery,dict)
                and delivery.get('mode')=='patch'
                and delivery.get('contribution_paths')==[task_path]
                and isinstance(evidence_record,dict)
                and delivery.get('contribution_patch')==evidence_record.get('contribution_patch')
            )
            require_check(
                f'worker_{worker_id}_returned_inspection_valid',inspect_binding,
                {'worker_id':worker_id,'inspection':inspected},
                f'Worker {worker_id} returned inspection is not bound to its sole owned contribution',
                code='RETURNED_INSPECTION_INVALID',
                expected={'status':'returned','phase':'returned','receipt':setup_worker.get('receipt'),
                          'worktree':setup_worker.get('worktree'),'branch':setup_worker.get('branch'),
                          'contribution_paths':[task_path],'artifacts':[OWNER_MARKER]},
            )
            worktree=Path(setup_worker['worktree']).resolve()
            actual_root=Path(fixture.git(worktree,'rev-parse','--show-toplevel')).resolve()
            child_state=fixture.capture_repo_state(actual_root,worker_mode=True)
            child_checks,child_details=fixture.state_checks(child_state,manifest,worker_id,'finish')
            child_state_ok=(
                actual_root==worktree
                and child_state['branch']==setup_worker['branch']
                and all(child_checks.values())
            )
            require_check(
                f'worker_{worker_id}_finish_snapshot_valid',child_state_ok,
                {'root':str(actual_root),'branch':child_state['branch'],'checks':child_checks,'details':child_details},
                f'Worker {worker_id} finish snapshot differs from the frozen caller outside its owned step',
                code='WORKER_FINISH_STATE_INVALID',
                expected={'owned_path':task_path,'head':manifest['caller_snapshot']['head']},
            )
            module_path=actual_root/task_path
            if module_path.is_symlink() or not module_path.is_file():
                raise fixture.FixtureError(f'Worker {worker_id} owned module is not a regular file')
            module_bytes=module_path.read_bytes()
            module_digest=fixture.sha256_bytes(module_bytes)
            module_snapshot_digest=child_state['working_tree']['files'].get(task_path)
            snapshot_digest_matches=(module_snapshot_digest==f'sha256:{module_digest}')
            require_check(
                f'worker_{worker_id}_module_bytes_bound',snapshot_digest_matches,
                {'worker_id':worker_id,'module_sha256':module_digest,'snapshot_sha256':module_snapshot_digest},
                f'Worker {worker_id} module bytes differ from its finish snapshot',
                code='WORKER_MODULE_SNAPSHOT_MISMATCH',
                expected=f'sha256:{module_digest}',
            )
            oracle=fixture.check_module_oracle(module_path,int(worker_id))
            require_check(
                f'worker_{worker_id}_task_oracle_passed',oracle.get('passed') is True,
                {'worker_id':worker_id,'oracle':oracle},
                f'Worker {worker_id} module failed its independent task oracle',
                code='WORKER_ORACLE_FAILED',
                expected={'task_id':worker_id,'formula':'(task_id+1)*x+task_id*task_id'},
            )
            evidence=evidence_record
            source_patch_value=evidence.get('contribution_patch') if isinstance(evidence,dict) else None
            if not isinstance(source_patch_value,str):
                raise fixture.FixtureError(f'Worker {worker_id} inspection omitted its contribution patch')
            source_patch=Path(source_patch_value)
            if source_patch.is_symlink() or not source_patch.is_file():
                raise fixture.FixtureError(f'Worker {worker_id} contribution patch is missing or is a symlink')
            resolved_source_patch=source_patch.resolve()
            try:
                resolved_source_patch.relative_to((run/'workspace-store').resolve())
            except ValueError as exc:
                raise fixture.FixtureError(f'Worker {worker_id} contribution patch is outside the fixture store') from exc
            patch_bytes=resolved_source_patch.read_bytes()
            patch_path=patch_dir/f'worker-{worker_id}.patch'
            _write_immutable_patch(patch_path,patch_bytes)
            patch_digest=fixture.sha256_bytes(patch_bytes)
            require_check(
                f'worker_{worker_id}_patch_copy_exact',
                fixture.sha256_file(patch_path)==patch_digest,
                {'source_patch_path':str(resolved_source_patch),'patch_path':str(patch_path),
                 'expected_sha256':patch_digest,'actual_sha256':fixture.sha256_file(patch_path)},
                f'Worker {worker_id} immutable patch copy differs from helper evidence',
                code='PATCH_COPY_MISMATCH',expected=patch_digest,
            )
            contribution={
                'worker_id':worker_id,'path':task_path,'worktree':str(actual_root),
                'receipt':setup_worker['receipt'],'branch':setup_worker['branch'],
                'source_patch_path':str(resolved_source_patch),'patch_path':str(patch_path),
                'patch_sha256':patch_digest,'patch_size_bytes':len(patch_bytes),
                'module_sha256':module_digest,'module_oracle':oracle,
                'returned_inspection':inspected,'finish_checks':child_checks,
                'finish_details':child_details,
            }
            contributions[worker_id]=contribution
            result['patches'].append(contribution)
            save()

        collected_package_digest=fixture.package_tree_sha256(package)
        require_check(
            'frozen_package_hash_unchanged_after_collection',
            collected_package_digest==manifest['source']['package_tree_sha256'],
            {'expected':manifest['source']['package_tree_sha256'],'actual':collected_package_digest},
            'Frozen package changed while collecting worker contributions',
        )
        source_after_collection=fixture.capture_repo_state(source)
        source_unchanged=all(source_after_collection.get(key)==source_before.get(key) for key in (
            'root','common_dir','index_path','branch','head','index_entries','index_tree',
            'index_entries_sha256','cached_diff_sha256','unstaged_dirty_diffs','status','working_tree',
        ))
        require_check(
            'source_unchanged_after_collection',source_unchanged,
            {'head':source_after_collection['head'],'index_tree':source_after_collection['index_tree'],
             'status':source_after_collection['status'],'working_tree':source_after_collection['working_tree']},
            'Caller changed while contributions were being collected',
        )

        apply_prefix=['git','-C',str(source),'-c','core.autocrlf=false','apply']
        for contribution in result['patches']:
            patch_path=contribution['patch_path']
            if fixture.sha256_file(Path(patch_path))!=contribution['patch_sha256']:
                raise fixture.FixtureError(f"Worker {contribution['worker_id']} immutable patch hash changed")
            numstat_text=run_action(
                f"patch-numstat-{contribution['worker_id']}",
                [*apply_prefix,'--numstat',patch_path],
            )
            numstat_rows=[]
            for row in numstat_text.splitlines():
                fields=row.split('\t',2)
                if len(fields)!=3:
                    raise fixture.FixtureError(f"Worker {contribution['worker_id']} patch has malformed numstat output")
                numstat_rows.append(fields[2])
            require_check(
                f"worker_{contribution['worker_id']}_patch_paths_exact",
                numstat_rows==[contribution['path']],
                {'worker_id':contribution['worker_id'],'paths':numstat_rows,'expected':[contribution['path']]},
                f"Worker {contribution['worker_id']} patch contains paths outside its owned module",
                code='PATCH_PATHS_INVALID',expected=[contribution['path']],
            )
            contribution['patch_numstat_paths']=numstat_rows
            save()
        initial_target,initial_checks,initial_details=target_state([],contributions)
        require_check(
            'caller_state_before_patch_checks',all(initial_checks.values()),
            {'checks':initial_checks,'details':initial_details},
            'Caller state drifted before patch validation',
            code='FROZEN_SOURCE_DRIFT',
            expected={'head':manifest['caller_snapshot']['head'],
                      'index_tree':manifest['caller_snapshot']['index_tree'],'accepted_worker_ids':[]},
        )
        for contribution in result['patches']:
            run_action(
                f"patch-check-initial-{contribution['worker_id']}",
                [*apply_prefix,'--check','--binary','--whitespace=nowarn',contribution['patch_path']],
            )
            require_check(
                f"worker_{contribution['worker_id']}_patch_hash_after_check",
                fixture.sha256_file(Path(contribution['patch_path']))==contribution['patch_sha256'],
                {'worker_id':contribution['worker_id'],'patch_sha256':contribution['patch_sha256']},
                f"Worker {contribution['worker_id']} patch changed during validation",
            )

        accepted_ids=[]
        for contribution in result['patches']:
            worker_id=contribution['worker_id']
            before_apply,before_checks,before_details=target_state(accepted_ids,contributions)
            require_check(
                f'caller_state_before_apply_{worker_id}',all(before_checks.values()),
                {'checks':before_checks,'details':before_details},
                f'Caller drifted before applying worker {worker_id}; preserving prior progress',
                code='SOURCE_DRIFT_BEFORE_APPLY',
                expected={'accepted_worker_ids':list(accepted_ids),
                          'head':manifest['caller_snapshot']['head'],
                          'index_tree':manifest['caller_snapshot']['index_tree']},
            )
            require_check(
                f'worker_{worker_id}_patch_hash_before_apply',
                fixture.sha256_file(Path(contribution['patch_path']))==contribution['patch_sha256'],
                {'worker_id':worker_id,'patch_sha256':contribution['patch_sha256']},
                f'Worker {worker_id} immutable patch changed before apply',
            )
            run_action(
                f'patch-check-{worker_id}',
                [*apply_prefix,'--check','--binary','--whitespace=nowarn',contribution['patch_path']],
            )
            run_action(
                f'patch-apply-{worker_id}',
                [*apply_prefix,'--binary','--whitespace=nowarn',contribution['patch_path']],
            )
            result['applied_worker_ids'].append(worker_id)
            accepted_ids.append(worker_id)
            save()
            after_apply,after_checks,after_details=target_state(accepted_ids,contributions)
            require_check(
                f'caller_state_after_apply_{worker_id}',all(after_checks.values()),
                {'checks':after_checks,'details':after_details},
                f'Caller state changed outside worker {worker_id} patch application; preserving applied bytes',
            )
            require_check(
                f'worker_{worker_id}_patch_hash_after_apply',
                fixture.sha256_file(Path(contribution['patch_path']))==contribution['patch_sha256'],
                {'worker_id':worker_id,'patch_sha256':contribution['patch_sha256']},
                f'Worker {worker_id} patch changed during apply',
            )

        verify_started=time.time()
        try:
            verification=fixture.verify_fixture(run)
            verify_error=None
            verify_exit=0 if verification.get('passed') is True else 1
            verify_stdout=json.dumps(verification,sort_keys=True)
            verify_stderr=''
        except Exception as exc:
            verification=None
            verify_error=f'{type(exc).__name__}: {exc}'
            verify_exit=None
            verify_stdout=''
            verify_stderr=verify_error
        verify_record={
            'label':'fixture-verify','argv':['fixture.verify_fixture',str(run)],
            'started_epoch':verify_started,'elapsed_s':time.time()-verify_started,
            'exit_code':verify_exit,'stdout':verify_stdout,'stderr':verify_stderr,
        }
        if verify_error:
            verify_record['error']=verify_error
        save_action(verify_record)
        result['fixture_verification']=verification
        require_check(
            'fixture_verify_passed',verification is not None and verification.get('passed') is True,
            {'verification':verification},
            'Final fixture verifier did not pass; preserving patches and applied progress',
            code='FINAL_FIXTURE_VERIFICATION_FAILED',
            expected={'passed':True,'applied_worker_ids':expected_ids},
        )
        result['phase']='integrated'
        result['status']='INTEGRATED'
    except Exception as exc:
        result['status']='FAILED'
        result['error']=f'{type(exc).__name__}: {exc}'
        evidence_path=failure_context.get('evidence_path')
        if evidence_path is None:
            evidence_path=result['actions'][-1]['evidence'] if result['actions'] else str(output)
        result['failure']={
            'code':failure_context.get('code','INTEGRATION_FAILED'),
            'phase':failure_context.get('phase',result.get('phase')),
            'message':str(exc),
            'expected':failure_context.get('expected','all integration assertions and validation checks pass'),
            'observed':failure_context.get('observed',{'error':f'{type(exc).__name__}: {exc}'}),
            'evidence_path':evidence_path,
            'applied_worker_ids':list(result['applied_worker_ids']),
            'retry_semantics':result['retry_semantics'],
        }
        result['error_code']=result['failure']['code']
        raise
    finally:
        save()
    return result


def _cli_failure_diagnostic(run, command, exc, worker_id=None):
    run=Path(run).expanduser().resolve()
    operator_dir=run/'operator'
    if command=='prepare-batch':
        result_path=operator_dir/'setup-result.json'
    elif command=='verify-return' and worker_id:
        result_path=operator_dir/'compact-returns'/f'worker-{worker_id}.json'
    else:
        result_path=operator_dir/'integration-result.json'
    result=None
    try:
        result=json.loads(result_path.read_text(encoding='utf-8'))
    except (OSError,ValueError):
        pass
    failure=result.get('failure') if isinstance(result,dict) else None
    if not isinstance(failure,dict):
        failure={}

    code=failure.get('code') or getattr(exc,'diagnostic_code',None)
    if not isinstance(code,str) or re.fullmatch(r'[A-Z][A-Z0-9_]{1,63}',code) is None:
        match=re.match(r'^\[([A-Z][A-Z0-9_]{1,63})\]',str(exc))
        code=match.group(1) if match else ('SETUP_OPERATION_FAILED' if command=='prepare-batch' else 'INTEGRATION_FAILED')
    phase=failure.get('phase') or getattr(exc,'diagnostic_phase',None)
    if not isinstance(phase,str) or not phase:
        phase=result.get('phase') if isinstance(result,dict) and isinstance(result.get('phase'),str) else 'argument_validation'
    expected=failure.get('expected')
    if expected is None:
        expected=getattr(exc,'diagnostic_expected',None)
    if expected is None:
        expected='The operation satisfies the frozen-input, worker-ownership, and delivery checks.'
    observed=failure.get('observed')
    if observed is None:
        observed=getattr(exc,'diagnostic_observed',None)
    if observed is None:
        observed={'error':f'{type(exc).__name__}: {exc}'}

    evidence=[diagnostics.evidence_reference(
        result_path,
        json_pointer='/failure' if failure else '/status',
    )]
    detail_path=failure.get('evidence_path')
    if isinstance(detail_path,str) and detail_path and Path(detail_path).resolve()!=result_path.resolve():
        evidence.append(diagnostics.evidence_reference(detail_path))
    manifest_path=run/'manifest.json'
    evidence.append(diagnostics.evidence_reference(manifest_path))

    retry_safety=failure.get('retry_semantics')
    if not isinstance(retry_safety,str) or not retry_safety.strip():
        retry_safety=(
            'Keep this run evidence. Do not repeat setup or integration in this run; '
            'reconcile the failure and use a fresh run for another attempt.'
        )
    return diagnostics.make_diagnostic(
        code=code,
        severity='error',
        phase=phase,
        expected=expected,
        observed=observed,
        rationale=(
            'Setup and patch integration must remain bound to the frozen task, worker receipts, '
            'and caller state; proceeding after a failed check can invalidate attribution or obscure partial work.'
        ),
        rationale_ref='CONTRACT.md#retry-safety',
        evidence=evidence,
        recovery=(
            'Inspect the cited result and call log. Preserve receipts, immutable patch copies, and any applied '
            'modules; reconcile the cause before using a fresh run.'
        ),
        retry_safety=retry_safety,
    )


def integration_summary(run, result):
    """Compact LLM response; complete expectations, calls and checks stay in the result file."""
    if result.get('status')!='INTEGRATED' or result.get('fixture_verification',{}).get('passed') is not True:
        raise fixture.FixtureError('Cannot summarize an unaccepted integration as successful')
    return {'status':result['status'],'applied_worker_ids':result['applied_worker_ids'],
            'elapsed_s':result['elapsed_s'],'result_path':str(Path(run).resolve()/'operator/integration-result.json'),
            'verification_path':str(Path(run).resolve()/'operator/verification.json'),
            'patches':[{k:p[k] for k in ('worker_id','path','patch_path','patch_sha256')} for p in result['patches']],
            'native_lifecycle_note':result['native_lifecycle_note']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare-batch','verify-return','integrate-batch']);p.add_argument('--run',required=True)
    p.add_argument('--compact',action='store_true',help='prepare worker worktrees through ask_agent_task.py')
    p.add_argument('--worker',help='worker ID for compact verify-return')
    p.add_argument('--collected-worker',action='append',required=False,
                   help='explicit parent assertion of a collected worker id (repeat for every worker)')
    a=p.parse_args()
    try:
        if a.command=='prepare-batch':
            result=prepare_batch(a.run,compact=a.compact)
            # All inspection details stay in setup-result.json and the exact helper logs.
            compact={**result,'workers':[{k:v for k,v in w.items() if k!='prepared_inspection'} for w in result['workers']]}
            print(json.dumps(compact,indent=2))
        elif a.command=='verify-return':
            if not a.worker:
                p.error('verify-return requires --worker')
            result=verify_compact_return(a.run,a.worker)
            print(json.dumps(result,indent=2))
        else:
            if a.compact:
                p.error('--compact applies only to prepare-batch')
            result=integrate_batch(a.run,a.collected_worker or [])
            print(json.dumps(integration_summary(a.run,result),indent=2))
    except Exception as exc:
        diagnostic=_cli_failure_diagnostic(a.run,a.command,exc,a.worker)
        operator_dir=Path(a.run).expanduser().resolve()/'operator'
        jsonl_path=operator_dir/'diagnostics.jsonl' if operator_dir.is_dir() else None
        diagnostics.exit_with_diagnostic(diagnostic,jsonl_path=jsonl_path)
