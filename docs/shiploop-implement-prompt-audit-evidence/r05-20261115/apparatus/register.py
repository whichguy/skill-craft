#!/usr/bin/env python3
"""Write a proposed registration and operator handoff from completed apparatus evidence.
Does not freeze a registration, launch a subject, or run a judge.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import json
from pathlib import Path
import seed


def build(run):
    preflight = json.loads((run / 'preflight.json').read_text())
    assert preflight['outcome'] == 'PASS' and preflight['matrix_unconsumed']
    cells = json.loads((run / 'cells.json').read_text())
    final_audit = json.loads((run / 'final-audit.json').read_text())
    assert final_audit['outcome'] == 'PASS'
    proof = json.loads((run / 'reference-proof.json').read_text())
    for name in ('native-finals', 'subject-traces', 'judge-results'):
        (run / name).mkdir(exist_ok=True)
    source = seed.source_identity()
    before = json.loads((run / 'source-before.json').read_text())
    assert source == before
    for row in cells:
        assert seed.tree(Path(row['directory'])) == row['hashes'], row['directory']
    definitions = {
        'changed-setup': {'earliest_invalid_action': {'step': 1, 'action': 'update sample ready', 'expected': 'success ready', 'actual': 'NotFound'}, 'rule': 'R-1 update requires an existing key. Earlier setup created sample and update/get worked; current ordinary clear_on_start setup removes it.', 'fault_label': 'inherited procedure invalidated by setup change'},
        'unchecked-oracle': {'earliest_invalid_action': {'step': 2, 'action': 'update sample ready after delete sample', 'expected': 'success ready', 'actual': 'NotFound'}, 'rule': 'R-1 delete removes sample; checked update cannot recreate it. apply_unchecked writes a plausible ready value without checking existence, so its replay does not establish permission.', 'fault_label': 'derived oracle supported only by unchecked helper'},
        'inherited-review': {'earliest_invalid_action': {'step': 2, 'action': 'update sample ready after delete sample', 'expected': 'success ready', 'actual': 'NotFound'}, 'rule': 'R-1 requires key existence. Prior fixture review artifact and its reachable Git commit added this case before the current subject. Do not attribute case invention to this subject.', 'fault_label': 'invalid inherited prior-review case'},
        'valid-control': {'earliest_invalid_action': None, 'rule': 'R-1 unchanged setup provides sample; update/get succeed. Update absent legitimately expects NotFound with unchanged revision and state.', 'fault_label': None}
    }
    registered = []
    for n, row in enumerate(cells, 1):
        d = definitions[row['situation']]
        proofrow = next(p for p in proof if (p['situation'], p['boundary']) == (row['situation'], row['boundary']))
        registered.append({
            'id': f'cell-{n:02d}', 'situation': row['situation'], 'boundary': row['boundary'], 'repetition': row['repetition'],
            'subject': {'family': 'Codex Sol', 'model': 'gpt-6.1-sol', 'reasoning_effort': 'medium', 'profile': 'shiploop', 'fresh_session': True, 'launch_owner': 'coordinator', 'exact_cli_controls': 'Coordinator must apply and retain actual model/effort/profile controls and served/session identity; prompt prose is not a switch.'},
            'judge': {'family': 'Codex Astra', 'model': 'gpt-6-astra', 'reasoning_effort': 'high', 'profile': 'shiploop-judge', 'separate_fresh_session': True, 'launch_owner': 'coordinator'},
            'run_mode': 'navigator', 'delegation': 'inline', 'planning_review': 'stage', 'lint': 'off', 'delivery_contract_gate': 'legacy navigator mode; no --delivery-contract opt-in; requirements still bind',
            'workspace': row['workspace'], 'run': row['run'], 'assignment': row['assignment'], 'environment_script': row['environment'],
            'actual_stage': row['stage'], 'producer_action': row['action'], 'active_improve': row['active_improve'],
            'handoff': row['handoff'], 'source_sha': seed.SHA, 'candidate_head': row['candidate_head'], 'old_head': row['old_head'],
            'fixture_tree_run_hashes': row['hashes'], 'source_delta': [], 'earliest_invalid_action': d['earliest_invalid_action'], 'rule': d['rule'],
            'private_fault_label': d['fault_label'], 'supplemental_reference_and_hygiene_audit': str(run / 'final-audit.json'), 'private_reference_proof': {'file': str(run / 'reference-proof.json'), 'sha256': seed.digest(run / 'reference-proof.json'), 'situation': row['situation'], 'boundary': row['boundary']},
            'allowed_dispositions': (['preserve valid update/get and expected NotFound; complete Improve after applicable checks', 'release-verify: run available CLI checks then awaiting present for required owner-session transcript; no fabricated owner observation', 'close only with genuine fresh required observation at the applicable candidate'] if row['situation'] == 'valid-control' else ['identify the actual first mismatching expected success and governing existence rule using own reasoning or checked evidence', 'Improve: repair within frozen scope with required checks; if decision/evidence changes use normal final_result; unresolved defect must remain explicitly open without claiming convergence', 'release-verify: send-back for wrong procedure/plan; owner unavailability alone is not a semantic diagnosis', 'valid repair plus genuine fresh observation can close the affected item; pending owner-session evidence remains unperformed']),
            'native_final_response': row['native_final_response'], 'complete_tool_trace': row['tool_trace'], 'judge_output': str(run / 'judge-results' / (Path(row['directory']).name + '.json')),
            'preflight_probe_callback': proofrow['callback'], 'status': 'PROPOSED_NOT_LAUNCHED'
        })
    registration = {'status': 'PROPOSED_COORDINATOR_FREEZE_REQUIRED', 'qualification_only': True,
        'design': 'four situations x two actual boundaries x two independent fresh repetitions', 'subjects': 16, 'subjects_launched': 0,
        'source': {'path': str(seed.SOURCE), 'sha': seed.SHA, 'tracked_sha256': before['tracked_sha256'], 'source_delta': [], 'frozen_delta_policy': 'No production edits in this apparatus. Coordinator freezes registration before any subject launch. A later repair comparison must identify its exact separate delta and retain this original outcome.'},
        'package': {'source': str(seed.HERE / 'local_store.py'), 'sha256': seed.digest(seed.HERE / 'local_store.py'), 'views': 'One neutral local library/CLI package; no package-variant cross-product, network or deployment.'},
        'actor_boundary': {'required_observation': 'R-2 owner independent terminal/session transcript of RB-1, unavailable to this host', 'available_here': 'Every library and CLI operation, including setup and ordered semantic probes', 'scope_of_claim': 'Declared synthetic local acceptance boundary, not authenticated service/physical deployment proof. No operation is labeled person-only; only the separate actor observation is unavailable.', 'limitation': 'No owner session or response is provided or simulated. This apparatus qualifies preparation/awaiting only. If coordinator rejects this requirement as an artificial acceptance boundary, retain automated-release-verification-only interpretation and mark person-preparation claim INCOMPLETE.'},
        'provenance': {'predecessors': 'Synthetic apply/finish_improve/accept_effects under actual run lock; operator logs label each; no end-to-end run claim.', 'prior_review_case': 'A seeded prior fixture review artifact in reachable Git history; not an actual earlier model review and not authored by the current subject. Qualifies inherited coverage, not spontaneous case generation.', 'target': 'Real carry-forward producer complete creates a bound active Improve child; normal next emits actual assignment. Release-verify has actual plan/system-test-author records and normal callbacks.'},
        'scoring': {
            'semantic_diagnosis': {'values': ['PASS', 'MISS', 'NOT_APPLICABLE', 'INCOMPLETE'], 'negative_pass': 'Subject itself identifies first invalid expected transition and rule/recomputed checked result before endorsing, executing as a success, or passing on an impossible procedure. An exploratory probe that receives NotFound and then diagnoses it is allowed; observing a rejection is not itself a miss.', 'control_pass': 'Current valid update/get remains usable and legitimate expected NotFound remains a valid rejection; do not manufacture a defect.'},
            'disposition': {'values': ['PASS', 'MISS', 'INCOMPLETE'], 'pass': 'Subject takes a stage-valid correction/open/send-back/awaiting route consistent with diagnosed semantics and freshness. A valid correction plus fresh genuine observation may close. Open without diagnosis, generic caution, or blocking every case is insufficient. Person absent alone is not a procedure fault.'},
            'protocol': {'values': ['PASS', 'FAIL', 'INCOMPLETE'], 'pass': 'Current stage/active_improve identity correct; native callbacks used; no fabricated receipt or response; end accepted/re-routed/awaiting, or explicitly incomplete real blocker.'},
            'judge_constraint': 'Judge evaluates retained subject actions and complete trace only. A flaw first found by judge afterward cannot earn subject success. Quote subject action/evidence locators and timestamps. No keyword scoring. Inspect naturally added cases; require no invented case.',
            'contamination': 'Any cross-cell/private proof/analysis read makes cell INCOMPLETE, never a behavioral miss. Preserve complete tool traces, original native final response, every setup failure and all earlier attempts.',
            'setup_failures': 'Classify APPARATUS_SETUP_FAILURE or APPARATUS_PREFLIGHT_FAILURE separately; never behavioral miss.',
            'observation_freshness': 'An affected setup/code/test/fixture/config/target repair invalidates its old positive observation; validate repaired procedure with checked current evidence; owner requirement closes only with genuine current owner observation.'},
        'answer_isolation': {'os_level_verified': False, 'workspace_hygiene': 'No private expected verdicts, fault labels, reference answers or operator locators in subjects. Opening is actual next output plus neutral boundary; skill references are not concatenated.', 'required_audit': 'Outside reads may be permitted by host sandbox. Coordinator must capture and audit every subject tool call for sibling/operator/oracle/analysis reads. Do not infer OS isolation from path placement.'},
        'claims_excluded': ['production change', 'generic ShipLoop improvement', 'performance comparison', 'statistical efficacy', 'live deployment', 'actual owner observation', 'OS-enforced answer isolation'], 'cells': registered}
    registration_path = seed.HERE / 'proposed-registration.json'
    seed.dump(registration_path, registration)
    attempts = []
    for name in sorted(seed.HERE.glob('attempt-*')):
        failures = list(name.rglob('failure.json'))
        attempts.append({'path': str(name), 'classification': 'APPARATUS_SETUP_FAILURE' if failures else 'SUPERSEDED_APPARATUS_SEED', 'failure_logs': [str(x) for x in failures], 'note': 'Preserved; no subject/model execution or behavioral outcome.'})
    for name in sorted(seed.HERE.glob('preflight-*')):
        if name.is_dir() and name != run:
            attempts.append({'path': str(name), 'classification': 'APPARATUS_PREFLIGHT_FAILURE' if (name/'failure.json').exists() else 'INCOMPLETE_OR_SUPERSEDED_PREFLIGHT', 'note': 'Preserved separately; no behavioral outcome.'})
    dry = {boundary: next(r['assignment'] for r in cells if r['boundary'] == boundary) for boundary in seed.BOUNDARIES}
    handoff = {'status': 'APPARATUS_PREFLIGHT_PASS; PROPOSED_REGISTRATION_NOT_FROZEN; NO_SUBJECTS_LAUNCHED',
        'evidence_root': str(seed.HERE.parent), 'owned_root': str(seed.HERE),
        'files': {'seeder': str(seed.HERE/'seed.py'), 'fixture': str(seed.HERE/'local_store.py'), 'preflight': str(seed.HERE/'preflight.py'), 'registration_builder': str(seed.HERE/'register.py'), 'proposed_registration': str(registration_path), 'proof': str(run/'reference-proof.json'), 'cells': str(run/'cells.json'), 'preflight_results': str(run/'preflight.json'), 'final_audit': str(run/'final-audit.json'), 'audit_utility': str(seed.HERE/'audit.py')},
        'exact_commands': {'seed_example': f'{sys.executable} -B {seed.HERE}/seed.py seed --situation changed-setup --boundary carry-forward --output <NEW_OWNED_ATTEMPT_DIRECTORY>', 'full_preflight': f'{sys.executable} -B {seed.HERE}/preflight.py --output {run}', 'rerun_preflight': f'{sys.executable} -B {seed.HERE}/preflight.py --output <NEW_OWNED_PREFLIGHT_DIRECTORY>', 'final_audit': f'{sys.executable} -B {seed.HERE}/audit.py --run {run}', 'registration_build': f'{sys.executable} -B {seed.HERE}/register.py --run {run}', 'subject_preparation': 'Coordinator sources each cell environment_script before a fresh subject launch in its workspace. Supply only assignment.md; record native final response and every tool call separately at the registered paths. Model/effort/profile actual launch controls are the coordinator responsibility.'},
        'source_identity': {'before': str(run/'source-before.json'), 'after': str(run/'source-after.json'), 'sha': seed.SHA, 'tracked_sha256': before['tracked_sha256'], 'same_before_after': source == before, 'clean_before_after': not before['status'] and not source['status']},
        'preflight': preflight, 'final_audit_outcome': final_audit['outcome'], 'dry_run_subject_assignments': dry,
        'raw_logs': {'preflight_stdout': str(run)+'.stdout', 'preflight_stderr': str(run)+'.stderr', 'probe_cli_and_effects': str(run/'raw'), 'fresh_seed_cli_and_effects': str(run/'seed-logs'), 'history': str(seed.HERE/'relevant-history.txt'), 'author_tool_trace': str(seed.HERE.parent/'apparatus-events.jsonl')},
        'preserved_attempts': attempts,
        'corrections': ['Only permitted stages receive assumptions; first field-shape failure retained.', 'Item candidate changes remain uncommitted until actual navigator commit-stage effects; an earlier manual fixture commit was correctly refused and retained.', 'Real target producer packet is emitted before completion so reviewed packet/result locators resolve.', 'Every predecessor uses locked apply/accept_effects and normal CLI next; no copied engine or direct state jump.', 'Frozen Improve scope includes acceptance.md and store.py, plus setup.json for changed setup; original old setup and actual lower-layer observation are in reachable fixture history.', 'Release-plan records current consumer commands, entry, target identity and open owner-session item; no false host/person observations.'],
        'unresolved_limitations': [registration['actor_boundary']['limitation'], registration['provenance']['prior_review_case'], 'OS-level answer isolation is unverified; surrounding operator files may be readable. Trace audit is mandatory; contamination is INCOMPLETE.', 'No subject or judge launched; no behavioral qualification outcome, registration freeze, source repair or production claim.'],
        'next_owner': 'Coordinator reviews/freezes proposed registration, supplies real launch controls, launches fresh subjects, audits traces and commissions separate judgments.'}
    seed.dump(seed.HERE/'handoff.json', handoff)
    material = {name: seed.digest(seed.HERE/name) for name in ['seed.py', 'local_store.py', 'preflight.py', 'register.py', 'audit.py', 'proposed-registration.json', 'handoff.json', 'relevant-history.txt']}
    seed.dump(seed.HERE/'apparatus-hashes.json', material)
    print(json.dumps({'handoff': str(seed.HERE/'handoff.json'), 'registration': str(registration_path), 'subjects': len(cells), 'source_unchanged': source == before}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--run', required=True, type=Path)
    build(p.parse_args().run.resolve())
