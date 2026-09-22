#!/usr/bin/env python3
"""Reconciled planning sources at the consumer boundary.

Producer/Improve setup receipts are synthetic. Reconciliation uses the real
bundled ephemeral runtime and importer; this is not a model-behavior test.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/shiploop/scripts'
sys.path.insert(0, str(SCRIPTS))
import shiploop_navigator as nav
import shiploop_standalone_improve as bridge
import shiploop_planning_context as context
import shiploop_planning_revision as revision
import shiploop_consumer_delivery as delivery
import shiploop_chain as chain
import shiploop_navigator_dry_run as dry_run


def load_fixture(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


context_fixture = load_fixture('v4_context_fixture', 'test/shiploop-planning-context.test.py')
delivery_fixture = load_fixture('v4_delivery_fixture', 'test/shiploop-consumer-delivery.test.py')


class V4ConsumersTests(unittest.TestCase):
    def setUp(self):
        self.f = context_fixture.PlanningContextTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.state = nav.new_state(str(self.f.repo.resolve()), 'Reconcile planning sources', protocol_version=4)

    def to_plan(self, references=None):
        while nav.current_stage(self.f.state) != 'plan':
            stage = nav.current_stage(self.f.state)
            self.f.advance(evidence_refs=(references or {}).get(stage))

    def reconcile(self, target):
        self.assertEqual(nav.current_stage(self.f.state), 'plan')
        action = nav.current_action(self.f.state)['id']
        waiting = nav.apply(self.f.state, action, {'outcome': 'done', 'summary': 'Provisional plan'})
        skill = bridge.resolve_skill(str(ROOT / 'skills/improve/SKILL.md'))
        binding = bridge.binding(waiting, action, 'plan', waiting['active_improve']['seed_result'], skill)
        waiting['active_improve'] = binding
        contract = {
            'workspace': binding['workspace'], 'work': 'Review this plan and its experiment evidence.',
            'exit_condition': 'Coherent reviewed planning sources', 'repeat_condition': 'Authorized work remains',
            'required_trivial_reviews': 2,
            'context': {'request': 'Reconcile this plan.\n' + binding['contract_marker'],
                        'scope': 'Only temporary evidence and candidate plan', 'authority': 'No product edits or commits',
                        'environment': 'Local isolated test fixture', 'resources': []},
        }
        started = subprocess.run([sys.executable, '-B', skill['runtime_cli'], 'start'],
                                 input=json.dumps(contract), text=True, capture_output=True, check=True)
        packet = json.loads(started.stdout)
        stopped = subprocess.run(packet['done_argv'], input=json.dumps({
            'classification': 'unresolved', 'exit_assessment': 'unsatisfied',
            'continuation_assessment': 'cancelled', 'evidence': 'A prior premise was disproved.',
            'handoff': 'Parent must reconcile ' + target + '; no product effect or cleanup remains.',
        }), text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(stopped.stdout)['status'], 'stopped')
        packet_path = bridge.receipt_path(binding)
        packet_path.parent.mkdir(parents=True, exist_ok=True)
        packet_path.write_text(stopped.stdout)
        evidence = self.f.repo / ('experiment-' + action + '.md')
        evidence.write_text('Observed premise contradiction; synthetic observation for protocol test.\n')
        receipt = {'summary': 'An experiment invalidated the ' + target + ' premise.',
                   'target': target, 'evidence_refs': [str(evidence.resolve())]}
        record, writes = bridge.settle_incomplete(binding, receipt)
        self.f.state = nav.reconcile(waiting, action, record, receipt)
        nav.save(self.f.run, self.f.state, writes)
        return action

    def test_reconciled_manifest_requires_new_suffix_not_deleted_old_files(self):
        old_spec = self.f.write_text('old-spec.md', 'Obsolete requirement premise')
        old_tests = self.f.write_text('old-tests.md', 'Obsolete verification premise')
        self.to_plan({'spec': [str(old_spec)], 'test-strategy': [str(old_tests)]})
        old_actions = {stage: values[-1] for stage, values in self.f.actions.items()}
        reconciled = self.reconcile('spec')
        self.assertIsNone(nav._latest_done_test_strategy(self.f.state))
        current = revision.current_actions(self.f.state)
        self.assertEqual(current[(None, 'research')], old_actions['research'])
        self.assertNotIn((None, 'spec'), current)
        with self.assertRaises(chain.ChainError):
            chain._require_bindable(self.f.state, nav.current_action(self.f.state)['id'])
        old_spec.unlink()
        old_tests.unlink()
        new_spec = self.f.write_text('new-spec.md', 'Reconciled requirement')
        self.f.to_implement({'spec': [str(new_spec)]})
        self.assertEqual(nav._latest_done_test_strategy(self.f.state)['action'], self.f.actions['test-strategy'][-1])
        result = context.collect(self.f.run.resolve(), self.f.state, self.f.graph, self.f.graph_source)
        self.assertFalse(result['missing_required'], result['missing_required'])
        classes = context._entry_classifications(self.f.state, 'W1')
        self.assertEqual(classes[old_actions['spec']], 'history')
        self.assertEqual(classes[reconciled], 'history')
        self.assertEqual(classes[self.f.actions['spec'][-1]], 'current')
        self.assertTrue(any(reconciled in row['producers'] for row in result['manifest']['artifacts']))
        chain._require_bindable(self.f.state, nav.current_action(self.f.state)['id'])

    def test_missing_reconciliation_archive_blocks_context_and_chain_recovery(self):
        self.to_plan()
        action = self.reconcile('test-strategy')
        self.f.to_implement()
        (self.f.run / 'improve' / action / 'receipt.md').unlink()
        with self.assertRaisesRegex(context.PlanningContextError, 'reconciliation'):
            context.collect(self.f.run.resolve(), self.f.state, self.f.graph, self.f.graph_source)
        with self.assertRaisesRegex(chain.ChainError, 'reconciliation'):
            chain._load_state(self.f.run)

    def test_stale_delivery_contract_keeps_authority_lineage_but_cannot_unlock_plan(self):
        # Consumer projection accepts compact synthetic histories; it must use
        # the same invalidation projection without erasing correction authority.
        contract = delivery_fixture.contract()
        state = {'navigator_protocol_version': 4, 'delivery_contract_version': 1,
                 'history': [
                     {'action': 'spec-old', 'stage': 'spec', 'outcome': 'done', 'workitem': None},
                     {'action': 'plan-old', 'stage': 'plan', 'outcome': 'reconcile', 'workitem': None}],
                 'accepted': {
                     'spec-old': {'outcome': 'done', 'summary': 'Original contract',
                                  'delivery_assessment': {'kind': 'contract', 'contract': contract}},
                     'plan-old': {'outcome': 'reconcile', 'summary': 'Changed premise',
                                  'reconciliation_target': 'spec'}}}
        projected = delivery.project(state)
        self.assertEqual(projected['anchor'], 'spec-old')
        self.assertIsNotNone(projected['replan_required'])
        with self.assertRaisesRegex(delivery.ConsumerDeliveryError, 'superseded'):
            delivery.validate_transition(state, 'plan-new', 'plan', {'outcome': 'done', 'summary': 'No correction'})
        weakened = delivery_fixture.local_contract()
        with self.assertRaisesRegex(delivery.ConsumerDeliveryError, 'user-approved'):
            delivery.validate_transition(state, 'plan-new', 'plan', {
                'outcome': 'done', 'summary': 'Unauthorized weakening',
                'delivery_assessment': {'kind': 'contract', 'contract': weakened, 'supersedes': 'spec-old'}})
        corrected = delivery.validate_transition(state, 'plan-new', 'plan', {
            'outcome': 'done', 'summary': 'Fresh current contract',
            'delivery_assessment': {'kind': 'contract', 'contract': contract, 'supersedes': 'spec-old'}})
        self.assertEqual(corrected['anchor'], 'plan-new')
        self.assertIsNone(corrected['replan_required'])

    def test_v4_dry_run_preserves_full_existing_graph(self):
        for name, scenario in dry_run.scenarios(4).items():
            result = dry_run.run_scenario(name, scenario, protocol_version=4)
            self.assertTrue(result['ok'], result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
