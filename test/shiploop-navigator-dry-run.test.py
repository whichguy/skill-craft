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
import shiploop_packet_symbols as symbols  # noqa: E402
import shiploop_prompts as guidance  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_reference as run_reference  # noqa: E402
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


def is_improve_packet(prompt):
    """The Improve stage's packet: its header names the stage `improve` and the reviewed result."""
    return prompt.splitlines()[0].startswith('ShipLoop navigator | improve | revision ')


def reviewed_stages(events):
    """For each finish-improve event, the stage whose result it reviews: the nearest produce event before it."""
    found = []
    for index, event in enumerate(events):
        if event['command'] == 'finish-improve':
            earlier = [e for e in events[:index] if e['command'] == 'produce']
            found.append(earlier[-1]['from'])
    return found


class BattleshipMeasurementTests(unittest.TestCase):
    """The run-feedback plan's measurement: a metadata-only item costs the host far less."""

    def test_a_metadata_only_item_skips_its_test_stage(self):
        counts = host_work_per_item({"W1": CODE_ITEM, "W2": METADATA_ITEM})
        # W1 walks all 7 INNER stages (verify retired, design T §9.1 2b-4c); its step-plan and its implemented change
        # (rule item) get Improve reviews, and its test-spec none (2026-10-26).
        self.assertEqual(counts["W1"], {"packets": 7, "reviews": 2})
        # W2 loses the test stage (no command, only non-code paths); the end-of-work review is added. Its step-plan
        # follows W1's reviewed pattern (rule first-item, 2026-10-19): implement and carry-forward remain.
        self.assertEqual(counts["W2"], {"packets": 6, "reviews": 2})

    def test_without_proof_a_no_command_item_still_walks_every_stage(self):
        code_without_commands = {"paths": ["src/**"], "test_commands": [],
                                 "test_commands_na": "The model says there is nothing to test."}
        counts = host_work_per_item({"W1": code_without_commands})
        self.assertEqual(counts["W1"]["packets"], 7)

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
        # The requirement and the shared allowance are in the discovery and research duties (packet re-cut,
        # 2026-10-11); a packet keeps only the two locators and no longer prints the requirement line.
        discovery_lines = (
            f'Recursive discovery policy: {policy}#recursive-discovery-and-experiments',
            f'Navigator adapter: {policy}#navigator-execution-mode-adapter',
        )
        # 2026-10-11 dedupe: a packet prints a policy locator once, only when its own text names the
        # label; every policy and guide, and the host-authored lifecycle note, is listed in the run
        # reference file (#policies), which each packet points at.
        reference = run_reference.render({"planning_review": "stage"}, driver.RUN)
        policies = {
            'Access-readiness policy': f'{policy}#early-access-readiness',
            'Cross-run knowledge policy': str(policy.parent / 'project-knowledge.md'),
            'Consumer testing guide': str(policy.parent / 'testing-and-documentation.md')
            + '#lightweight-and-browser-checks',
            'Worktree and artifact policy': str(policy.parent / 'workspace-lifecycle.md'),
            'Delivery-authority policy': str(references / 'delivery-authority.md'),
            'Environment lifecycle policy': str(lifecycle),
        }
        lifecycle_note = ('Environment lifecycle note (host-authored, if present): '
                          + str(driver.RUN / 'notes' / 'environment-lifecycle.md'))
        self.assertIn(lifecycle_note, reference)
        for label, target in policies.items():
            self.assertIn(f'{label}: {target}', reference)
        printed_somewhere = set()
        for name in ('delivery', 'blocked-resume', 'pause-resume'):
            report = driver.run_scenario(name, driver.scenarios()[name])
            self.assertTrue(report['ok'], report.get('error'))
            for event in report['events']:
                with self.subTest(scenario=name, stage=event['from'], command=event['command']):
                    prompt = symbols.guides_expanded(event['prompt'])  # a packet prints guides as GUIDES/<file>
                    if is_improve_packet(prompt):
                        # The Improve packet is two instructions (re-cut, 2026-10-11) and carries no policy
                        # locators; those reach the Improve child through the handoff file.
                        # (The pure navigator does not bind at the transition, so the dry run prints the bind step.)
                        self.assertEqual(event['from'], 'improve')
                        self.assertIn('improve-bind', prompt)
                        self.assertNotIn('improve-complete', prompt)
                        continue
                    self.assertIn('reference.md (#policies', prompt)
                    self.assertIn(
                        'Repository knowledge index (host-authored, if present): ',
                        prompt,
                    )
                    for label, target in policies.items():
                        line = f'{label}: {target}'
                        printed = prompt.count(line)
                        self.assertLessEqual(printed, 1, line)
                        if prompt.count(label) > printed:
                            self.assertEqual(printed, 1, line)
                        if printed:
                            printed_somewhere.add(label)
                    self.assertEqual(prompt.count('Environment lifecycle note'), 0)
                    # Only the discovery and research producers carry the
                    # environment discovery requirement and its locators.
                    discovery = event['from'] in requirements
                    self.assertEqual(prompt.count('Environment discovery requirement: '), 0)
                    self.assertEqual(prompt.count('One investigation allowance spans'), 0)
                    if discovery:
                        self.assertIn('allowance', ' '.join(prompt.split()))
                    for line in discovery_lines:
                        self.assertEqual(prompt.count(line), int(discovery), line)
        # The selection is live: the packets of these scenarios print some policy locators.
        self.assertTrue(printed_somewhere)

    def test_dry_run_simulates_actual_improve_handoffs_without_starting_them(self):
        # two-work-items: 44 until rule first-item (2026-10-19) dropped W2's step-plan and test-spec reviews; each scenario
        # one fewer (send-back two: W1's test spec was reviewed again after it) since test-spec lost its review (2026-10-26),
        # and one fewer per work item since verify retired (design T §9.1 2b-4c).
        expected = {'delivery': 31, 'two-work-items': 39, 'blocked-resume': 33,
                    'send-back': 36, 'pause-resume': 33, 'halted': 1}
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
                    if not is_improve_packet(event['prompt']):
                        # The Improve packet is two instructions (re-cut, 2026-10-11) and no longer prints the request;
                        # the request reaches the Improve child through the opening ShipLoop writes.
                        # D2 (owner, 2026-10-17): the request is quoted whole at intake, spec and plan; every other
                        # producer packet points to RUN/request.md instead.
                        if event['from'] in navigator.REQUEST_WHOLE_STAGES:
                            self.assertIn('Inspect the SDLC graph', event['prompt'])
                        else:
                            self.assertIn('Original request: RUN/', event['prompt'])
                    self.assertIn(event['from'], event['prompt'])
                    self.assertFalse(
                        {'phase', 'subphase', 'counter', 'review_count'} & set(event)
                    )
                produces = [event for event in report['events'] if event['command'] == 'produce']
                finishes = [event for event in report['events'] if event['command'] == 'finish-improve']
                # An actual Improve child starts only for a planning/contract
                # stage result, a step's document stage (the step's review, design T §8)
                # or the end-of-work carry-forward; every other produce advances directly
                # with no paired finish-improve.
                # The finish is an event of the Improve stage; the stage it reviews is the producer before it.
                checkpoint_stages = guidance.PLANNING_REVIEW_STAGES | {'document', 'carry-forward'}
                self.assertEqual({event['from'] for event in finishes} - {'improve'}, set())
                reviewed = reviewed_stages(report['events'])
                self.assertTrue(set(reviewed) <= checkpoint_stages)
                # Rule first-item (2026-10-19): a later item's step-plan and test-spec advance without a review.
                planning_produces = sorted(event['from'] for event in produces
                                           if event['from'] in guidance.PLANNING_REVIEW_STAGES
                                           and not (event['from'] in ('step-plan', 'test-spec')
                                                    and event['owner'] not in ('root', 'W1')))
                planning_finishes = sorted(stage for stage in reviewed
                                           if stage in guidance.PLANNING_REVIEW_STAGES)
                self.assertEqual(planning_produces, planning_finishes)
                self.assertTrue(all(event['simulation_only'] for event in report['events']))

        two_items = driver.run_scenario(
            'two-work-items', scenarios['two-work-items'])
        self.assertEqual(two_items['completed_instances'], ['W1', 'W2'])
        self.assertEqual({event['owner'] for event in two_items['events']
                          if event['owner'] != 'root'}, {'W1', 'W2'})
        produce_inner = [event for event in two_items['events']
                         if event['from'] in ('step-plan', 'implement', 'carry-forward')
                         and event['command'] == 'produce']
        self.assertEqual([event['owner'] for event in produce_inner],
                         ['W1', 'W1', 'W1', 'W2', 'W2', 'W2'])
        # Each item's one step gets its step review after its document stage (design T §8). W1's carry-forward
        # leaves W2 pending, so only W2's end-of-work carry-forward gets a
        # review; W1's carry-forward advances straight to W2 without one.
        two_events = two_items['events']
        finish_inner = [(stage, event['owner'])
                        for stage, event in zip(reviewed_stages(two_events),
                                                [e for e in two_events if e['command'] == 'finish-improve'])
                        if stage in ('document', 'carry-forward')]
        self.assertEqual(finish_inner, [('document', 'W1'), ('document', 'W2'), ('carry-forward', 'W2')])
        w1_produce = next(event for event in two_items['events']
                          if event['owner'] == 'W1' and event['from'] == 'carry-forward'
                          and event['command'] == 'produce')
        self.assertEqual(w1_produce['next_owner'], 'W2')
        self.assertEqual(w1_produce['completed_instances'], ['W1'])

    def test_the_blocked_resume_scenario_waits_on_a_service_and_the_send_back_scenario_returns_to_the_step_plan(self):
        scenarios = driver.scenarios()
        # repeat is retired and revise is send-back (N5), so neither old scenario name is declared.
        self.assertFalse({'repeat-improve', 'revise'} & set(scenarios))
        steps = scenarios['blocked-resume']['steps']
        self.assertEqual((steps[0]['at'], steps[0]['result']['outcome'], steps[0]['result']['awaiting']['kind']),
                         ('intake', 'blocked', 'service'))
        self.assertEqual((steps[1]['command'], steps[1]['expect']), ('resume', 'intake'))
        self.assertTrue(steps[1]['observed'])  # a service wait resumes on --observed, never without a reply
        without = copy.deepcopy(scenarios['blocked-resume'])
        del without['steps'][1]['observed']
        refused = driver.run_scenario('no-reply', without)
        self.assertFalse(refused['ok'])
        self.assertIn('resume with --observed', refused['error'])
        # An answer wait is not satisfied by an observation, so the dry run cannot be made to resume on the wrong flag.
        wrong = copy.deepcopy(scenarios['blocked-resume'])
        wrong['steps'][0]['result']['awaiting'] = {'kind': 'answer', 'question': 'Which prerequisite?',
                                                   'no_default': 'Synthetic: only the user can choose.'}
        self.assertFalse(driver.run_scenario('wrong-flag', wrong)['ok'])
        back = next(row for row in scenarios['send-back']['steps'] if row['at'] == 'implement'
                    and row.get('result', {}).get('outcome') == 'send-back')
        self.assertEqual(back['expect'], 'step-plan')

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
        self.assertEqual(output.getvalue().count('PASS '), 6)

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
            self.assertEqual(len(data['scenarios']), 6)
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
                              'send-back', 'pause-resume', 'halted'})
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

    def test_the_dry_run_has_no_backchain_passes_option(self):
        """Backchain is retired (owner decision 2026-11-16): the option is gone from the dry run as from the run."""
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        base = [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run', '--scenario', 'delivery']
        with tempfile.TemporaryDirectory(prefix='navigator-dry-run-backchain-') as temporary:
            refused = subprocess.run(base + ['--backchain-passes', 'none'], cwd=temporary, env=env,
                                     capture_output=True, text=True)
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn('unrecognized arguments: --backchain-passes', refused.stderr)

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
        # Each step's review follows its document stage in both modes (rule item, design T §8; planning_review none does
        # not skip it), and test-spec has none.
        reviewed = {'stage': {'spec', 'test-strategy', 'plan', 'step-plan',
                              'system-test-author', 'release-plan', 'document'},
                    'none': {'system-test-author', 'release-plan', 'document'}}
        # One verify packet fewer per work item since verify retired (design T §9.1 2b-4c).
        events = {'stage': {'delivery': 31, 'two-work-items': 39, 'blocked-resume': 33, 'send-back': 36,
                            'pause-resume': 33, 'halted': 1},
                  # none drops one finish-improve row for each planning result the option covers
                  'none': {'delivery': 27, 'two-work-items': 35, 'blocked-resume': 29, 'send-back': 31,
                           'pause-resume': 29, 'halted': 1}}
        self.assertEqual(set(driver.REVIEWED3), set(navigator.PLANNING_REVIEW_MODES))
        for mode in navigator.PLANNING_REVIEW_MODES:
            self.assertEqual(driver.REVIEWED3[mode], reviewed[mode])
            for name, scenario in driver.scenarios(planning_review=mode).items():
                with self.subTest(mode=mode, scenario=name):
                    report = driver.run_scenario(name, scenario, planning_review=mode)
                    self.assertTrue(report['ok'], report.get('error'))
                    self.assertEqual(len(report['events']), events[mode][name])
                    finishes = set(reviewed_stages(report['events']))
                    self.assertLessEqual(finishes, reviewed[mode] | {'carry-forward'})
                    self.assertEqual(finishes, set() if name == 'halted' else reviewed[mode] | {'carry-forward'})
        # a stage-mode script is refused by a none run: the oracle is not the engine's own table
        stale = driver.run_scenario('delivery', driver.scenarios()['delivery'], planning_review='none')
        self.assertFalse(stale['ok'])
        self.assertIn('event 4: expected improve/active, got test-strategy/active', stale['error'])
        # and the other way: a none script is refused by a stage run, which parks the Improve stage after spec
        early = driver.run_scenario('delivery', driver.scenarios(planning_review='none')['delivery'])
        self.assertFalse(early['ok'])
        self.assertIn('event 4: expected test-strategy/active, got improve/active', early['error'])

    def test_each_reviewed_stage_is_followed_by_an_improve_row(self):
        """Improve is a stage of its own (owner, 2026-10-11): the dry run shows one `improve` row after each reviewed
        stage's produce row, with its own packet, and no other produce row is followed by one."""
        for mode in navigator.PLANNING_REVIEW_MODES:
            with self.subTest(mode=mode):
                rows = driver.activity(planning_review=mode)
                reviewed = driver.REVIEWED3[mode] | {'carry-forward'}
                for index, row in enumerate(rows):
                    if row['command'] != 'produce':
                        continue
                    followed = row['expect'] == navigator.IMPROVE_STAGE
                    if followed:
                        after = rows[index + 1]
                        self.assertEqual((after['at'], after['command']), (navigator.IMPROVE_STAGE, 'finish-improve'))
                        self.assertIn(row['at'], reviewed)
                    elif row['at'] in driver.REVIEWED3[mode]:
                        self.fail('reviewed stage ' + row['at'] + ' has no improve row after it')
                report = driver.run_scenario('delivery', driver.scenarios(planning_review=mode)['delivery'],
                                             planning_review=mode)
                self.assertTrue(report['ok'], report.get('error'))
                events = report['events']
                for index, event in enumerate(events):
                    if event['command'] == 'produce' and event['to'] == navigator.IMPROVE_STAGE:
                        after = events[index + 1]
                        self.assertEqual((after['from'], after['command']), ('improve', 'finish-improve'))
                        self.assertTrue(is_improve_packet(after['prompt']), after['prompt'].splitlines()[0])
                        self.assertIn('| the ' + event['from'] + ' result', after['prompt'].splitlines()[0])
                    if event['command'] == 'finish-improve':
                        self.assertEqual(events[index - 1]['to'], navigator.IMPROVE_STAGE)
                        self.assertNotEqual(event['to'], navigator.IMPROVE_STAGE)

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
                             ['discovery', 'research', 'spec', 'improve', 'test-strategy'])


class BackchainStageTextTests(unittest.TestCase):
    """What each Backchain stage prints, now that no stage offers a Backchain child (Backchain retired, owner decision
    2026-11-16): spec and plan fold the planning guide's item into their duty, a delegated step-plan or carry-forward
    prints the route paragraph with the record-only check, and an inline step-plan or carry-forward and
    product-acceptance print neither.  Content pins (what each stage prints or omits), not byte pins."""

    CHECK_READS = ("The printed `backchain-check` reads only a candidate graph in the plan graph format, a JSON file "
                   "(Backchain planning guide, \"Plan graph format\"), never a spec, a Markdown note or a prose plan.")
    CHECK_SCOPE = "Run it after each revision of a graph you wrote, and write none only to run it"
    RETIRED = ("This run requests no Backchain child", "source-aware-native", "`review` / `audit`",
               "`repair` / `revise`", "Backchain passes", "Selected Backchain and Until Loop resources",
               "Run the printed `backchain-check` after each candidate revision", "Plan document shape")

    @staticmethod
    def flat(text):
        return " ".join(text.split())

    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(prefix="backchain-stage-text-") as temporary:
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS / "shiploop"), "graph-dry-run", "--scenario", "delivery",
                 "--format", "json"], cwd=temporary,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        events = json.loads(result.stdout)["scenarios"][0]["events"]
        cls.packets = {event["from"]: event["prompt"] for event in events if event["command"] == "produce"}

    def test_each_route_prints_what_its_stage_needs_and_no_child_text(self):
        for stage in sorted(guidance.BACKCHAIN_STAGES):
            for delegation in (guidance.INLINE, guidance.ASK_AGENT):
                text = self.flat(guidance.prompt(stage, delegation=delegation))
                no_paragraph = (stage in guidance.INLINE_AUDIT_STAGES and delegation == guidance.INLINE
                                or stage in guidance.AUDIT_LINE_STAGES)
                with self.subTest(stage=stage, delegation=delegation):
                    self.assertEqual(text.count(self.CHECK_READS), 0 if no_paragraph else 1)
                    self.assertEqual(text.count(self.CHECK_SCOPE), 0 if no_paragraph else 1)
                    # an inline step-plan or carry-forward prints no paragraph; its packet locator names the guide
                    self.assertEqual("Backchain planning guide" in text,
                                     not (stage in guidance.INLINE_AUDIT_STAGES and delegation == guidance.INLINE))
                    for retired in self.RETIRED:
                        self.assertNotIn(retired, text)

    def test_product_acceptance_checks_a_dependency_gap_with_the_guide(self):
        for delegation in (guidance.INLINE, guidance.ASK_AGENT):
            with self.subTest(delegation=delegation):
                text = self.flat(guidance.prompt("product-acceptance", delegation=delegation))
                self.assertIn("check it with the Backchain planning guide's dependency audit and route it as item 6 "
                              "says", text)

    def test_the_dry_run_packets_print_the_check_sentence_at_spec_and_plan(self):
        for stage in guidance.BACKCHAIN_FOLDED_STAGES:
            with self.subTest(stage=stage):
                packet = self.flat(self.packets[stage])
                self.assertEqual(packet.count(self.CHECK_READS), 1)
                for retired in self.RETIRED:
                    self.assertNotIn(retired, packet)

    def test_the_plan_item_keeps_the_audit_and_the_carried_locators(self):
        plan = self.flat(guidance.duty("plan", delegation=guidance.INLINE))
        self.assertIn("Run the dependency audit of the Backchain planning guide.", plan)
        self.assertIn("Keep material findings visible in `summary`. Carry the selected requirement sections and test "
                      "locators through the plan and the items' `context`.", plan)
        spec = self.flat(guidance.duty("spec", delegation=guidance.INLINE))
        self.assertIn("Check outcomes and missing prerequisites with the Backchain planning guide.", spec)

    def test_the_planning_guide_defines_the_graph_format_the_check_reads(self):
        guide = (SCRIPTS.parent / "references" / "backchain-planning.md").read_text(encoding="utf-8")
        section = guide.split("## Plan graph format\n", 1)[1].split("\n## ", 1)[0]
        for clause in ("Write one only when the work needs a graph", "**Structural invariants.**",
                       "every `from: null` need appears in `initial_state`"):
            with self.subTest(clause=clause):
                self.assertIn(clause, self.flat(section))


class BindCommandTests(unittest.TestCase):
    """Batch 1009 B1a: a packet that tells the host to bind the Improve card prints a path ShipLoop knows, not a template.

    The round-1 runs each built the path by hand (`IMP=.../skills/improve/SKILL.md; ls $IMP`) from the CLI path, although
    ShipLoop's own sibling card is a fact it can read (SPEC S-4: copy printed values; S-5: the script decides what it can).
    """

    def test_no_dry_run_packet_prints_a_placeholder_path_in_a_command(self):
        import shlex
        seen = 0
        for delegation in navigator.DELEGATIONS:
            for name, scenario in driver.scenarios().items():
                report = driver.run_scenario(name, scenario, delegation=delegation)
                self.assertTrue(report['ok'], report.get('error'))
                for event in report['events']:
                    prompt = event['prompt']
                    with self.subTest(delegation=delegation, scenario=name, sequence=event['sequence']):
                        self.assertNotIn('/absolute/path/to', prompt)
                        for line in prompt.splitlines():
                            # The bind line's lead-in holds an apostrophe ("skill's"); parse only the command.
                            command = line.split('): ', 1)[1] if line.startswith('Next command (') else line
                            for token in shlex.split(command) if '--skill-card=' in line else ():
                                if token.startswith('--skill-card='):
                                    seen += 1
                                    self.assertTrue(os.path.isabs(token.split('=', 1)[1]), line)
        self.assertGreater(seen, 0, 'the dry run reaches a packet that binds the Improve card')

    def test_a_run_with_no_recorded_card_prints_a_marked_blank_and_where_shiploop_looks(self):
        """The not-recorded sample: a saved run that predates init-time resolution, or an install with no sibling card."""
        done = {'outcome': 'done', 'summary': 'Synthetic declaration; no work executed.'}
        state = navigator.new_state('/simulation-only/repo', 'Bind sample.', improve_skill='')
        while navigator.current_stage(state) != 'spec':
            state = navigator.apply(state, navigator.current_action(state)['id'], done)
        waiting = navigator.apply(state, navigator.current_action(state)['id'], done)
        packet = navigator.render(driver.CORE, driver.RUN, waiting)
        self.assertNotIn('/absolute/path/to', packet)
        self.assertIn(navigator.IMPROVE_CARD_BLANK, packet)
        self.assertIn('No Improve card is recorded for this run.', packet)
        self.assertIn(str(guidance.installed_improve_card()), packet)

if __name__ == '__main__':
    unittest.main()
