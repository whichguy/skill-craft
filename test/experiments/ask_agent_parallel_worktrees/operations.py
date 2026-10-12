#!/usr/bin/env python3
"""Test-only managed-worktree setup and delivery integration; no native lifecycle proof."""
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
        packet_bytes=binding_path.read_bytes()
        binding=json.loads(packet_bytes.decode('utf-8'))
    except (OSError,ValueError) as exc:
        _compact_return_error('COMPACT_RETURN_BINDING_INVALID','cannot read compact binding JSON',
                              {'readable_json':str(binding_path)},
                              {'error':f'{type(exc).__name__}: {exc}'})
    packet_digest=hashlib.sha256(packet_bytes).hexdigest()
    if packet_digest!=worker.get('compact_packet_sha256'):
        _compact_return_error('COMPACT_RETURN_BINDING_INVALID','retained packet bytes differ from compact setup',
                              {'packet_sha256':worker.get('compact_packet_sha256')},
                              {'packet_sha256':packet_digest})
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
    delivery_mode=manifest.get('delivery_mode','patch')
    task_mode='ephemeral' if delivery_mode=='ephemeral' else 'edit'
    expected_write_set=sorted([worker['path'],OWNER_MARKER]) if delivery_mode=='ephemeral' else [worker['path']]
    checks={
        'setup_delivery_matches':setup.get('delivery_mode',manifest.get('delivery_mode','patch'))==delivery_mode,
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
        and bound_task.get('expected_result')==expected_result and bound_task.get('mode')==task_mode
        and bound_task.get('write_set')==expected_write_set
        and (bound_task.get('delivery_mode')==delivery_mode if task_mode=='edit'
             else bound_task.get('delivery_mode') is None),
        'workspace_matches_setup':bound_workspace.get('route')=='worktree'
        and bound_workspace.get('source')==manifest['paths']['caller']
        and bound_workspace.get('root')==worker.get('worktree')
        and bound_workspace.get('launch_cwd')==worker.get('worktree')
        and bound_workspace.get('receipt')==worker.get('receipt')
        and bound_workspace.get('baseline')==worker.get('prepared_inspection',{}).get('baseline')
        and bound_workspace.get('branch')==worker.get('branch')
        and bound_workspace.get('prepared_fingerprint')==worker.get('prepared_inspection',{}).get('fingerprint')
        and (delivery_mode!='commits' or
             (bound_workspace.get('commit_base')==worker.get('commit_base')
              and bound_workspace.get('snapshot')==worker.get('snapshot'))),
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
    delivery_mode=fixture.fixture_delivery_mode(manifest)
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
    argv=[sys.executable,'-B',str(task_script),'verify-return','--binding',str(binding_path),
          '--expected-binding-sha256',binding['binding_sha256']]
    started=time.time()
    record={'schema':'ask-agent.compact-command/v1','phase':'verify-return','run_id':manifest['run_id'],'worker_id':worker_id,
            'delivery_mode':delivery_mode,
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
    passed=(record.get('exit_code')==0 and _compact_return_result_valid(
        result,manifest,setup,worker,binding))
    record['status']='PASSED' if passed else 'FAILED'
    record['evidence_path']=str(record_path.resolve())
    fixture.write_exclusive_json(record_path,record)
    if not passed:
        error=fixture.FixtureError(f'[COMPACT_RETURN_CHECK_FAILED] worker {worker_id} compact verify-return did not confirm its bound contribution; evidence: {record_path}')
        error.diagnostic_code='COMPACT_RETURN_CHECK_FAILED'
        error.diagnostic_phase='compact-verify-return'
        error.diagnostic_expected={'status':'READY_FOR_PARENT_ACCEPTANCE','binding_sha256':binding['binding_sha256'],
                                   'delivery_mode':manifest.get('delivery_mode','patch'),
                                   'receipt':worker['receipt'],'worktree':worker['worktree'],'contribution_paths':[worker['path']]}
        error.diagnostic_observed={'exit_code':record.get('exit_code'),'result':result,'error':record.get('error'),
                                   'evidence_path':str(record_path)}
        raise error
    return {'status':'PASSED','worker_id':worker_id,'binding_sha256':binding['binding_sha256'],
            'delivery_mode':manifest.get('delivery_mode','patch'),
            'evidence_path':str(record_path.resolve()),
            'contribution_paths':[worker['path']]}


def _compact_return_result_valid(result,manifest,setup,worker,binding):
    if not (isinstance(result,dict)
            and result.get('status')=='READY_FOR_PARENT_ACCEPTANCE'
            and result.get('command')=='verify-return'
            and result.get('binding_sha256')==binding.get('binding_sha256')):
        return False
    evidence=result.get('workspace_evidence',{})
    if not isinstance(evidence,dict):
        return False
    mode=manifest.get('delivery_mode','patch')
    if mode=='ephemeral':
        audit=evidence.get('ephemeral_audit')
        if not isinstance(audit,dict):
            return False
        paths=audit.get('changed_paths')
        expected_paths=[worker['path'],OWNER_MARKER]
        expected_audit_fields={'status','findings_only','changed_paths','baseline_fingerprint',
                               'fingerprint','head','branch','scratch_retained'}
        forbidden={'inspection','delivery','contribution_patch','patch_path','patch_sha256',
                   'commits','commit_base','contribution_commits','integration_strategy'}
        return (audit.get('findings_only') is True
                and set(audit)==expected_audit_fields
                and isinstance(paths,list) and set(paths)==set(expected_paths)
                and len(paths)==len(expected_paths)
                and audit.get('status')=='ephemeral-audit'
                and isinstance(audit.get('baseline_fingerprint'),str)
                and isinstance(audit.get('fingerprint'),str)
                and audit.get('baseline_fingerprint')==worker.get('prepared_inspection',{}).get('fingerprint')
                and audit.get('head')==manifest.get('caller_snapshot',{}).get('head')
                and audit.get('branch')==worker.get('branch')
                and audit.get('scratch_retained') is True
                and not any(key in evidence for key in forbidden)
                and not any(key in result for key in forbidden))
    inspection=evidence.get('inspection')
    if not isinstance(inspection,dict):
        return False
    common=(inspection.get('status')=='returned'
            and inspection.get('receipt')==worker.get('receipt')
            and inspection.get('worktree')==worker.get('worktree')
            and inspection.get('contribution_paths')==[worker.get('path')])
    if mode=='patch':
        delivery=inspection.get('delivery')
        return (common and isinstance(delivery,dict) and delivery.get('mode')=='patch'
                and delivery.get('contribution_paths')==[worker.get('path')])
    snapshot=worker.get('snapshot',{})
    delivery=inspection.get('delivery')
    strategy=result.get('integration_strategy')
    if mode!='commits' or not (common and isinstance(delivery,dict)):
        return False
    commits=delivery.get('commits')
    per_commit=delivery.get('per_commit_paths')
    return (delivery.get('mode')=='commits'
            and delivery.get('base')==worker.get('commit_base')
            and isinstance(commits,list) and len(commits)>=1
            and all(isinstance(sha,str) and re.fullmatch(r'[0-9a-f]{40,64}',sha) for sha in commits)
            and len(set(commits))==len(commits)
            and worker.get('commit_base') not in commits
            and delivery.get('commit_paths')==[worker.get('path')]
            and isinstance(per_commit,list) and len(per_commit)==len(commits)
            and all(row=={'commit':sha,'paths':[worker.get('path')]}
                    for row,sha in zip(per_commit,commits))
            and delivery.get('residual_paths')==[]
            and (isinstance(delivery.get('contribution_patch'),str)
                 if snapshot.get('source_dirty') else 'contribution_patch' not in delivery)
            and isinstance(strategy,dict)
            and strategy.get('source_dirty') == snapshot.get('source_dirty')
            and strategy.get('commit_base')==worker.get('commit_base')
            and strategy.get('commits')==commits
            and strategy.get('parent_target_revalidation_required') is True
            and strategy.get('strategy')==('preserve-parent patch from commits'
                                           if snapshot.get('source_dirty') else 'eligible cherry-pick'))


def _require_compact_returns(run, setup, expected_ids):
    if setup.get('treatment')!='compact':
        return []
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
            if path.is_symlink() or not path.is_file():
                raise fixture.FixtureError(f'compact return evidence is not a regular in-run file: {path}')
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
        valid=(isinstance(result,dict)
               and record.get('status')=='PASSED' and record.get('exit_code')==0
               and record.get('schema')=='ask-agent.compact-command/v1' and record.get('phase')=='verify-return'
               and record.get('worker_id')==worker_id
               and record.get('evidence_path')==str(path.resolve())
               and record.get('command_status') in (None,'COMPLETED')
               and record.get('binding_path')==str(binding_path.resolve())
               and record.get('argv')==[sys.executable,'-B',str(task_script),'verify-return','--binding',str(binding_path.resolve()),
                                        '--expected-binding-sha256',binding['binding_sha256']]
               and record.get('cwd')==caller and stdout_result==result
               and record.get('run_id')==manifest.get('run_id')
               and record.get('binding_sha256')==binding.get('binding_sha256')==worker.get('compact_binding_sha256')
               and _compact_return_result_valid(result,manifest,setup,worker,binding))
        records.append({'worker_id':worker_id,'valid':valid,'evidence_path':str(path.resolve()),
                        'record':record,'result':result})
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
    return records


def _canonical_sha256(value):
    payload=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def compact_prepare_summary(run, result):
    """Return the bounded v4 setup receipt; the full record remains on disk."""
    run=Path(run).expanduser().resolve()
    setup_path=run/'operator/setup-result.json'
    if setup_path.is_symlink() or not setup_path.is_file():
        raise fixture.FixtureError(f'Compact setup result is not a regular retained file: {setup_path}')
    setup_bytes=setup_path.read_bytes()
    setup=json.loads(setup_bytes.decode('utf-8'))
    if (setup.get('status')!='PREPARED' or setup.get('treatment')!='compact'
            or setup.get('compact_startup_contract')!='action-packet/v1'
            or setup.get('run_id')!=result.get('run_id')):
        raise fixture.FixtureError('Compact setup summary requires the completed v4 action-packet record')
    return {
        'schema':'ask-agent.compact-prepare-summary/v1',
        'status':setup['status'],
        'run_id':setup['run_id'],
        'treatment':setup['treatment'],
        'delivery_mode':setup.get('delivery_mode'),
        'setup_path':str(setup_path.resolve()),
        'setup_sha256':hashlib.sha256(setup_bytes).hexdigest(),
        'dispatch_index_path':str((run/'operator/compact-dispatch/index.json').resolve()),
        'runtime_python_executable':setup.get('runtime_python_executable'),
    }


def _ephemeral_audit_matches(phase_audit, return_audit, expected_cwd):
    if not isinstance(phase_audit,dict) or not isinstance(return_audit,dict):
        return False
    phase_shared={key:value for key,value in phase_audit.items() if key!='actual_cwd'}
    return phase_shared==return_audit and phase_audit.get('actual_cwd')==expected_cwd


def _assert_collected_ids(manifest, collected_worker_ids):
    expected_ids=[task['worker_id'] for task in manifest['task_assignments']]
    if (not isinstance(collected_worker_ids,(list,tuple))
            or any(not isinstance(worker_id,str) for worker_id in collected_worker_ids)
            or len(collected_worker_ids)!=len(expected_ids)
            or len(set(collected_worker_ids))!=len(collected_worker_ids)
            or list(collected_worker_ids)!=expected_ids):
        error=fixture.FixtureError(
            f'[PARENT_COLLECTION_ASSERTION_INVALID] expected every manifest id exactly once: {expected_ids}; '
            f'observed {collected_worker_ids!r}; no integration files were written'
        )
        error.diagnostic_code='PARENT_COLLECTION_ASSERTION_INVALID'
        error.diagnostic_phase='argument_validation'
        error.diagnostic_expected={'manifest_worker_ids_exactly_once':expected_ids}
        error.diagnostic_observed={'collected_worker_ids':list(collected_worker_ids)
                                   if isinstance(collected_worker_ids,(list,tuple)) else repr(collected_worker_ids)}
        raise error
    return expected_ids


def finish_ephemeral(run, collected_worker_ids):
    """Retain independently checked findings without importing worker changes."""
    run=Path(run).resolve()
    manifest=fixture.load_manifest(run)
    if manifest.get('delivery_mode')!='ephemeral':
        raise fixture.FixtureError('[EPHEMERAL_MODE_REQUIRED] finalization requires an ephemeral fixture')
    expected_ids=_assert_collected_ids(manifest,collected_worker_ids)
    setup=json.loads((run/'operator/setup-result.json').read_text(encoding='utf-8'))
    return_records=_require_compact_returns(run,setup,expected_ids)
    if setup.get('treatment')!='compact' or setup.get('delivery_mode')!='ephemeral':
        raise fixture.FixtureError('[EPHEMERAL_MODE_REQUIRED] setup is not the retained ephemeral compact attempt')
    output=run/'operator/integration-result.json'
    log_dir=run/'operator/integration-calls'
    if output.exists() or log_dir.exists():
        raise fixture.FixtureError(
            f'[INTEGRATION_ALREADY_ATTEMPTED] ephemeral finalization evidence already exists at {output} or {log_dir}'
        )
    log_dir.mkdir()
    baseline=manifest['caller_snapshot']
    baseline_sha=_canonical_sha256(baseline)
    result={'schema':'ask-agent.integration-result/v2','run_id':manifest['run_id'],
            'status':'FINALIZING','delivery_mode':'ephemeral','worker_ids':expected_ids,
            'parent_asserted_collected_worker_ids':list(collected_worker_ids),
            'caller_snapshot':baseline,'caller_snapshot_sha256':baseline_sha,'workers':[],
            'retry_semantics':'One finalization per run. Preserve this record and all scratch worktrees on failure.'}
    try:
        caller=Path(manifest['paths']['caller']).resolve()
        caller_before=fixture.capture_repo_state(caller)
        frozen_fields=tuple(baseline)
        if any(caller_before.get(key)!=baseline.get(key) for key in frozen_fields):
            raise fixture.FixtureError('Caller changed from the frozen source snapshot before ephemeral finalization')
        return_by_id={row['worker_id']:row for row in return_records}
        setup_by_id={worker['worker_id']:worker for worker in setup['workers']}
        for task in sorted(manifest['task_assignments'],key=lambda item:int(item['worker_id'])):
            worker_id=task['worker_id']
            worker=setup_by_id[worker_id]
            returned=return_by_id[worker_id]['result']
            audit=returned['workspace_evidence']['ephemeral_audit']
            phase_path=run/'operator/worker-phases'/f'worker-{worker_id}-finish'/'attempt.json'
            phase=json.loads(phase_path.read_text(encoding='utf-8'))
            phase_audit=phase.get('ephemeral_audit')
            if (phase.get('status')!='PASSED' or phase.get('worker_id')!=worker_id
                    or phase.get('root')!=worker.get('worktree')
                    or phase.get('checks',{}).get('production_worker_finish_passed') is not True
                    or phase.get('checks',{}).get('ephemeral_findings_only') is not True
                    or not _ephemeral_audit_matches(phase_audit,audit,str(Path(worker['worktree']).resolve()))):
                raise fixture.FixtureError(f'Worker {worker_id} lacks matching successful ephemeral worker-finish evidence')
            root=Path(worker['worktree']).resolve(strict=True)
            state=fixture.capture_repo_state(root,worker_mode=True)
            checks,details=fixture.state_checks(
                state,manifest,worker_id,'finish',expected_worker_branch=worker.get('branch'))
            if not all(checks.values()):
                raise fixture.FixtureError(f'Worker {worker_id} scratch snapshot failed: {details}')
            module=root/task['path']
            if module.is_symlink() or not module.is_file():
                raise fixture.FixtureError(f'Worker {worker_id} scratch module is not a regular file')
            oracle=fixture.check_module_oracle(module,int(worker_id))
            if oracle.get('passed') is not True:
                raise fixture.FixtureError(f'Worker {worker_id} scratch result failed the independent task oracle')
            finding={'worker_id':worker_id,'path':task['path'],
                     'formula':f'({int(worker_id)}+1)*x+{int(worker_id)}*{int(worker_id)}',
                     'module_sha256':fixture.sha256_file(module),'oracle':oracle,'ephemeral_audit':audit}
            result['workers'].append({
                'worker_id':worker_id,
                'verify_return_path':return_by_id[worker_id]['evidence_path'],
                'worker_phase_path':str(phase_path.resolve()),
                'collection_ref':{'worker_id':worker_id,'kind':'parent-collected-worker-assertion'},
                'findings':finding,'findings_sha256':_canonical_sha256(finding),
            })
        caller_after=fixture.capture_repo_state(caller)
        if any(caller_after.get(key)!=baseline.get(key) for key in frozen_fields):
            raise fixture.FixtureError('Ephemeral finalization changed the frozen caller snapshot')
        result['caller_unchanged']=True
        result['status']='NO_INTEGRATION'
        result['finished_epoch']=time.time()
        fixture.write_exclusive_json(output,result)
    except Exception as exc:
        result['status']='FAILED'
        result['error']=f'{type(exc).__name__}: {exc}'
        result['finished_epoch']=time.time()
        fixture.write_exclusive_json(output,result)
        raise
    summary={'schema':result['schema'],'status':result['status'],'delivery_mode':'ephemeral',
             'worker_ids':result['worker_ids'],'result_path':str(output.resolve()),
             'caller_snapshot_sha256':baseline_sha}
    if setup.get('compact_startup_contract')=='action-packet/v1':
        summary['result_sha256']=fixture.sha256_file(output)
    return summary

def prepare_batch(run, *, compact=False, delivery_mode=None):
    run = Path(run).resolve()
    manifest = fixture.load_manifest(run)
    source = Path(manifest['paths']['caller'])
    delivery_mode = delivery_mode or manifest.get('delivery_mode', 'patch')
    if delivery_mode not in {'patch', 'commits', 'ephemeral'}:
        raise fixture.FixtureError(f'Unsupported compact delivery mode: {delivery_mode}')
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
            'delivery_mode':delivery_mode if compact else None,
            'compact_startup_contract':'action-packet/v1' if compact else None,
            'started_epoch':start,'workers':[],'calls':calls,
            'operations_script_sha256':fixture.sha256_file(Path(__file__).resolve()),
            'frozen_package_tree_sha256_before_preparation':None,
            'frozen_package_tree_sha256_after_preparation':None,
            'retry_semantics':'One setup attempt per run; failed attempts retain receipts and logs and must not be rerun.'}
    if compact:
        result.update({'run_id':manifest['run_id'],
                       'runtime_python_executable':str(Path(sys.executable).resolve())})
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
                task_mode='ephemeral' if delivery_mode=='ephemeral' else 'edit'
                write_set=sorted([task['path'],OWNER_MARKER]) if delivery_mode=='ephemeral' else [task['path']]
                request={
                    'objective':task['assignment'],
                    'expected_result':f"src/step_{identifier}.py defines transform(x)=({int(identifier)}+1)*x+{int(identifier)}*{int(identifier)} for every integer.",
                    'source':str(source),'workspace':'worktree','mode':task_mode,'write_set':write_set,
                    'current_learnings':'This fixture preserves the caller snapshot and gives this worker one owned source module.',
                    'authorization':'The parent authorizes preparation of this isolated fixture worktree and the assigned source edit.',
                    'writers_quiescent':True,'exclusive_writer':False,'store':str(run/'workspace-store'),
                }
                if delivery_mode=='patch':
                    request['delivery_mode']='patch'
                request_path=compact_prepare_dir/f'worker-{identifier}.request.json'
                fixture.write_exclusive_json(request_path,request)
                binding_path=compact_binding_dir/f'worker-{identifier}.json'
                compact_result=command_call(
                    f'compact-prepare-{identifier}',
                    [sys.executable,'-B',str(task_script),'prepare','--skill-card',str(card),
                     '--request',str(request_path),'--packet',str(binding_path.resolve())],
                )
                packet=compact_result.get('packet')
                if (compact_result.get('status')!='READY_TO_LAUNCH' or not isinstance(packet,dict)
                        or packet.get('path')!=str(binding_path.resolve()) or binding_path.is_symlink()
                        or not binding_path.is_file()):
                    raise fixture.FixtureError(f'Compact prepare did not retain the exact packet for worker {identifier}')
                packet_bytes=binding_path.read_bytes()
                packet_digest=hashlib.sha256(packet_bytes).hexdigest()
                if packet_digest!=packet.get('sha256'):
                    raise fixture.FixtureError(f'Compact prepare packet SHA-256 differs for worker {identifier}')
                binding=json.loads(packet_bytes.decode('utf-8'))
                if not isinstance(binding,dict):
                    raise fixture.FixtureError(f'Compact prepare packet is not a JSON object for worker {identifier}')
                binding_without_digest={key:value for key,value in binding.items() if key!='binding_sha256'}
                canonical_digest=hashlib.sha256(json.dumps(binding_without_digest,sort_keys=True,
                    separators=(',',':'),ensure_ascii=True).encode('utf-8')).hexdigest()
                if canonical_digest!=binding.get('binding_sha256') or packet.get('binding_sha256')!=canonical_digest:
                    raise fixture.FixtureError(f'Compact prepare binding digest differs for worker {identifier}')
                launch=compact_result.get('launch')
                commands=compact_result.get('commands')
                if (not isinstance(launch,dict) or launch.get('transport')!='packet'
                        or launch.get('cwd')!=binding.get('workspace',{}).get('root')
                        or not isinstance(launch.get('prompt'),str)
                        or not isinstance(launch.get('delivery_header'),str)
                        or not isinstance(commands,dict)):
                    raise fixture.FixtureError(f'Compact prepare launch packet is incomplete for worker {identifier}')
                bound=binding.get('workspace',{})
                for name,action,expected_cwd in (
                    ('worker-start','worker-start',str(Path(bound['root']).resolve())),
                    ('worker-finish','worker-finish',str(Path(bound['root']).resolve())),
                    ('verify-return','verify-return',str(source.resolve())),
                ):
                    command=commands.get(name)
                    argv=command.get('argv') if isinstance(command,dict) else None
                    if (not isinstance(argv,list) or any(not isinstance(value,str) for value in argv)
                            or command.get('cwd')!=expected_cwd
                            or action not in argv or '--binding' not in argv
                            or argv[argv.index('--binding')+1:argv.index('--binding')+2]!=[str(binding_path.resolve())]
                            or '--expected-binding-sha256' not in argv
                            or argv[argv.index('--expected-binding-sha256')+1:argv.index('--expected-binding-sha256')+2]
                                !=[canonical_digest]
                            or argv.count('--binding')!=1 or argv.count('--expected-binding-sha256')!=1):
                        raise fixture.FixtureError(f'Compact prepare {name} command is not digest-pinned for worker {identifier}')
                fixture.write_exclusive_json(compact_prepare_dir/f'worker-{identifier}.result.json',compact_result)
                if manifest.get('seed_compact_ignore_controls'):
                    omitted=bound.get('ignored_dependencies_omitted')
                    if (not isinstance(omitted,list) or 'unrelated-ignored-input.txt' not in omitted
                            or '.claspignore' in omitted):
                        raise fixture.FixtureError(
                            f'Compact prepare did not report the expected ignored inputs for worker {identifier}'
                        )
                if (binding.get('schema')!='ask-agent.task.binding.v1'
                        or binding.get('status')!='READY_TO_LAUNCH'
                        or binding.get('task',{}).get('write_set')!=write_set
                        or binding.get('task',{}).get('mode')!=task_mode
                        or (delivery_mode=='patch' and binding.get('task',{}).get('delivery_mode')!='patch')
                        or (delivery_mode=='commits' and binding.get('task',{}).get('delivery_mode')!='commits')
                        or (delivery_mode=='ephemeral' and binding.get('task',{}).get('delivery_mode') is not None)
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
                if delivery_mode=='commits':
                    prepared_inspection.update({'commit_base':bound.get('commit_base'),
                                                'snapshot':bound.get('snapshot')})
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
                    'compact_packet_sha256':packet_digest,
                    'compact_prepare_result_path':str((compact_prepare_dir/f'worker-{identifier}.result.json').resolve()),
                })
                if delivery_mode=='commits':
                    bound_workspace=binding.get('workspace',{})
                    commit_base=bound_workspace.get('commit_base')
                    snapshot=bound_workspace.get('snapshot')
                    worker_baseline=fixture.capture_repo_state(Path(bound['root']),worker_mode=True)
                    if (not isinstance(commit_base,str) or not commit_base
                            or re.fullmatch(r'[0-9a-f]{40,64}',commit_base) is None
                            or not isinstance(snapshot,dict)
                            or set(snapshot)!={'mode','commit','tree','created','source_dirty'}
                            or snapshot.get('mode')!='private-commit'
                            or snapshot.get('commit')!=commit_base or not isinstance(snapshot.get('tree'),str)
                            or re.fullmatch(r'[0-9a-f]{40,64}',snapshot.get('tree','')) is None
                            or not isinstance(snapshot.get('created'),bool)
                            or snapshot.get('source_dirty') is not True
                            or worker_baseline.get('head')!=commit_base
                            or worker_baseline.get('status')!={}):
                        raise fixture.FixtureError(f'Commit preparation did not bind a clean worker baseline at S for worker {identifier}')
                    worker_result.update({'commit_base':commit_base,'snapshot':snapshot,
                                          'worker_baseline':worker_baseline})
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


def integrate_batch(run, collected_worker_ids, *, delivery_mode=None):
    """Integrate validated worker contributions after an explicit collection assertion.

    The supplied ids are assertions only; a separate native-trace auditor must
    establish the actual launch, wait, and collection lifecycle.
    """
    run=Path(run).resolve()
    manifest=fixture.load_manifest(run)
    delivery_mode=delivery_mode or manifest.get('delivery_mode','patch')
    if delivery_mode not in {'patch','commits'} or manifest.get('delivery_mode','patch')!=delivery_mode:
        raise fixture.FixtureError('[DELIVERY_MODE_MISMATCH] integration mode must match a patch or commits fixture')
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
    return_records=_require_compact_returns(run,setup_for_preflight,expected_ids)
    return_by_id={row['worker_id']:row for row in return_records}

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
        'delivery_mode':delivery_mode,
        'integration_strategy':('preserve-parent patch from commits'
                                if delivery_mode=='commits' else 'preserve-parent patch'),
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
        'commit_records':[],
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

        delivery_setup_check=(setup.get('treatment')!='compact' or setup.get('delivery_mode')==delivery_mode)
        require_check(
            'prepared_delivery_mode_bound',delivery_setup_check,
            {'setup_treatment':setup.get('treatment'),'delivery_mode':setup.get('delivery_mode'),
             'manifest_delivery_mode':delivery_mode},
            'Compact setup delivery mode differs from the frozen fixture',
        )

        setup_by_id={worker['worker_id']:worker for worker in setup_workers}
        if delivery_mode=='commits':
            commit_setup_checks={}
            for worker_id in expected_ids:
                worker=setup_by_id[worker_id]
                snapshot=worker.get('snapshot')
                worker_baseline=worker.get('worker_baseline')
                binding_path=Path(worker.get('compact_binding_path',''))
                binding=json.loads(binding_path.read_text(encoding='utf-8'))
                commit_setup_checks[worker_id]=(isinstance(snapshot,dict)
                    and snapshot.get('mode')=='private-commit'
                    and snapshot.get('commit')==worker.get('commit_base')
                    and snapshot.get('source_dirty') is True
                    and isinstance(snapshot.get('created'),bool)
                    and isinstance(snapshot.get('tree'),str)
                    and isinstance(worker_baseline,dict)
                    and worker_baseline.get('head')==worker.get('commit_base')
                    and worker_baseline.get('status')=={}
                    and binding.get('workspace',{}).get('snapshot')==snapshot
                    and binding.get('workspace',{}).get('commit_base')==worker.get('commit_base'))
            require_check(
                'commit_private_snapshots_bound',all(commit_setup_checks.values()),
                {'workers':commit_setup_checks},
                'Commit workers do not share the validated dirty-source private snapshot contract',
                code='COMMIT_BASELINE_INVALID',
            )
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

            inspect_argv=[sys.executable,'-B',str(helper),'inspect','--receipt',setup_worker['receipt'],
                          '--phase','returned','--delivery-mode',delivery_mode,'--artifact',OWNER_MARKER]
            returned_delivery={}
            if delivery_mode=='commits':
                returned_result=return_by_id[worker_id]['result']
                returned_inspection=returned_result['workspace_evidence']['inspection']
                returned_delivery=returned_inspection['delivery']
                commit_base=setup_worker['commit_base']
                inspect_argv += ['--commit-base',commit_base]
                for commit_sha in returned_delivery['commits']:
                    inspect_argv += ['--commit',commit_sha]
            inspect_stdout=run_action(f'inspect-returned-{worker_id}',inspect_argv,cwd=source)
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
                and delivery.get('mode')==delivery_mode
                and isinstance(evidence_record,dict)
                and delivery.get('contribution_patch',evidence_record.get('contribution_patch'))
                    ==evidence_record.get('contribution_patch')
            )
            if delivery_mode=='commits':
                inspect_binding=(inspect_binding
                    and delivery.get('base')==setup_worker['commit_base']
                    and delivery.get('commits')==returned_delivery.get('commits')
                    and delivery.get('commit_paths')==[task_path]
                    and delivery.get('per_commit_paths')==returned_delivery.get('per_commit_paths')
                    and delivery.get('residual_paths')==[]
                    and (isinstance(delivery.get('contribution_patch'),str)
                         if setup_worker.get('snapshot',{}).get('source_dirty') else True))
            else:
                inspect_binding=(inspect_binding
                    and delivery.get('contribution_paths')==[task_path])
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
            state_kwargs={'expected_worker_branch':setup_worker.get('branch')}
            if delivery_mode=='commits':
                commit_context=fixture._load_commit_delivery_context(
                    run,manifest,worker_id,worktree)
                state_kwargs.update(fixture._commit_state_kwargs(commit_context))
            child_checks,child_details=fixture.state_checks(child_state,manifest,worker_id,'finish',**state_kwargs)
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
            source_patch_value=(delivery.get('contribution_patch') if isinstance(delivery,dict) else None)
            if not source_patch_value and isinstance(evidence,dict):
                source_patch_value=evidence.get('contribution_patch')
            if delivery_mode=='commits' and not source_patch_value:
                raise fixture.FixtureError(f'Worker {worker_id} dirty-source commit inspection omitted its contribution patch')
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
            if delivery_mode=='commits':
                commit_record={'worker_id':worker_id,'commit_base':setup_worker['commit_base'],
                               'commits':delivery['commits'],'patch_sha256':patch_digest}
                contribution['commit_record']=commit_record
                result['commit_records'].append(commit_record)
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
    elif command=='write-parent-result':
        result_path=operator_dir/'parent-result.json'
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
        default_code = ('SETUP_OPERATION_FAILED' if command=='prepare-batch' else
                        'PARENT_RESULT_INVALID' if command=='write-parent-result' else
                        'INTEGRATION_FAILED')
        code=match.group(1) if match else default_code
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
            'Setup and delivery finalization must remain bound to the frozen task, worker receipts, '
            'and caller state; proceeding after a failed check can invalidate attribution or obscure partial work.'
        ),
        rationale_ref='CONTRACT.md#retry-safety',
        evidence=evidence,
        recovery=(
            'Inspect the cited result and call log. Preserve receipts, worker evidence, any immutable contribution '
            'copies, and applied files; reconcile the cause before using a fresh run.'
        ),
        retry_safety=retry_safety,
    )


def integration_summary(run, result):
    """Compact LLM response; complete expectations, calls and checks stay in the result file."""
    if result.get('status')!='INTEGRATED' or result.get('fixture_verification',{}).get('passed') is not True:
        raise fixture.FixtureError('Cannot summarize an unaccepted integration as successful')
    summary={'status':result['status'],'applied_worker_ids':result['applied_worker_ids'],
            'elapsed_s':result['elapsed_s'],'result_path':str(Path(run).resolve()/'operator/integration-result.json'),
            'verification_path':str(Path(run).resolve()/'operator/verification.json'),
            'patches':[{k:p[k] for k in ('worker_id','path','patch_path','patch_sha256')} for p in result['patches']],
            'native_lifecycle_note':result['native_lifecycle_note']}
    integration_path=Path(run).resolve()/'operator/integration-result.json'
    if integration_path.is_file() and not integration_path.is_symlink():
        summary['result_sha256']=fixture.sha256_file(integration_path)
    if result.get('delivery_mode')=='commits':
        expected=result.get('integration_worker_ids')
        records=result.get('commit_records')
        record_shape={'worker_id','commit_base','commits','patch_sha256'}
        valid_records=(isinstance(records,list) and isinstance(expected,list)
                       and len(records)==len(expected)
                       and all(isinstance(row,dict) and set(row)==record_shape
                               and isinstance(row.get('commit_base'),str)
                               and re.fullmatch(r'[0-9a-f]{40,64}',row['commit_base']) is not None
                               and isinstance(row.get('commits'),list) and row['commits']
                               and all(isinstance(sha,str) and re.fullmatch(r'[0-9a-f]{40,64}',sha)
                                       for sha in row['commits'])
                               and row['commit_base'] not in row['commits']
                               and isinstance(row.get('patch_sha256'),str)
                               and re.fullmatch(r'[0-9a-f]{64}',row['patch_sha256']) is not None
                               for row in records)
                       and [row['worker_id'] for row in records]==expected)
        if (not isinstance(expected,list) or result.get('applied_worker_ids')!=expected
                or result.get('integration_strategy')!='preserve-parent patch from commits'
                or result.get('delivery_mode')!='commits' or not valid_records):
            raise fixture.FixtureError('Cannot summarize commit integration with incomplete worker commit records')
        summary.update({'delivery_mode':'commits','integration_strategy':result.get('integration_strategy'),
                        'worker_ids':expected,'commit_records':records})
    elif result.get('delivery_mode')=='patch':
        summary['delivery_mode']='patch'
    return summary


def _parent_result_error(message, expected=None, observed=None):
    error=fixture.FixtureError(f'[PARENT_RESULT_INVALID] {message}')
    error.diagnostic_code='PARENT_RESULT_INVALID'
    error.diagnostic_phase='parent-result'
    error.diagnostic_expected=expected or {'parent_result_gate':True}
    error.diagnostic_observed=observed or {'message':message}
    raise error


def _in_run_regular_file(run, relative_path):
    path=run/relative_path
    if path.is_symlink() or not path.is_file():
        _parent_result_error(f'required evidence is missing or symlinked: {path}',
                             {'regular_file':str(path)},
                             {'exists':path.exists(),'symlink':path.is_symlink()})
    resolved=path.resolve(strict=True)
    if resolved!=path.absolute() or run not in resolved.parents:
        _parent_result_error(f'evidence resolves outside this run: {path}',
                             {'in_run_path':str(path.absolute())},{'resolved_path':str(resolved)})
    return path


def write_parent_result(run, worker_handles, verification_sha256, integration_sha256):
    """Write a small parent assertion index after every fixture gate has passed."""
    run=Path(run).expanduser().resolve(strict=True)
    manifest=fixture.load_manifest(run)
    operator=run/'operator'
    manifest_ids=[task.get('worker_id') for task in manifest.get('task_assignments',[])
                  if isinstance(task,dict)]
    expected_ids=[str(i) for i in range(1,manifest.get('workers',0)+1)]
    if (manifest_ids!=expected_ids or manifest.get('worker_ids')!=expected_ids
            or type(manifest.get('workers')) is not int or manifest.get('workers') not in (3,5)):
        _parent_result_error('manifest does not define the exact ordered worker IDs',
                             {'worker_ids':expected_ids},{'worker_ids':manifest_ids})
    if (not isinstance(worker_handles,list)
            or any(not isinstance(item,str) or '=' not in item for item in worker_handles)):
        _parent_result_error('repeatable worker handles must use ID=HANDLE values',
                             {'worker_handle_pairs':expected_ids},{'worker_handles':worker_handles})
    pairs=[]
    for item in worker_handles:
        worker_id,handle=item.split('=',1)
        if (not worker_id or not handle or worker_id.strip()!=worker_id or handle.strip()!=handle
                or any(char.isspace() for char in handle)):
            _parent_result_error('worker handle pair has an empty or malformed ID/handle',
                                 {'id_and_handle':'nonempty, no surrounding whitespace'}, {'value':item})
        pairs.append((worker_id,handle))
    supplied_ids=[worker_id for worker_id,_ in pairs]
    handles=[handle for _,handle in pairs]
    if (len(supplied_ids)!=len(expected_ids) or set(supplied_ids)!=set(expected_ids)
            or len(set(supplied_ids))!=len(supplied_ids) or len(set(handles))!=len(handles)):
        _parent_result_error('worker IDs and native handles must each occur exactly once',
                             {'worker_ids':expected_ids,'unique_handles':True},
                             {'worker_ids':supplied_ids,'handles':handles})
    handles_by_id={worker_id:handle for worker_id,handle in pairs}
    pairs=[(worker_id,handles_by_id[worker_id]) for worker_id in expected_ids]
    if any(not isinstance(value,str) or re.fullmatch(r'[0-9a-f]{64}',value) is None
           for value in (verification_sha256,integration_sha256)):
        _parent_result_error('verification and integration hashes must be lowercase SHA-256 values',
                             {'sha256_fields':2},
                             {'verification_sha256':verification_sha256,'integration_sha256':integration_sha256})

    setup_path=_in_run_regular_file(run,Path('operator/setup-result.json'))
    treatment_path=_in_run_regular_file(run,Path('operator/treatment.json'))
    setup=json.loads(setup_path.read_text(encoding='utf-8'))
    treatment=json.loads(treatment_path.read_text(encoding='utf-8'))
    if (setup.get('status')!='PREPARED' or setup.get('phase')!='prepared'
            or setup.get('treatment')!='compact' or setup.get('compact_startup_contract')!='action-packet/v1'
            or treatment.get('treatment')!='compact' or treatment.get('version')!=4
            or treatment.get('verification_output')!='summary-v1'):
        _parent_result_error('setup and treatment do not declare a prepared compact v4 action-packet run',
                             {'setup':'PREPARED compact action-packet/v1','treatment':'compact v4 summary-v1'},
                             {'setup_status':setup.get('status'),'treatment':treatment})
    setup_workers=setup.get('workers')
    setup_ids=[item.get('worker_id') for item in setup_workers] if isinstance(setup_workers,list) else []
    if setup_ids!=expected_ids:
        _parent_result_error('setup worker records do not match manifest order',
                             {'worker_ids':expected_ids},{'worker_ids':setup_ids})

    verification_path=_in_run_regular_file(run,Path('operator/verification.json'))
    verification_bytes=verification_path.read_bytes()
    observed_verification_sha=hashlib.sha256(verification_bytes).hexdigest()
    if observed_verification_sha!=verification_sha256:
        _parent_result_error('parent verification summary hash differs from saved full verification report',
                             {'report_sha256':verification_sha256},
                             {'report_sha256':observed_verification_sha})
    try:
        verification=json.loads(verification_bytes.decode('utf-8'))
    except (UnicodeDecodeError,ValueError) as exc:
        _parent_result_error(f'full parent verification is not valid JSON: {exc}')
    verification_checks=verification.get('checks')
    if (verification.get('run_id')!=manifest.get('run_id') or verification.get('passed') is not True
            or verification.get('errors')!=[] or not isinstance(verification_checks,dict)
            or not verification_checks or any(value is not True for value in verification_checks.values())):
        _parent_result_error('full parent verification report is not a successful exact run',
                             {'run_id':manifest.get('run_id'),'passed':True,'errors':[],'all_checks_true':True},
                             {'run_id':verification.get('run_id'),'passed':verification.get('passed'),
                              'errors':verification.get('errors'),'checks':verification_checks})
    archive_path=operator/'parent-verification.json'
    if archive_path.exists() or archive_path.is_symlink():
        _parent_result_error('post-exit archive already exists before controller verification',
                             {'archive_absent_before_parent_exit':True},
                             {'path':str(archive_path),'exists':archive_path.exists(),'symlink':archive_path.is_symlink()})

    integration_path=_in_run_regular_file(run,Path('operator/integration-result.json'))
    integration_bytes=integration_path.read_bytes()
    observed_integration_sha=hashlib.sha256(integration_bytes).hexdigest()
    if observed_integration_sha!=integration_sha256:
        _parent_result_error('integration summary hash differs from saved integration result',
                             {'result_sha256':integration_sha256},
                             {'result_sha256':observed_integration_sha})
    integration=json.loads(integration_bytes.decode('utf-8'))
    delivery_mode=manifest.get('delivery_mode','patch')
    integration_ok=(integration.get('run_id')==manifest.get('run_id')
                    and integration.get('delivery_mode')==delivery_mode
                    and (integration.get('status')=='NO_INTEGRATION' and delivery_mode=='ephemeral'
                         or integration.get('status')=='INTEGRATED'
                         and integration.get('fixture_verification',{}).get('passed') is True
                         and integration.get('applied_worker_ids')==expected_ids))
    if not integration_ok:
        _parent_result_error('integration record is not a successful matching run/mode',
                             {'delivery_mode':delivery_mode,'successful_finalization':True},
                             {'status':integration.get('status'),'delivery_mode':integration.get('delivery_mode'),
                              'run_id':integration.get('run_id')})

    worker_rows=[]
    for worker_id,handle in pairs:
        worker=next(item for item in setup_workers if item.get('worker_id')==worker_id)
        binding_path=_in_run_regular_file(run,Path('operator/compact-bindings')/f'worker-{worker_id}.json')
        binding_bytes=binding_path.read_bytes()
        binding_sha=hashlib.sha256(binding_bytes).hexdigest()
        binding=json.loads(binding_bytes.decode('utf-8'))
        canonical=hashlib.sha256(json.dumps({key:value for key,value in binding.items() if key!='binding_sha256'},
            sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('utf-8')).hexdigest()
        if (binding_sha!=worker.get('compact_packet_sha256')
                or binding.get('binding_sha256')!=canonical
                or worker.get('compact_binding_sha256')!=canonical):
            _parent_result_error(f'worker {worker_id} compact packet/binding digest does not match setup',
                                 {'packet_sha256':worker.get('compact_packet_sha256'),
                                  'binding_sha256':worker.get('compact_binding_sha256')},
                                 {'packet_sha256':binding_sha,'binding_sha256':canonical})
        phases={}
        for phase in ('start','finish'):
            phase_path=_in_run_regular_file(run,Path('operator/worker-phases')/f'worker-{worker_id}-{phase}'/'attempt.json')
            phase_record=json.loads(phase_path.read_text(encoding='utf-8'))
            checks=phase_record.get('checks')
            if (phase_record.get('status')!='PASSED' or phase_record.get('run_id')!=manifest.get('run_id')
                    or phase_record.get('worker_id')!=worker_id or phase_record.get('phase')!=phase
                    or phase_record.get('root')!=worker.get('worktree')
                    or phase_record.get('compact_binding_sha256')!=canonical
                    or not isinstance(checks,dict) or checks.get('phase_passed') is not True
                    or any(value is not True for key,value in checks.items() if key!='phase_passed')):
                _parent_result_error(f'worker {worker_id} {phase} phase is not a successful bound run record',
                                     {'run_id':manifest.get('run_id'),'worker_id':worker_id,'phase_passed':True},
                                     {'run_id':phase_record.get('run_id'),'worker_id':phase_record.get('worker_id'),
                                      'status':phase_record.get('status'),'binding_sha256':phase_record.get('compact_binding_sha256'),
                                      'checks':checks})
            phases[phase]={'path':str(phase_path.resolve()),'sha256':fixture.sha256_file(phase_path)}
        worker_rows.append({'worker_id':worker_id,'status':'PARENT_ASSERTED','native_handle':handle,
                            'native_lifecycle':'parent_asserted','binding_sha256':canonical,
                            'packet_sha256':binding_sha,
                            'records':{'start':phases['start'],'finish':phases['finish'],
                                       'verify_return':None}})
    return_records=_require_compact_returns(run,setup,expected_ids)
    record_by_id={row['worker_id']:row for row in return_records}
    for row in worker_rows:
        worker_id=row['worker_id']
        return_row=record_by_id.get(worker_id)
        if not isinstance(return_row,dict) or return_row.get('valid') is not True:
            _parent_result_error(f'worker {worker_id} has no successful bound compact return record')
        return_path=_in_run_regular_file(run,Path('operator/compact-returns')/f'worker-{worker_id}.json')
        row['records']['verify_return']={'path':str(return_path.resolve()),
                                         'sha256':fixture.sha256_file(return_path)}
    index_path=operator/'parent-result.json'
    if index_path.exists() or index_path.is_symlink():
        _parent_result_error('parent result index already exists; refusing overwrite',
                             {'exclusive_create':True}, {'path':str(index_path)})
    index={'schema':'ask-agent.parent-result-index/v1','run_id':manifest['run_id'],
           'status':'PARENT_ASSERTED','native_lifecycle':'parent_asserted',
           'verification':{'source_path':str(verification_path.resolve()),
                            'source_sha256':verification_sha256,
                            'archive_path':str(archive_path.absolute()),
                            'archive_sha256':verification_sha256},
           'integration':{'path':str(integration_path.resolve()),'sha256':integration_sha256},
           'workers':worker_rows}
    fixture.write_exclusive_json(index_path,index)
    return {'status':index['status'],'run_id':index['run_id'],'result_path':str(index_path.resolve()),
            'result_sha256':fixture.sha256_file(index_path),'worker_ids':expected_ids}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare-batch','verify-return','integrate-batch','finish-ephemeral','write-parent-result']);p.add_argument('--run',required=True)
    p.add_argument('--compact',action='store_true',help='prepare worker worktrees through ask_agent_task.py')
    p.add_argument('--worker',help='worker ID for compact verify-return')
    p.add_argument('--delivery-mode',choices=['patch','commits'],
                   help='delivery mode for integrate-batch; must match the fixture')
    p.add_argument('--collected-worker',action='append',required=False,
                   help='explicit parent assertion of a collected worker id (repeat for every worker)')
    p.add_argument('--worker-handle',action='append',required=False,
                   help='parent assertion ID=HANDLE (repeat once for every worker)')
    p.add_argument('--verification-sha256',help='report_sha256 from fixture verify --summary output')
    p.add_argument('--integration-sha256',help='result_sha256 from integration/finalizer summary output')
    a=p.parse_args()
    try:
        if a.command=='prepare-batch':
            result=prepare_batch(a.run,compact=a.compact)
            if a.compact:
                print(json.dumps(compact_prepare_summary(a.run,result),sort_keys=True,separators=(',',':')))
            else:
                print(json.dumps(result,indent=2))
        elif a.command=='verify-return':
            if not a.worker:
                p.error('verify-return requires --worker')
            result=verify_compact_return(a.run,a.worker)
            print(json.dumps(result,indent=2))
        elif a.command=='integrate-batch':
            if a.compact:
                p.error('--compact applies only to prepare-batch')
            result=integrate_batch(a.run,a.collected_worker or [],delivery_mode=a.delivery_mode)
            print(json.dumps(integration_summary(a.run,result),indent=2))
        elif a.command=='write-parent-result':
            if (a.compact or a.delivery_mode is not None or a.worker is not None
                    or a.collected_worker is not None):
                p.error('write-parent-result accepts only worker handles and the two expected hashes')
            if not a.worker_handle or not a.verification_sha256 or not a.integration_sha256:
                p.error('write-parent-result requires repeated --worker-handle, --verification-sha256, and --integration-sha256')
            result=write_parent_result(a.run,a.worker_handle,a.verification_sha256,a.integration_sha256)
            print(json.dumps(result,indent=2))
        else:
            if a.compact or a.delivery_mode is not None:
                p.error('finish-ephemeral does not accept --compact or --delivery-mode')
            result=finish_ephemeral(a.run,a.collected_worker or [])
            print(json.dumps(result,indent=2))
    except Exception as exc:
        diagnostic=_cli_failure_diagnostic(a.run,a.command,exc,a.worker)
        operator_dir=Path(a.run).expanduser().resolve()/'operator'
        jsonl_path=operator_dir/'diagnostics.jsonl' if operator_dir.is_dir() else None
        diagnostics.exit_with_diagnostic(diagnostic,jsonl_path=jsonl_path)
