#!/usr/bin/env python3
"""Navigator graph acceptance: actual routes and packets without project work."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/shiploop/scripts'
sys.path.insert(0, str(SCRIPTS))
import shiploop_navigator_dry_run as driver  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_prompts as guidance  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_store as store  # noqa: E402


# A Battleship-shaped pair of work items: W1 changes code and has tests; W2 only
# adds navigation metadata (a Salesforce tab and app), as the run's corrective item did.
CODE_ITEM = {"paths": ["force-app/main/default/lwc/fleetCommand/**"],
             "test_commands": [{"command": "npm test -- --verbose", "suite": "focused", "ids": ["TC-9"]},
                               {"command": "npm test", "suite": "regression"}]}
METADATA_ITEM = {"paths": ["force-app/main/default/tabs/Fleet_command.tab-meta.xml",
                           "force-app/main/default/applications/Fleet.app-meta.xml"],
                 "test_commands": [], "test_commands_na": "Navigation metadata; no unit-testable behaviour."}


def host_work_per_item(step_plans):
    """Drive the pure navigator through the INNER loop; count what the host must do per item.

    Returns {item: {"packets": producer results the host submitted, "reviews": Improve children}}.
    Stages ShipLoop records as not applicable are not host work.
    """
    state = navigator.new_state("/simulation-only/repo", "Battleship-shaped measurement.")
    counts = {}
    for _ in range(400):
        stage = navigator.current_stage(state)
        if stage == "system-test-author":
            return counts
        action = navigator.current_action(state)["id"]
        item = navigator._current_work_item(state)
        if state.get("active_improve") is not None:
            counts.setdefault(item, {"packets": 0, "reviews": 0})["reviews"] += 1
            state = navigator.finish_improve(state, action, {"summary": "Synthetic review.",
                                                              "review_refs": ["synthetic://r"],
                                                              "check_refs": ["synthetic://c"]})
            continue
        result = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}
        if stage == "plan":
            result["work_items"] = [{"id": item_id, "title": item_id} for item_id in step_plans]
        if stage == "step-plan":
            result.update(step_plans[item])
        if item:
            counts.setdefault(item, {"packets": 0, "reviews": 0})["packets"] += 1
        state = navigator.apply(state, action, result)
    raise AssertionError("did not reach the outer stages")


class BattleshipMeasurementTests(unittest.TestCase):
    """The run-feedback plan's measurement: a metadata-only item costs the host far less."""

    def test_a_metadata_only_item_skips_its_seven_test_stages_and_the_test_spec_review(self):
        counts = host_work_per_item({"W1": CODE_ITEM, "W2": METADATA_ITEM})
        # W1 walks all 18 INNER stages; its step-plan and test-spec get Improve reviews.
        self.assertEqual(counts["W1"], {"packets": 18, "reviews": 2})
        # W2 loses test-spec, baseline, test-author, test-red, test-green, test-refine and
        # regression (7 packets) and the test-spec review; the end-of-work review remains.
        self.assertEqual(counts["W2"], {"packets": 11, "reviews": 2})

    def test_without_proof_a_no_command_item_still_walks_every_stage(self):
        code_without_commands = {"paths": ["src/**"], "test_commands": [],
                                 "test_commands_na": "The model says there is nothing to test."}
        counts = host_work_per_item({"W1": code_without_commands})
        self.assertEqual(counts["W1"]["packets"], 18)

class NavigatorDryRunTests(unittest.TestCase):
    def test_access_policy_is_reachable_through_actual_graph_and_recovery(self):
        # A routing/locator contract, not proof that a host follows auth advice.
        references = ROOT / 'skills/shiploop/references'
        policy = references / 'research-loop.md'
        lifecycle = references / 'environment-lifecycle.md'
        self.assertTrue(lifecycle.is_file())
        self.assertTrue((references / 'delivery-authority.md').is_file())
        policy_text = policy.read_text(encoding='utf-8')
        self.assertIn('## Recursive discovery and experiments', policy_text)
        self.assertIn('## Navigator execution mode adapter', policy_text)
        requirements = guidance.ENVIRONMENT_DISCOVERY_REQUIREMENTS
        self.assertEqual(set(requirements), {'discovery', 'research'})
        discovery_lines = (
            'One investigation allowance spans applicable discovery and research review stages; '
            'a stage boundary does not refill it.',
            f'Recursive discovery policy: {policy}#recursive-discovery-and-experiments',
            f'Navigator adapter: {policy}#navigator-execution-mode-adapter',
        )
        for name in ('delivery', 'blocked-resume', 'pause-resume'):
            report = driver.run_scenario(name, driver.scenarios()[name])
            self.assertTrue(report['ok'], report.get('error'))
            for event in report['events']:
                with self.subTest(scenario=name, stage=event['from'], command=event['command']):
                    prompt = event['prompt']
                    self.assertEqual(prompt.count(
                        f'Access-readiness policy: {policy}#early-access-readiness'
                    ), 1)
                    self.assertEqual(prompt.count(
                        'Cross-run knowledge policy: '
                        + str(policy.parent / 'project-knowledge.md')
                    ), 1)
                    self.assertIn(
                        'Repository knowledge index (host-authored, if present): ',
                        prompt,
                    )
                    self.assertEqual(prompt.count(
                        'Consumer testing guide: '
                        + str(policy.parent / 'testing-and-documentation.md')
                        + '#lightweight-and-browser-checks'
                    ), 1)
                    self.assertEqual(prompt.count(
                        'Worktree and artifact policy: '
                        + str(policy.parent / 'workspace-lifecycle.md')
                    ), 1)
                    self.assertEqual(prompt.count(
                        'Delivery-authority policy: ' + str(references / 'delivery-authority.md')
                    ), 1)
                    self.assertEqual(prompt.count(f'Environment lifecycle policy: {lifecycle}'), 1)
                    self.assertEqual(prompt.count(
                        'Environment lifecycle note (host-authored, if present): '
                        + str(driver.RUN / 'notes' / 'environment-lifecycle.md')
                    ), 1)
                    # Only the discovery and research producers carry the
                    # environment discovery requirement and its locators.
                    discovery = event['from'] in requirements
                    self.assertEqual(prompt.count('Environment discovery requirement: '),
                                     int(discovery))
                    if discovery:
                        self.assertIn('Environment discovery requirement: '
                                      + requirements[event['from']], prompt)
                    for line in discovery_lines:
                        self.assertEqual(prompt.count(line), int(discovery), line)

    def test_dry_run_simulates_actual_improve_handoffs_without_starting_them(self):
        expected = {'delivery': 42, 'two-work-items': 62, 'blocked-resume': 44,
                    'repeat-improve': 44, 'revise': 50, 'pause-resume': 44, 'halted': 1}
        scenarios = driver.scenarios()
        self.assertEqual(set(scenarios), set(expected))
        for name, scenario in scenarios.items():
            with self.subTest(name=name):
                report = driver.run_scenario(name, scenario)
                self.assertTrue(report['ok'], report.get('error'))
                self.assertEqual(len(report['events']), expected[name])
                self.assertEqual(report['simulated_status'],
                                 'halted' if name == 'halted' else 'done')
                for event in report['events']:
                    self.assertTrue(event['simulation_only'])
                    self.assertIn('owner', event)
                    self.assertIn('next_owner', event)
                    self.assertIn('completed_instances', event)
                    self.assertIn('Inspect the SDLC graph', event['prompt'])
                    self.assertIn(event['from'], event['prompt'])
                    self.assertFalse(
                        {'phase', 'subphase', 'counter', 'review_count'} & set(event)
                    )
                produces = [event for event in report['events'] if event['command'] == 'produce']
                finishes = [event for event in report['events'] if event['command'] == 'finish-improve']
                # An actual Improve child starts only for a planning/contract
                # stage result or the end-of-work carry-forward; every other
                # produce advances directly with no paired finish-improve.
                checkpoint_stages = guidance.PLANNING_REVIEW_STAGES | {'carry-forward'}
                self.assertTrue({event['from'] for event in finishes} <= checkpoint_stages)
                planning_produces = sorted(event['from'] for event in produces
                                           if event['from'] in guidance.PLANNING_REVIEW_STAGES)
                planning_finishes = sorted(event['from'] for event in finishes
                                           if event['from'] in guidance.PLANNING_REVIEW_STAGES)
                self.assertEqual(planning_produces, planning_finishes)
                self.assertTrue(all(event['simulation_only'] for event in report['events']))

        two_items = driver.run_scenario(
            'two-work-items', scenarios['two-work-items'])
        self.assertEqual(two_items['completed_instances'], ['W1', 'W2'])
        self.assertEqual({event['owner'] for event in two_items['events']
                          if event['owner'] != 'root'}, {'W1', 'W2'})
        produce_inner = [event for event in two_items['events']
                         if event['from'] in ('get-next-work-item', 'implement', 'carry-forward')
                         and event['command'] == 'produce']
        self.assertEqual([event['owner'] for event in produce_inner],
                         ['W1', 'W1', 'W1', 'W2', 'W2', 'W2'])
        # get-next-work-item/implement are not planning stages and W1's carry-forward
        # leaves W2 pending, so only W2's end-of-work carry-forward gets a
        # review; W1's carry-forward advances straight to W2 without one.
        finish_inner = [event for event in two_items['events']
                        if event['from'] in ('get-next-work-item', 'implement', 'carry-forward')
                        and event['command'] == 'finish-improve']
        self.assertEqual([event['owner'] for event in finish_inner], ['W2'])
        w1_produce = next(event for event in two_items['events']
                          if event['owner'] == 'W1' and event['from'] == 'carry-forward'
                          and event['command'] == 'produce')
        self.assertEqual(w1_produce['next_owner'], 'W2')
        self.assertEqual(w1_produce['completed_instances'], ['W1'])

    def test_wrong_edge_and_unknown_command_fail(self):
        wrong = copy.deepcopy(driver.scenarios()['delivery'])
        wrong['steps'][0]['expect'] = 'release'
        self.assertFalse(driver.run_scenario('skip', wrong)['ok'])
        wrong['steps'][0]['expect'] = 'discovery'
        wrong['steps'][0]['command'] = 'execute-shell'
        self.assertIn('unknown synthetic command', driver.run_scenario('shell', wrong)['error'])

    def test_unknown_top_level_script_field_is_refused_by_name(self):
        """A retired setting such as improve_cadence is refused, not ignored."""
        retired = copy.deepcopy(driver.scenarios()['delivery'])
        retired['improve_cadence'] = 'every-stage'
        report = driver.run_scenario('custom', retired)
        self.assertFalse(report['ok'])
        self.assertIn('scenario has unsupported fields: improve_cadence', report['error'])
        self.assertEqual(report['events'], [])

    def test_no_live_run_or_engine_calls(self):
        class ForbiddenCore:
            def __getattr__(self, name):
                raise AssertionError(f'Unexpected live core access: {name}')
        def forbidden(*args, **kwargs):
            raise AssertionError('Navigator dry-run attempted project execution or persistence')
        from contextlib import redirect_stdout
        from io import StringIO
        output = StringIO()
        with (patch.object(subprocess, 'run', side_effect=forbidden),
              patch.object(store, 'transaction', side_effect=forbidden),
              patch.object(navigator, 'save', side_effect=forbidden),
              redirect_stdout(output)):
            self.assertEqual(protocol.main(ForbiddenCore(), ['graph-dry-run']), 0)
        self.assertEqual(output.getvalue().count('PASS '), 7)

    def test_cli_custom_json_and_markdown_without_state_changes(self):
        with tempfile.TemporaryDirectory(prefix='navigator-dry-run-') as temporary:
            root = Path(temporary)
            sentinel = root / '.shiploop'
            sentinel.mkdir()
            state = sentinel / 'state.md'
            state.write_text('Unrelated incomplete run')
            before = state.read_bytes()
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            cli = [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run']
            result = subprocess.run(cli + ['--format', 'json'], cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data['simulation_only'])
            self.assertEqual(len(data['scenarios']), 7)
            example = ROOT / 'skills/shiploop/references/graph-dry-run-scenario.json'
            custom = subprocess.run(cli + ['--script', str(example), '--format', 'markdown'],
                                    cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(custom.returncode, 0, custom.stdout + custom.stderr)
            self.assertIn('intake -> discovery', custom.stdout)
            self.assertEqual(state.read_bytes(), before)
            self.assertEqual([p.name for p in sentinel.iterdir()], ['state.md'])

    def test_cli_simulates_protocol_4_without_touching_saved_state(self):
        with tempfile.TemporaryDirectory(prefix='navigator-dry-run-v4-') as temporary:
            root = Path(temporary)
            sentinel = root / '.shiploop'
            sentinel.mkdir()
            state = sentinel / 'state.md'
            state.write_text('Unrelated incomplete run')
            before = state.read_bytes()
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            cli = [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run',
                   '--format', 'json']
            result = subprocess.run(cli, cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data['simulation_only'])
            self.assertEqual(data['protocol_version'], 4)
            self.assertEqual(set(item['name'] for item in data['scenarios']),
                             {'delivery', 'two-work-items', 'blocked-resume',
                              'repeat-improve', 'revise', 'pause-resume', 'halted'})
            self.assertEqual(state.read_bytes(), before)

    def test_every_listed_scenario_runs(self):
        # Regression: --list once printed names a protocol lacked, so
        # --scenario crashed with a bare KeyError (exit 1).
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        base = [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run']
        with tempfile.TemporaryDirectory(prefix='navigator-dry-run-list-') as temporary:
            listed = subprocess.run(base + ['--list'],
                                    cwd=temporary, env=env, capture_output=True, text=True)
            self.assertEqual(listed.returncode, 0, listed.stderr)
            names = listed.stdout.split()
            self.assertEqual(names, list(driver.scenarios()))
            for name in names:
                with self.subTest(scenario=name):
                    result = subprocess.run(
                        base + ['--scenario', name],
                        cwd=temporary, env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertNotIn('Traceback', result.stderr)

    def test_the_dry_run_simulates_the_selected_backchain_passes_option(self):
        scenario = driver.scenarios()['delivery']
        for mode in navigator.BACKCHAIN_PASSES_MODES:
            with self.subTest(mode=mode):
                with patch.object(navigator.guidance, 'prompt', wraps=guidance.prompt) as rendered:
                    report = driver.run_scenario('delivery', scenario, backchain_passes=mode)
                self.assertTrue(report['ok'], report.get('error'))
                self.assertTrue(rendered.call_args_list)
                self.assertEqual({call.kwargs['backchain_passes'] for call in rendered.call_args_list}, {mode})
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        base = [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run', '--scenario', 'delivery']
        with tempfile.TemporaryDirectory(prefix='navigator-dry-run-backchain-') as temporary:
            for mode in navigator.BACKCHAIN_PASSES_MODES:
                with self.subTest(cli=mode):
                    result = subprocess.run(base + ['--backchain-passes', mode], cwd=temporary, env=env,
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            refused = subprocess.run(base + ['--backchain-passes', 'two'], cwd=temporary, env=env,
                                     capture_output=True, text=True)
            self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
            self.assertIn('invalid choice', refused.stderr)

    def test_the_dry_run_simulates_the_selected_planning_review_option(self):
        for mode in navigator.PLANNING_REVIEW_MODES:
            with self.subTest(mode=mode):
                scenario = driver.scenarios(planning_review=mode)['delivery']
                with patch.object(navigator.guidance, 'prompt', wraps=guidance.prompt) as rendered:
                    report = driver.run_scenario('delivery', scenario, planning_review=mode)
                self.assertTrue(report['ok'], report.get('error'))
                self.assertTrue(rendered.call_args_list)
                self.assertEqual({call.kwargs['planning_review'] for call in rendered.call_args_list}, {mode})
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        base = [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run', '--scenario', 'all']
        with tempfile.TemporaryDirectory(prefix='navigator-dry-run-planning-review-') as temporary:
            for mode in navigator.PLANNING_REVIEW_MODES:
                with self.subTest(cli=mode):
                    result = subprocess.run(base + ['--planning-review', mode], cwd=temporary, env=env,
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout.count('PASS '), len(driver.scenarios()), result.stdout)
            for unregistered in ('once', 'two'):
                with self.subTest(refused=unregistered):
                    refused = subprocess.run(base + ['--planning-review', unregistered], cwd=temporary, env=env,
                                             capture_output=True, text=True)
                    self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
                    self.assertIn('invalid choice', refused.stderr)

    def test_the_dry_run_schedule_is_declared_per_planning_review_mode(self):
        """An independent oracle: the stages whose result starts an Improve child, declared here for each mode."""
        reviewed = {'stage': {'spec', 'test-strategy', 'plan', 'step-plan', 'test-spec',
                              'system-test-author', 'release-plan'},
                    'none': {'system-test-author', 'release-plan'}}
        events = {'stage': {'delivery': 42, 'two-work-items': 62, 'blocked-resume': 44, 'repeat-improve': 44,
                            'revise': 50, 'pause-resume': 44, 'halted': 1},
                  # none drops one finish-improve row for each planning result the option covers
                  'none': {'delivery': 37, 'two-work-items': 55, 'blocked-resume': 39, 'repeat-improve': 39,
                           'revise': 43, 'pause-resume': 39, 'halted': 1}}
        self.assertEqual(set(driver.REVIEWED3), set(navigator.PLANNING_REVIEW_MODES))
        for mode in navigator.PLANNING_REVIEW_MODES:
            self.assertEqual(driver.REVIEWED3[mode], reviewed[mode])
            for name, scenario in driver.scenarios(planning_review=mode).items():
                with self.subTest(mode=mode, scenario=name):
                    report = driver.run_scenario(name, scenario, planning_review=mode)
                    self.assertTrue(report['ok'], report.get('error'))
                    self.assertEqual(len(report['events']), events[mode][name])
                    finishes = {event['from'] for event in report['events'] if event['command'] == 'finish-improve'}
                    self.assertLessEqual(finishes, reviewed[mode] | {'carry-forward'})
                    self.assertEqual(finishes, set() if name == 'halted' else reviewed[mode] | {'carry-forward'})
        # a stage-mode script is refused by a none run: the oracle is not the engine's own table
        stale = driver.run_scenario('delivery', driver.scenarios()['delivery'], planning_review='none')
        self.assertFalse(stale['ok'])
        self.assertIn('event 4: expected spec/active, got test-strategy/active', stale['error'])
        # and the other way: a none script is refused by a stage run, which parks a child at spec
        early = driver.run_scenario('delivery', driver.scenarios(planning_review='none')['delivery'])
        self.assertFalse(early['ok'])
        self.assertIn('event 4: expected test-strategy/active, got spec/active', early['error'])

    def test_protocol_version_flag_is_retired(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        base = [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run']
        with tempfile.TemporaryDirectory(prefix='navigator-dry-run-flag-') as temporary:
            for version in ('3', '4'):
                with self.subTest(version=version):
                    result = subprocess.run(base + ['--protocol-version', version],
                                            cwd=temporary, env=env, capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('--protocol-version', result.stderr)

    def test_example_script_passes(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        example = ROOT / 'skills/shiploop/references/graph-dry-run-scenario.json'
        with tempfile.TemporaryDirectory(prefix='graph-dry-run-scenario-') as temporary:
            result = subprocess.run(
                [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run',
                 '--script', str(example), '--format', 'json'],
                cwd=temporary, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            events = json.loads(result.stdout)['scenarios'][0]['events']
            self.assertEqual([event['to'] for event in events],
                             ['discovery', 'research', 'spec', 'spec', 'test-strategy'])


class BackchainStageTextTests(unittest.TestCase):
    """The Backchain loop text and its resource list print only where a whole loop may start (plan).

    Measured on the 1.16.1 packets: the loop text was 553 words and the six-file list 1.5 KB at every Backchain
    stage, although only `plan` may request a whole loop. The other four stages print the read-only audit route,
    its one resource and a script-computed status of the loop resources a repair/revise needs. These are content
    pins (what each stage prints or omits), not word or byte pins: a packet may grow when an obligation needs it.
    """

    LOOP_STAGE = "plan"
    AUDIT_STAGES = ("spec", "step-plan", "carry-forward", "product-acceptance")

    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(prefix="backchain-stage-text-") as temporary:
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS / "shiploop"), "graph-dry-run", "--scenario", "delivery",
                 "--format", "json"], cwd=temporary, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        events = json.loads(result.stdout)["scenarios"][0]["events"]
        cls.packets = {event["from"]: event["prompt"] for event in events if event["command"] == "produce"}

    def test_the_dry_run_packet_carries_exactly_the_stage_guidance(self):
        for stage in (self.LOOP_STAGE, *self.AUDIT_STAGES):
            with self.subTest(stage=stage):
                self.assertEqual(self.packets[stage].count(guidance._backchain_guidance(stage)), 1)

    def test_only_the_loop_stage_prints_the_resource_list_and_the_others_print_the_audit_line_and_status(self):
        for stage in (self.LOOP_STAGE, *self.AUDIT_STAGES):
            packet = self.packets[stage]
            with self.subTest(stage=stage):
                loop = stage == self.LOOP_STAGE
                self.assertEqual("Selected Backchain and Until Loop resources" in packet, loop)
                self.assertEqual("Backchain audit resource (" in packet, not loop)
                self.assertEqual("Loop resources for a repair/revise request, under " in packet, not loop)
                if not loop:
                    self.assertIn(": all present", packet.split("Loop resources for a repair/revise request, under ")[1]
                                  .splitlines()[0])

    def test_audit_stages_offer_the_audit_and_one_bounded_repair_and_not_the_loop_text(self):
        for stage in self.AUDIT_STAGES:
            flat = " ".join(guidance._backchain_guidance(stage).split())
            with self.subTest(stage=stage):
                self.assertIn("action `review` / stage `audit`", flat)
                self.assertIn("read-only, one-pass diagnostic", flat)
                self.assertIn("exactly one action `repair` / stage `revise`", flat)
                self.assertIn("Until Loop state budget", flat)  # a repair/revise request starts a loop
                self.assertIn("A whole `plan`/`draft` is requested only at `plan`", flat)
                self.assertIn("A MISSING loop resource blocks repair/revise; no other install substitutes", flat)
                for loop_text in ("`MISSING: ...`", "Record the binding id", "required_trivial_reviews"):
                    self.assertNotIn(loop_text, flat)
                packet = self.packets[stage]
                self.assertEqual(packet.count("Backchain planning guide: "), 1)  # the pointer stays at every stage
                self.assertEqual(packet.count("Backchain graph check: "), 1)  # the record-only check line stays

    LOOP_OBLIGATIONS = ("`MISSING: ...` entry blocks the route for that named resource",
                        "never substitute a sibling, cache or other install",
                        "Record the binding id, candidate and receipt paths",
                        "is not execution evidence or a passed experiment",
                        "The planning guide's Source-aware native caller section holds",
                        "Until Loop state budget", "action `plan` / stage `draft`",
                        "Backchain standalone Until Loop binding: <binding-id>",
                        "only after the child reports `complete`",
                        "final candidate identity and domain evidence",
                        "The Until Loop child is plan-only")

    def test_the_loop_stage_keeps_every_obligation_the_trim_did_not_target_in_every_mode(self):
        for mode in ("one", "converge"):
            flat = " ".join(guidance._backchain_guidance(self.LOOP_STAGE, backchain_passes=mode).split())
            for kept in self.LOOP_OBLIGATIONS:
                with self.subTest(mode=mode, kept=kept):
                    self.assertIn(kept, flat)
        self.assertIn("Backchain graph check: ", self.packets[self.LOOP_STAGE])

    def test_converge_prints_the_two_review_gate_and_none_of_the_one_pass_text(self):
        flat = " ".join(guidance._backchain_guidance(self.LOOP_STAGE, backchain_passes="converge").split())
        self.assertIn("required_trivial_reviews: 2", flat)
        self.assertIn("two consecutive distinct complete trivial/no-change dependency reviews", flat)
        for one_pass in ("required_trivial_reviews: 0", "Backchain passes", "One complete dependency"):
            with self.subTest(one_pass=one_pass):
                self.assertNotIn(one_pass, flat)

    def test_one_prints_gate_zero_the_exit_condition_and_the_marker_line_and_not_the_two_review_text(self):
        flat = " ".join(guidance._backchain_guidance(self.LOOP_STAGE, backchain_passes="one").split())
        self.assertEqual(flat.count("`required_trivial_reviews: 0`"), 1)
        for printed in ("Backchain passes: one.",
                        "Put the line `Backchain passes: one` beside the binding marker in the child request",
                        "this exit condition verbatim",
                        "One complete dependency review/fix/check cycle has run",
                        "every finding of that cycle is repaired within the edit bounds",
                        "every `Confirm by` clause on a step this cycle may change meets the planning guide's Outcomes rule",
                        "the printed `backchain-check` is ok on the final candidate and its receipt is cited",
                        "final candidate-specific domain evidence is saved",
                        "reports `exit_assessment: satisfied` even when it repaired the candidate",
                        "no second review runs"):
            with self.subTest(printed=printed):
                self.assertIn(printed, flat)
        for two_review in ("required_trivial_reviews: 2", "two consecutive", "trivial/no-change dependency reviews"):
            with self.subTest(two_review=two_review):
                self.assertNotIn(two_review, flat)

    def test_the_stage_prompt_carries_the_text_of_the_modes_it_is_given(self):
        # the route, not the module constants: the mode the CLI records reaches the packet the host reads
        for mode, gate in (("one", "required_trivial_reviews: 0"), ("converge", "required_trivial_reviews: 2")):
            with tempfile.TemporaryDirectory(prefix="backchain-mode-text-") as temporary:
                result = subprocess.run(
                    [sys.executable, "-B", str(SCRIPTS / "shiploop"), "graph-dry-run", "--scenario", "delivery",
                     "--backchain-passes", mode, "--format", "json"], cwd=temporary,
                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            events = json.loads(result.stdout)["scenarios"][0]["events"]
            packets = {event["from"]: event["prompt"] for event in events if event["command"] == "produce"}
            with self.subTest(mode=mode):
                self.assertIn(gate, packets[self.LOOP_STAGE])
                self.assertEqual(packets[self.LOOP_STAGE].count(
                    guidance._backchain_guidance(self.LOOP_STAGE, backchain_passes=mode)), 1)
                for stage in self.AUDIT_STAGES:
                    self.assertNotIn("required_trivial_reviews", packets[stage])
                    self.assertEqual(packets[stage].count(
                        guidance._backchain_guidance(stage, backchain_passes=mode)), 1)

    POINTER = ("A repair/revise child runs one review/fix/check cycle: put the line `Backchain passes: one` "
               "beside the binding marker in the child request, as Backchain's convergence reference defines it")

    def test_audit_stages_carry_the_one_pass_pointer_in_mode_one_and_nothing_in_converge(self):
        for stage in self.AUDIT_STAGES:
            one = " ".join(guidance._backchain_guidance(stage, backchain_passes="one").split())
            converge = " ".join(guidance._backchain_guidance(stage, backchain_passes="converge").split())
            with self.subTest(stage=stage):
                self.assertEqual(one.count(self.POINTER), 1)
                self.assertNotIn("Backchain passes", converge)
                # the pointer names no literal gate field in either mode (see the audit-text pin above)
                self.assertNotIn("required_trivial_reviews", one + converge)
                # a pointer is all mode one adds: the rest of the audit text is the converge text
                self.assertEqual(one.replace(self.POINTER + ". ", ""), converge)


    # Batch 1009 BC1: the one-pass plan packet said "may request" and, a few lines later, "Write the child's start
    # contract ... verbatim", and models read the child as required or optional by chance; both Sonnet round-1 runs
    # skipped it and ran the printed backchain-check on a prose plan.  The packet says what the script enforces.
    CHOICE = ("The `plan`/`draft` request is your choice",
              "nothing refuses a plan without it",
              "ShipLoop cannot see whether the child ran",
              "dependency audit is not optional on either route",
              "Say in this result's `summary` which route you took and why",
              "The start contract below applies only if you request the child",
              "reads a candidate graph in Backchain's plan schema (Backchain SKILL.md, \"Plan document shape\"), not a prose plan")

    def test_the_one_pass_plan_packet_says_the_child_is_a_choice_and_the_audit_is_not(self):
        flat = " ".join(guidance._backchain_guidance(self.LOOP_STAGE, backchain_passes="one").split())
        packet = " ".join(self.packets[self.LOOP_STAGE].split())
        for phrase in self.CHOICE:
            with self.subTest(phrase=phrase):
                self.assertEqual(flat.count(phrase), 1)
                self.assertEqual(packet.count(phrase), 1)  # the dry-run CLI route prints it, once
        # It sits before the gate it qualifies, so a reader meets "optional" before "write the contract verbatim".
        self.assertLess(flat.index(self.CHOICE[0]), flat.index("Write the child's start contract"))

    def test_the_choice_is_said_only_where_the_one_pass_gate_is_printed(self):
        """GUARD (passes on the unchanged tree): converge is the owner choosing the heavier route and its gate text has no
        'write verbatim' sentence to qualify; the audit stages and a `none` run offer no whole child at all."""
        quiet = {f"{stage} (one)": guidance._backchain_guidance(stage, backchain_passes="one") for stage in self.AUDIT_STAGES}
        quiet["plan (converge)"] = guidance._backchain_guidance(self.LOOP_STAGE, backchain_passes="converge")
        quiet["plan (none)"] = guidance._backchain_guidance(self.LOOP_STAGE, backchain_passes="none")
        for label, text in quiet.items():
            with self.subTest(label):
                flat = " ".join(text.split())
                self.assertNotIn("your choice", flat)
                self.assertNotIn("nothing refuses a plan without it", flat)

    NONE_SENTENCE = "No whole `plan`/`draft` is requested in this run"
    # The six resources only a whole loop reads; the seventh, the caller contract, serves the read-only audit.
    LOOP_ONLY_LABELS = ("Backchain SKILL.md", "Backchain references/convergence.md",
                        "Backchain prompts/convergence-review.prompt.md", "Until Loop ADAPTER.md",
                        "Until Loop references/runtime-ephemeral.md", "Until Loop scripts/until_loop_ephemeral.py")

    _mode_packets = {}

    @classmethod
    def packets_in(cls, mode):
        """The producer packets of the dry-run delivery scenario for `mode`, through the real CLI (once per mode)."""
        if mode not in cls._mode_packets:
            with tempfile.TemporaryDirectory(prefix="backchain-none-text-") as temporary:
                result = subprocess.run(
                    [sys.executable, "-B", str(SCRIPTS / "shiploop"), "graph-dry-run", "--scenario", "delivery",
                     "--backchain-passes", mode, "--format", "json"], cwd=temporary,
                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), capture_output=True, text=True)
            assert result.returncode == 0, result.stderr
            events = json.loads(result.stdout)["scenarios"][0]["events"]
            cls._mode_packets[mode] = {event["from"]: event["prompt"]
                                       for event in events if event["command"] == "produce"}
        return cls._mode_packets[mode]

    def test_none_offers_no_whole_plan_or_draft_and_keeps_the_audit_route_and_the_budget_at_plan(self):
        plan = self.packets_in("none")[self.LOOP_STAGE]
        printed = guidance._backchain_guidance(self.LOOP_STAGE, backchain_passes="none")
        self.assertEqual(plan.count(printed), 1)  # the route: the mode the CLI records reaches the packet
        flat = " ".join(printed.split())
        for kept in (self.NONE_SENTENCE, "action `review` / stage `audit`", "read-only, one-pass diagnostic",
                     "exactly one action `repair` / stage `revise`", self.POINTER, "Until Loop state budget",
                     "A MISSING loop resource blocks repair/revise; no other install substitutes"):
            with self.subTest(kept=kept):
                self.assertIn(kept, flat)
        for dropped in ("A whole `plan`/`draft` is requested only", "action `plan` / stage `draft`",
                        "Backchain standalone Until Loop binding", "required_trivial_reviews",
                        "`MISSING: ...`", "Record the binding id", "The Until Loop child is plan-only",
                        "Backchain passes: one.", "Backchain passes: none"):
            with self.subTest(dropped=dropped):
                self.assertNotIn(dropped, flat)
        self.assertEqual(flat.count("`plan`/`draft`"), 1)  # named once: to say it is not requested
        self.assertIn("Backchain graph check: ", plan)  # the record-only check command line stays
        self.assertIn(guidance.BACKCHAIN_CHECK, plan)  # and the guidance sentence that tells the host to run it
        self.assertEqual(plan.count("Backchain planning guide: "), 1)

    def test_none_prints_the_audit_resource_and_the_loop_status_not_the_six_file_block_at_plan(self):
        plan = self.packets_in("none")[self.LOOP_STAGE]
        self.assertNotIn("Selected Backchain and Until Loop resources", plan)
        for label in self.LOOP_ONLY_LABELS:
            with self.subTest(label=label):
                self.assertNotIn("  " + label + ": ", plan)
        self.assertIn("Backchain audit resource (", plan)
        status = plan.split("Loop resources for a repair/revise request, under ")[1].splitlines()[0]
        self.assertIn(": all present", status)

    def test_one_and_converge_still_print_the_whole_loop_and_the_six_file_block_at_plan(self):
        for mode in ("one", "converge"):
            plan = self.packets_in(mode)[self.LOOP_STAGE]
            with self.subTest(mode=mode):
                self.assertIn("action `plan` / stage `draft`", " ".join(plan.split()))
                self.assertNotIn(self.NONE_SENTENCE, " ".join(plan.split()))
                self.assertIn("Selected Backchain and Until Loop resources", plan)
                for label in self.LOOP_ONLY_LABELS:
                    self.assertIn("  " + label + ": ", plan)
                self.assertNotIn("Backchain audit resource (", plan)
                self.assertNotIn("Loop resources for a repair/revise request", plan)

    def test_the_plan_packet_is_shorter_in_none_than_in_one_and_in_converge(self):
        words = {mode: len(self.packets_in(mode)[self.LOOP_STAGE].split()) for mode in guidance.BACKCHAIN_PASSES_MODES}
        self.assertLess(words["none"], words["one"], words)
        self.assertLess(words["none"], words["converge"], words)
        # and the printed guidance alone, so the saving is the loop text and not a side effect elsewhere
        guidance_words = {mode: len(guidance._backchain_guidance(self.LOOP_STAGE, backchain_passes=mode).split())
                          for mode in guidance.BACKCHAIN_PASSES_MODES}
        self.assertLess(guidance_words["none"], guidance_words["one"], guidance_words)
        self.assertLess(guidance_words["none"], guidance_words["converge"], guidance_words)

    def test_none_says_at_every_audit_stage_that_no_whole_loop_is_requested_and_keeps_the_rest(self):
        for stage in self.AUDIT_STAGES:
            none = " ".join(guidance._backchain_guidance(stage, backchain_passes="none").split())
            one = " ".join(guidance._backchain_guidance(stage, backchain_passes="one").split())
            with self.subTest(stage=stage):
                self.assertEqual(none.count(self.NONE_SENTENCE), 1)
                self.assertNotIn("Backchain passes: none", none)  # `one` is the only marker value the reference defines
                self.assertNotIn("A whole `plan`/`draft` is requested only", none)
                self.assertIn(self.POINTER, none)  # a repair/revise after a finding runs one pass
                self.assertNotIn("required_trivial_reviews", none)
                # the sentence is all that differs from mode one
                self.assertEqual(none.replace(self.NONE_SENTENCE + ".", "A whole `plan`/`draft` is requested only at `plan`."),
                                 one)
            self.assertEqual(self.packets_in("none")[stage].count(
                guidance._backchain_guidance(stage, backchain_passes="none")), 1)

if __name__ == '__main__':
    unittest.main()
