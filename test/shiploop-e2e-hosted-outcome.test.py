#!/usr/bin/env python3
"""Hermetic hosted discovery tests through the real named-case entry point."""
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test/shiploop_e2e"
sys.path.insert(0, str(HARNESS))
from hosted_outcome import attempt, binding as b  # noqa: E402
from hosted_outcome import operator_fixtures  # noqa: E402

SCENARIO = HARNESS / "scenarios" / b.CASE
TEMPLATE_IGNORE = Path("/opt/homebrew/lib/node_modules/@salesforce/cli/node_modules/@salesforce/templates/lib/templates/project/.forceignore")


class HostedOutcome(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.home = self.root / "operator"
        (self.home / ".codex").mkdir(parents=True)
        (self.home / ".codex/auth.json").write_text("{}")
        old_path = self.root / "old-path"
        old_path.mkdir()
        (old_path / "grok-chat-ui").touch(mode=0o700)
        env = patch.dict(os.environ, {"HOME": str(self.home), "XDG_STATE_HOME": str(self.root / "xdg"),
                                      "CODEX_HOME": str(self.home / ".codex"),
                                      "SHIPLOOP_E2E_LEASES": str(self.root / "leases"),
                                      "PATH": f"{old_path}:{os.environ['PATH']}", "E2E_CHECKS": "old",
                                      "E2E_BIND_DEPLOY_SOURCE": "1", "SF_ACCESS_TOKEN": "fixture-secret"})
        env.start()
        self.addCleanup(env.stop)
        self.build = "1" * 40
        fixture = self.root / "publication/plugins/skill-craft"
        manifest = fixture / ".claude-plugin/plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text('{"version": "3.2.0"}')
        for name in ("shiploop", "improve"):
            shutil.copytree(ROOT / "skills" / name, fixture / "skills" / name,
                            ignore=shutil.ignore_patterns("__pycache__"))
        archive_path = self.root / "published.tar"
        with tarfile.open(archive_path, "w") as archive:
            archive.add(fixture, arcname="plugins/skill-craft")
        self.exe("git", f"""#!/bin/sh
case "$3" in
fetch) exit 0;;
ls-tree) [ "$6" = origin/main ] && exit 0;;
show)
case "$4" in
origin/main:.claude-plugin/marketplace.json) echo '{{"plugins":[{{"name":"skill-craft","version":"3.2.0"}}]}}'; exit;;
origin/main:plugins/skill-craft/skills/shiploop/SKILL.md) echo 'version: 2.2.0'; exit;;
esac;;
rev-parse) [ "$4" = origin/main ] && echo {self.build} && exit;;
merge-base) [ "$6" = "{self.build}" ] && exit 0;;
archive) [ "$4" = "{self.build}" ] && exec /bin/cat '{archive_path}';;
esac
case " $* " in *" fetch "*|*" pull "*|*" push "*|*" clone "*) exit 98;; esac
exec /usr/bin/git "$@"
""")
        self.exe("gh", "#!/bin/sh\necho '[]'\n")
        self.exe("sf", f"""#!{sys.executable}
import json, os, signal, sys
from pathlib import Path
root = Path({str(self.root)!r})
if sys.argv[1:3] == ['project', 'generate'] and sys.argv[3:4] != ['manifest']:
    print('fixture: generated project')
    raise SystemExit(0)
options = sys.argv[1:]
if options in (['--version'], ['version'], ['--help'], ['sobject', 'list', '--help'],
               ['org', 'list', '--help']):
    with (root / 'global-cli.log').open('a') as handle:
        handle.write(json.dumps(options) + '\\n')
    raise SystemExit(0)
selector = os.environ.get('SF_TARGET_ORG')
for i, option in enumerate(options):
    flag, equals, value = option.partition('=')
    if flag in ('--target-org', '--o', '-o', '--from-org'):
        selector = value if equals else options[i + 1]
    elif option.startswith('-o'):
        selector = option[2:]
resolved = 'foreign@example.invalid' if selector == 'de' and (root / 'alias-drift').exists() else selector
with (root / 'remote.log').open('a') as handle:
    handle.write(json.dumps({{'argv': options, 'cwd': str(Path.cwd()), 'resolved': resolved,
                             'target_env': os.environ.get('SF_TARGET_ORG')}}) + '\\n')
if (root / 'lose-response').exists():
    os.kill(os.getppid(), signal.SIGKILL)
elif sys.argv[1:4] == ['project', 'deploy', 'start'] and (root / 'native-verification').exists():
    if (root / 'reconcile-deploy').exists():
        print(json.dumps({{'result': {{'status': 'Unknown'}}}}))
    else:
        print(json.dumps({{'result': {{'id': '0Af000000000001CAA',
            'done': True, 'status': 'Succeeded', 'success': True,
            'details': {{'componentSuccesses': [{{'componentType': 'ApexClass', 'fullName': 'OutcomeDemoTest',
                                               'success': True, 'deleted': False}}]}}}}}}))
else:
    print(json.dumps({{'result': {{'id':'0Af000000000001CAA'}}}}))
""")
        self.codex = self.exe("codex", f"""#!{sys.executable}
import hashlib, json, os, shlex, shutil, subprocess, sys
from pathlib import Path
root = Path({str(self.root)!r})
args = sys.argv[1:]
if args[:2] == ['plugin', 'marketplace']:
    raise SystemExit(0)
if args[:2] == ['plugin', 'add']:
    dst = Path(os.environ['CODEX_HOME']) / 'plugins/cache/whichguy/skill-craft/3.2.0'
    shutil.copytree({str(fixture)!r}, dst)
    if (root / 'stale-improve').exists():
        (dst / 'skills/improve/SKILL.md').write_text('stale')
    raise SystemExit(0)
if args[:2] == ['plugin', 'list']:
    print(json.dumps({{'installed': [{{'installed': True, 'name': 'skill-craft', 'version': '3.2.0'}}]}}))
    raise SystemExit(0)
if args == ['--version']:
    print('codex-cli fixture')
    raise SystemExit(0)
assert args[0] == 'exec', args
with (root / 'launches.jsonl').open('a') as handle:
    handle.write(json.dumps({{'argv': args, 'env': dict(os.environ), 'cwd': str(Path.cwd()),
                            'initial_files': sorted(os.listdir())}}) + '\\n')
# The hosted environment whitelist drops GIT_CONFIG_NOSYSTEM before exec.
# Skip system Git defaults in this fake host, preserving the harness's
# GIT_CONFIG_GLOBAL fixture identity and the workspace's local config.
os.environ['GIT_CONFIG_NOSYSTEM'] = '1'
login_shell = shutil.which('zsh') or shutil.which('bash')
if login_shell is None:
    raise SystemExit('Codex fixture requires an executable zsh or bash login shell')
shell = subprocess.run([login_shell, '-lc', 'command -v sf; command -v sfdx; command -v grok-chat-ui'],
                       capture_output=True, text=True)
(root / 'shell.txt').write_text(shell.stdout)
if (root / 'read-alias-drift').exists():
    (root / 'alias-drift').touch()
    guard = shell.stdout.splitlines()[0]
    commands = [
        ['sobject', 'list', '--target-org', 'de', '--json'],
        ['sobject', 'describe', '--sobject', 'Account', '-o=de'],
        ['data', 'query', '-q', 'SELECT Id FROM Account', '-ode'],
        ['data', 'get', 'record', '--sobject', 'Account', '--record-id', 'fixture'],
        ['org', 'list', 'metadata-types', '--target-org=de'],
        ['project', 'generate', 'manifest', '--from-org', 'de'],
        ['sobject', 'list', '--o', 'foreign@example.invalid'],
        ['sobject', 'list', '--target-org', 'de', '--o', 'foreign@example.invalid'],
        ['org', 'list', '--json'], ['org', 'list', '--skip-connection-status'],
        ['--version'], ['version'], ['--help'], ['sobject', 'list', '--help'], ['org', 'list', '--help'],
    ]
    results = [subprocess.run([guard, *words], capture_output=True, text=True) for words in commands]
    (root / 'read-results.json').write_text(json.dumps([[done.returncode, done.stderr] for done in results]))
if (root / 'test-deploy').exists():
    guard = Path(shell.stdout.splitlines()[0])
    initial = Path.cwd()
    product = initial
    def scaffold(path):
        path.mkdir(parents=True, exist_ok=True)
        (path / 'sfdx-project.json').write_text(json.dumps({{'packageDirectories':[{{'path':'force-app'}}]}}))
        classes = path / 'force-app/main/default/classes'
        classes.mkdir(parents=True)
        (classes / 'OutcomeDemo.cls').write_text('public class OutcomeDemo {{}}')
        if (root / 'native-verification').exists():
            (classes / 'OutcomeDemoTest.cls').write_text('@IsTest class OutcomeDemoTest {{ @IsTest static void check() {{}} }}')
            (classes / 'OutcomeDemoUndeployedTest.cls').write_text('@IsTest class OutcomeDemoUndeployedTest {{}}')
        for source in classes.glob('*.cls'):
            source.with_suffix('.cls-meta.xml').write_text('<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata"><apiVersion>65.0</apiVersion><status>Active</status></ApexClass>')
        if (root / 'member-check').exists():
            permsets = classes.parent / 'permissionsets'
            permsets.mkdir()
            (permsets / 'OutcomeDemoAccess.permissionset-meta.xml').write_text('<PermissionSet/>')
            obj = classes.parent / 'objects/OutcomeDemo__c'
            (obj / 'fields').mkdir(parents=True)
            (obj / 'OutcomeDemo__c.object-meta.xml').write_text('<CustomObject/>')
            (obj / 'fields/Review__c.field-meta.xml').write_text('<CustomField><fullName>Review__c</fullName></CustomField>')
    command = ['sf', 'project', 'deploy', 'start', '--source-dir', 'force-app', '--target-org', 'de', '--json']
    def sf(words, path=None):
        return subprocess.run([login_shell, '-lc', shlex.join(words)], cwd=path or product,
                              capture_output=True, text=True)
    assert sf(['sf', 'project', 'generate', '--name', 'fixture']).stdout.strip() == 'fixture: generated project'
    if (root / 'native-workspace').exists():
        src = Path(os.environ['CODEX_HOME']) / 'plugins/cache/whichguy/skill-craft/3.2.0'
        assert '$skill-craft:shiploop' in args[-1]
        init = subprocess.run([sys.executable, '-B', str(src / 'skills/shiploop/scripts/shiploop'),
                               'workspace', 'start', '--repo', str(initial), '--prompt', args[-1]],
                              capture_output=True, text=True)
        assert init.returncode == 0, (init.stdout, init.stderr)
        product, = (initial.parent / '.shiploop-runs').glob('work-*/worktree')
        assert str(src / 'skills/improve/SKILL.md') in (product.parent / 'run/state.md').read_text()
    denied = sf(command[:-2] + ['other', '--json'])
    assert denied.returncode == 2 and 'must be' in denied.stderr, denied
    denied = sf(['sf', 'apex', 'run', '--target-org', 'de'])
    assert denied.returncode == 2 and 'operator handles' in denied.stderr, denied
    scaffold(product)
    if (root / 'template-ignore').exists():
        template = Path({str(TEMPLATE_IGNORE)!r})
        ignore = product / '.forceignore'
        if template.is_file():
            shutil.copyfile(template, ignore)
        else:
            ignore.write_text('# Salesforce DX stock ignore rules\\n#\\n#\\n\\npackage.xml\\n**/jsconfig.json\\n'
                              '**/.eslintrc.json\\n**/__tests__/**\\nnode_modules/\\n')
        denied = sf(command)
        assert denied.returncode == 2 and '.forceignore:5' in denied.stderr and 'package.xml' in denied.stderr, denied
        assert not (root / 'remote.log').exists()
        ignore.unlink()
    denied = sf(command)
    assert denied.returncode == 2 and 'awaiting operator' in denied.stderr, denied
    assert not (root / 'remote.log').exists()
    state = guard.parent.parent
    intent, = state.glob('*.intent')
    assert json.loads(intent.read_bytes())['root'] == str(product)
    if product != initial:
        invalid_id = product.parent.parent / 'work-unexpected' / 'worktree'
        invalid_id.parent.mkdir()
        subprocess.run(['/usr/bin/git', '-C', str(initial), 'worktree', 'add', '--detach', str(invalid_id)],
                       check=True, capture_output=True)
        unlinked = product.parent.parent / 'work-20261114-161603-dead00' / 'worktree'
        for path in (root / 'outside', initial.parent / 'unexpected', initial / 'nested', unlinked, invalid_id):
            scaffold(path)
            denied = sf(command, path)
            assert denied.returncode == 2 and 'owned DX product workspace' in denied.stderr, (path, denied)
        alias = product.parent.parent / 'work-20261114-161603-dead01' / 'worktree'
        alias.parent.mkdir()
        alias.symlink_to(root / 'outside')
        denied = sf(command, alias)
        assert denied.returncode == 2 and 'owned DX product workspace' in denied.stderr, denied
        assert list(state.glob('*.intent')) == [intent]
    # Simulate the parent approving the requested exact source digest.
    key = hashlib.sha256(intent.read_bytes()).hexdigest()
    approved = intent.with_suffix('.approved')
    approved.write_text(json.dumps({{'intent_sha256':key,'approved':True}}))
    if (root / 'reject-incomplete').exists():
        denied = sf(command)
        assert denied.returncode == 2 and not (root / 'remote.log').exists(), denied
    reviewed = root / 'parent-review.txt'
    reviewed.write_text('offline fixture review of exact source and grants')
    decision = json.loads(intent.read_bytes())
    approved.unlink()
    apex_members = ['OutcomeDemo']
    if (root / 'native-verification').exists():
        apex_members.extend(['OutcomeDemoTest', 'OutcomeDemoUndeployedTest'])
    approval = {{'intent_sha256':key,'approved':True,
        **{{field:decision[field] for field in ('binding_sha256','force_app_sha256','project_sha256')}},
        'members':{{'ApexClass':apex_members}},
        'review_evidence':{{'path':str(reviewed),'sha256':hashlib.sha256(reviewed.read_bytes()).hexdigest()}}}}
    approved.write_text(json.dumps(approval))
    if (root / 'member-check').exists():
        approval['members']['CustomObject'] = ['OutcomeDemo__c']
        for reviewed_members in [
            {{'ApexClass': apex_members}},
            {{**approval['members'], 'CustomField': ['OutcomeDemo__c.Review__c']}},
            {{**approval['members'], 'PermissionSet': ['OutcomeDemoAccess']}},
            {{**approval['members'], 'PermissionSet': ['OutcomeDemoAccess'],
             'CustomField': ['OutcomeDemo__c.Review__c', 'OutcomeDemo__c.Unshipped__c']}},
        ]:
            approved.write_text(json.dumps({{**approval, 'members': reviewed_members}}))
            denied = sf(command)
            assert denied.returncode == 2 and 'metadata member map' in denied.stderr, denied
            assert not (root / 'remote.log').exists() and not list(state.glob('*.submitted'))
        approval['members'].update(PermissionSet=['OutcomeDemoAccess'], CustomField=['OutcomeDemo__c.Review__c'])
        approved.write_text(json.dumps(approval))
    if (root / 'leave-intent').exists():
        raise SystemExit(0)
    source = product / 'force-app/main/default/classes/OutcomeDemo.cls'
    original = source.read_bytes()
    source.write_bytes(original + b' ')
    assert 'awaiting operator' in sf(command).stderr
    source.write_bytes(original)
    native = ['sf', 'apex', 'run', 'test']
    named = ['--class-names', 'OutcomeDemoTest']
    sync = ['--synchronous']
    pin = ['--target-org', 'de', '--json']
    report = ['sf', 'project', 'deploy', 'report', '--job-id', '0Af000000000001CAA', *pin]
    if (root / 'native-verification').exists():
        denied = sf(native + named + sync + pin)
        assert denied.returncode == 2, denied  # approved, never deployed
        assert not (root / 'remote.log').exists()
    if (root / 'move-alias').exists():
        (root / 'alias-drift').touch()
    assert sf(command).returncode != 2
    assert 'already forwarded' in sf(command).stderr
    if (root / 'native-verification').exists():
        for bad in [
            native + named + pin,
            native + sync + pin,
            native + named + sync + ['--json'],
            native + named + sync + ['--target-org', 'other'],
            native + ['--class-names', 'ForeignTest'] + sync + pin,
            native + ['--class-names', 'OutcomeDemoUndeployedTest'] + sync + pin,
            native + named + ['OutcomeDemoSecondTest'] + sync + pin,
            native + named + ['--class-names', 'OutcomeDemoSecondTest'] + sync + pin,
            native + ['--class-names', 'OutcomeDemoTest,ForeignTest'] + sync + pin,
            native + ['--class-names', '01p000000000001'] + sync + pin,
            native + ['--tests', 'ForeignTest.check'] + sync + pin,
            native + ['--suite-names', 'AnySuite'] + sync + pin,
            native + named + sync + ['--test-level', 'RunLocalTests'] + pin,
            native + sync + ['--test-level', 'RunAllTestsInOrg'] + pin,
            report[:5] + ['0Af000000000002CAA', *pin],
            report[:5] + ['0Af000000000001AAA', *pin],
            report + ['--job-id', '0Af000000000002CAA'],
            ['sf', 'project', 'deploy', 'report', '--use-most-recent', *pin],
            ['sf', 'project', 'deploy', 'validate', '--source-dir', 'force-app', *pin],
            ['sf', 'project', 'deploy', 'cancel', '--job-id', '0Af000000000001CAA', *pin],
        ]:
            denied = sf(bad)
            assert denied.returncode == 2, (bad, denied)
        assert len((root / 'remote.log').read_text().splitlines()) == 1
        if (root / 'reconcile-deploy').exists():
            denied = sf(report)
            assert denied.returncode == 2, denied
            receipt = intent.with_suffix('.reconciled')
            reconciled = {{'phase': 'reconciliation', 'verified': True, 'disposition': 'REMOTE_ID',
                          'intent_sha256': key, 'binding_sha256': decision['binding_sha256'],
                          'target': decision['target'], 'remote_id': '0Af000000000001CAA',
                          'evidence': {{'path': str(reviewed), 'sha256': '0' * 64}}}}
            receipt.write_text(json.dumps(reconciled))
            assert sf(report).returncode == 2  # invalid independent evidence digest
            reconciled['evidence']['sha256'] = hashlib.sha256(reviewed.read_bytes()).hexdigest()
            receipt.write_text(json.dumps(reconciled))
            assert sf(native + named + sync + pin).returncode == 2  # ID recovery alone proves no deployed class
        else:
            source.write_bytes(original + b' ')
            assert sf(native + named + sync + pin).returncode == 2  # current source was never deployed
            source.write_bytes(original)
            tested = sf(native + ['-n', 'OutcomeDemoTest', *sync, *pin])
            assert tested.returncode == 0, tested
        cache = root / 'operator' / '.sf' / 'deploy-cache.json'
        cache.parent.mkdir()
        cache.write_text(json.dumps({{'0Af000000000001CAA': {{'target-org': 'other'}}}}))
        denied = sf(report)
        assert denied.returncode == 2 and 'cache points to a different' in denied.stderr, denied
        cache.write_text(json.dumps({{'0Af000000000001CAA': {{'target-org': 'de'}}}}))
        assert sf(report).returncode == 2
        cache.unlink()
        reported = sf(report)
        assert reported.returncode == 0, reported
    (root / 'deploy-checks-finished').touch()
""")
        self.path = self.make_binding("run")

    def exe(self, name, script):
        path = self.tools / name
        path.write_text(script)
        path.chmod(0o700)
        return path

    def make_binding(self, name, **updates):
        data = {"case": b.CASE, "run_kind": "create", "product_cwd": str(self.root / name / "work"),
                "target": {"org_id": "00Daj000018BzO3EAK", "user_id": "005aj00000eLa6HAAS",
                           "selector": "de", "username": "owner@example.invalid"},
                "namespace": "OutcomeDemo", "legacy_prefixes": ["SLGrokChat"],
                "provider": {"reference": "Example_Credential", "endpoint": "https://api.x.ai/v1/responses",
                             "model": "grok-7.1-fixture"}, "synthetic_label": "fixture only",
                "sf_bin": str(self.tools / "sf"), "tool_dirs": [str(self.tools)],
                "prompt_sha256": b.sha((SCENARIO / "BUILDER_PROMPT.md").read_bytes()),
                "source_readiness_sha256": b.sha((SCENARIO / "READINESS.json").read_bytes()), **updates}
        core = b.sha(b.encoded(data))
        data["receipts"] = {}
        for kind in ("authority", "retirement", "observer"):
            path = self.root / f"{name}-{kind}.json"
            path.write_bytes(b.encoded({"kind": kind, "status": "VERIFIED", "checked_at": time.time(),
                                        "identity_sha256": core, "internal_only": "operator-evaluator-detail"}))
            data["receipts"][kind] = {"path": str(path), "sha256": b.sha(path.read_bytes())}
        path = self.root / f"{name}.json"
        path.write_bytes(b.encoded(data))
        return path

    def receipt(self, context, phase, **fields):
        for key in attempt.lease_keys(b.decoded(self.path.read_bytes())):
            self.assertEqual(attempt.lifecycle.holder(key)["pid"], os.getpid())
        return {"verified": True, "phase": phase, "binding_sha256": context["binding_sha256"],
                "target": context["target"], "checked_at": time.time(), **fields}

    def invoke(self, *, path=None, cleanup=None, observe=None, **more):
        options = {"campaign": "campaign-a", "build": self.build, "codex_bin": self.codex, "model": "gpt-6.2-sol",
                   "baseline": self.root / "campaign.jsonl", "deadline": time.time() + 75,
                   "observation_seconds": 8, "teardown_seconds": 8,
                   "reset": lambda ctx, _: self.receipt(ctx, "reset", empty_noop=True),
                   "observe": observe, "cleanup": cleanup or (lambda ctx, _: self.receipt(ctx, "cleanup", reconciled_intents=[]))}
        return attempt.execute(path or self.path, **(options | more))

    def launches(self):
        return [json.loads(line) for line in (self.root / "launches.jsonl").read_text().splitlines()]

    def test_frozen_opening_and_guarded_shell_through_named_runner(self):
        result = self.invoke()
        state = Path(result["state_dir"])
        self.assertEqual(result["state"], "SETTLED", (state / "runner.log").read_text())
        launch, = self.launches()
        argv = launch["argv"]
        out = self.root / "run"
        frozen = (SCENARIO / "BUILDER_PROMPT.md").read_bytes()
        delivered = (out / "host-prompt.txt").read_bytes()
        self.assertEqual((out / "prompt.txt").read_bytes(), frozen)
        self.assertEqual(argv[-1].encode(), delivered)
        self.assertTrue(delivered.startswith(frozen))
        self.assertEqual(delivered.count(b"$skill-craft:shiploop"), 1)
        binding = delivered[len(frozen):]
        self.assertIn(b"Example_Credential", binding)
        self.assertIn(b"sf project deploy start --source-dir force-app --target-org de --json", binding)
        for hidden in ("operator-evaluator-detail", "reconciled_intents", "fixture-secret", "grok-chat-ui"):
            self.assertNotIn(hidden.encode(), delivered)
        for flag in ("agents.default_subagent_model=\"gpt-6.2-sol\"", "model_reasoning_effort=medium",
                     "agents.default_subagent_reasoning_effort=medium"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-6.2-sol")
        self.assertEqual(launch["cwd"], str(out / "work"))
        self.assertEqual(launch["initial_files"], [])
        self.assertFalse(set(launch["env"]) & {"E2E_CHECKS", "E2E_BIND_DEPLOY_SOURCE", "SF_ACCESS_TOKEN", attempt.ATTEMPT_ENV})
        self.assertEqual((self.root / "shell.txt").read_text().splitlines(), [str(state / "bin" / sf) for sf in ("sf", "sfdx")])
        invocation = json.loads((out / "invocation.json").read_bytes())
        self.assertEqual(invocation["original_prompt_sha256"], b.sha(frozen))
        self.assertEqual(invocation["environment_binding_sha256"], b.sha(self.path.read_bytes()))
        self.assertEqual(invocation["delivered_opening_sha256"], b.sha(delivered))
        self.assertEqual(invocation["checks"], [])
        runner_result = attempt.read(out / "result.json")
        self.assertIsNone(runner_result["pass"])
        self.assertEqual(runner_result["product_acceptance"], "UNKNOWN")
        self.assertEqual(result["product_acceptance"], "UNKNOWN")
        self.assertEqual(result, self.invoke())
        self.assertEqual(len(self.launches()), 1)

    def test_missing_mismatched_and_nonfinite_bindings_refuse_before_output(self):
        def refuse(path=None):
            cmd = [sys.executable, "-B", str(HARNESS / "run.py"), "--case", b.CASE, "--host", "codex",
                   "--output", str(self.root / "run")]
            if path:
                cmd += ["--environment-binding", str(path)]
            done = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(done.returncode, 0, done.stdout)
            self.assertFalse((self.root / "run").exists())
            self.assertFalse((self.root / "launches.jsonl").exists())
            return done.stderr

        self.assertIn("BLOCKED", refuse())
        self.assertIn("canonical absolute path", refuse(self.path))  # no outer attempt
        data = b.decoded(self.path.read_bytes())
        data["target"]["selector"] = "other"
        self.path.write_bytes(b.encoded(data))
        self.assertIn("does not verify this binding", refuse(self.path))
        self.path.write_bytes(b'{"number":1e999}')
        self.assertIn("finite", refuse(self.path))

    def test_lost_remote_response_and_missing_cleanup_block_reuse(self):
        (self.root / "test-deploy").touch()
        (self.root / "lose-response").touch()
        (self.root / "unrelated").write_text("preserve")
        result = self.invoke(cleanup=lambda *_: None)
        state = Path(result["state_dir"])
        self.assertTrue((self.root / "deploy-checks-finished").exists(), (state / "runner.log").read_text())
        sent, = state.glob("*.submitted")
        self.assertTrue(Path(attempt.read(sent)["payload"]).is_dir())
        self.assertFalse(list(state.glob("*.returned")))
        self.assertEqual(len((self.root / "remote.log").read_text().splitlines()), 1)
        self.assertEqual(result["state"], "RECONCILIATION_REQUIRED")
        self.assertEqual(self.invoke(), result)
        with self.assertRaisesRegex(ValueError, "prior hosted attempt needs verified cleanup"):
            self.invoke(path=self.make_binding("next"), campaign="campaign-b")
        self.assertFalse((self.root / "next").exists())
        self.assertEqual((self.root / "unrelated").read_text(), "preserve")
        self.assertEqual(len(self.launches()), 1)
        with self.assertRaisesRegex(ValueError, "has not reconciled every submitted"):
            attempt.reconcile(self.path, state, deadline=time.time() + 8,
                              cleanup=lambda ctx, _: self.receipt(ctx, "cleanup", reconciled_intents=[]))
        def cleanup(context, _):
            self.assertIs(context["local_processes_clear"], True)
            return self.receipt(context, "cleanup", reconciled_intents=[sent.stem])

        reconciled = attempt.reconcile(self.path, state, deadline=time.time() + 8, cleanup=cleanup)
        self.assertEqual(reconciled["state"], "SETTLED")
        self.assertEqual(self.invoke(), reconciled)
        self.assertEqual(len(self.launches()), 1)

    def test_remote_id_and_observation_precede_verified_cleanup(self):
        (self.root / "test-deploy").touch()
        (self.root / "native-workspace").touch()
        phases = []

        def observe(context, _):
            phases.append("observe")
            returned, = Path(context["state_dir"]).glob("*.returned")
            self.assertEqual(attempt.read(returned)["remote_id"], "0Af000000000001CAA")
            return {"observed": "fixture receipt"}

        def cleanup(context, _):
            phases.append("cleanup")
            self.assertIs(context["local_processes_clear"], True)
            return self.receipt(context, "cleanup", reconciled_intents=sorted(attempt.submitted(Path(context["state_dir"]))))

        result = self.invoke(observe=observe, cleanup=cleanup)
        state = Path(result["state_dir"])
        diagnostics = (state / "runner.log").read_text() + "\n" + "\n".join(
            p.read_text() for p in (self.root / "run").glob("*stderr*") if p.is_file())
        self.assertTrue((self.root / "deploy-checks-finished").exists(), diagnostics)
        self.assertEqual(phases, ["observe", "cleanup"], (state / "runner.log").read_text())
        self.assertEqual(result["state"], "SETTLED")
        sent, = state.glob("*.submitted")
        remote = json.loads((self.root / "remote.log").read_bytes())
        self.assertEqual(remote["cwd"], attempt.read(sent)["payload"])
        self.assertEqual(Path(remote["cwd"]).parent, state)
        self.assertEqual(result["observations"], {"observed": "fixture receipt"})
        self.assertEqual(result["product_acceptance"], "UNKNOWN")

    def test_two_field_approval_has_no_forwards(self):
        for name in ("test-deploy", "reject-incomplete"):
            (self.root / name).touch()
        result = self.invoke()
        state = Path(result["state_dir"])
        self.assertTrue((self.root / "deploy-checks-finished").exists(),
                        (state / "runner.log").read_text())
        self.assertEqual(len((self.root / "remote.log").read_text().splitlines()), 1)

    def test_approval_members_must_match_complete_snapshot(self):
        for name in ("test-deploy", "member-check"):
            (self.root / name).touch()
        result = self.invoke()
        state = Path(result["state_dir"])
        self.assertTrue((self.root / "deploy-checks-finished").exists(),
                        (self.root / "run/stderr.txt").read_text())
        self.assertEqual(len((self.root / "remote.log").read_text().splitlines()), 1)
        self.assertEqual(len(list(state.glob("*.submitted"))), 1)

    def test_alias_drift_cannot_retarget_deploy_after_reset(self):
        for name in ("test-deploy", "move-alias"):
            (self.root / name).touch()
        result = self.invoke()
        state = Path(result["state_dir"])
        sent, = state.glob("*.submitted")
        remote = json.loads((self.root / "remote.log").read_text())
        self.assertEqual(remote["resolved"], "owner@example.invalid")
        self.assertEqual(remote["target_env"], "owner@example.invalid")
        self.assertEqual(attempt.read(sent)["forward_target"],
                         {"requested": "de", "effective": "owner@example.invalid"})

    def test_alias_drift_cannot_retarget_hosted_reads(self):
        (self.root / "read-alias-drift").touch()
        result = self.invoke()
        state = Path(result["state_dir"])
        calls = [json.loads(line) for line in (self.root / "remote.log").read_text().splitlines()]
        self.assertEqual([call["resolved"] for call in calls], ["owner@example.invalid"] * 6, calls)
        self.assertEqual([call["target_env"] for call in calls], ["owner@example.invalid"] * 6)
        self.assertEqual([call["argv"] for call in calls], [
            ["sobject", "list", "--target-org", "owner@example.invalid", "--json"],
            ["sobject", "describe", "--sobject", "Account", "--target-org", "owner@example.invalid"],
            ["data", "query", "-q", "SELECT Id FROM Account", "--target-org", "owner@example.invalid"],
            ["data", "get", "record", "--sobject", "Account", "--record-id", "fixture"],
            ["org", "list", "metadata-types", "--target-org", "owner@example.invalid"],
            ["project", "generate", "manifest", "--from-org", "owner@example.invalid"],
        ])
        results = json.loads((self.root / "read-results.json").read_text())
        self.assertEqual([code for code, _ in results], [0] * 6 + [2] * 4 + [0] * 5, results)
        local = [json.loads(line) for line in (self.root / "global-cli.log").read_text().splitlines()]
        self.assertEqual(local, [["--version"], ["version"], ["--help"], ["sobject", "list", "--help"],
                                 ["org", "list", "--help"]])
        decisions = [json.loads(line) for line in (state / "sf-calls.jsonl").read_text().splitlines()]
        self.assertEqual([row["forward_target"] for row in decisions if "forward_target" in row], [
            {"requested": target, "effective": "owner@example.invalid"}
            for target in ("de", "de", "de", None, "de", "de")
        ])

    def test_reconcile_uses_cleanup_cutoff_after_original_deadline(self):
        (self.root / "test-deploy").touch()
        (self.root / "lose-response").touch()
        result = self.invoke(cleanup=lambda *_: None)
        state = Path(result["state_dir"])
        original = attempt.read(state / "start.json")
        submitted, = state.glob("*.submitted")
        raw = submitted.read_bytes()
        self.assertFalse(list(state.glob("*.returned")))
        at = original["deadline"] + 1
        cutoff = at + 8
        seen = []

        def cleanup(context, received_cutoff):
            self.assertEqual(context["deadline"], original["deadline"])
            self.assertEqual(context["build_until"], original["build_until"])
            self.assertEqual(received_cutoff, cutoff)
            self.assertTrue(context["local_processes_clear"])
            seen.append(received_cutoff)
            return self.receipt(context, "cleanup", reconciled_intents=[submitted.stem])

        with patch.object(attempt.time, "time", return_value=at):
            with self.assertRaises(TimeoutError):
                attempt.reconcile(self.path, state, deadline=at - 1, cleanup=cleanup)
            reconciled = attempt.reconcile(self.path, state, deadline=cutoff, cleanup=cleanup)
            self.assertEqual(attempt.reconcile(self.path, state, deadline=cutoff, cleanup=cleanup), reconciled)
        self.assertEqual(seen, [cutoff])
        self.assertEqual(reconciled["state"], "SETTLED")
        self.assertEqual(submitted.read_bytes(), raw)
        self.assertEqual(list(state.glob("*.submitted")), [submitted])
        self.assertEqual(len(self.launches()), 1)
        self.assertEqual(len((self.root / "remote.log").read_text().splitlines()), 1)

    def assert_native_verification_forwards(self, expected):
        for name in ("test-deploy", "native-workspace", "native-verification"):
            (self.root / name).touch()
        result = self.invoke(cleanup=lambda ctx, _: self.receipt(
            ctx, "cleanup", reconciled_intents=sorted(attempt.submitted(Path(ctx["state_dir"])))))
        state = Path(result["state_dir"])
        diagnostics = (state / "runner.log").read_text() + "\n" + "\n".join(
            p.read_text() for p in (self.root / "run").glob("*stderr*") if p.is_file())
        self.assertTrue((self.root / "deploy-checks-finished").exists(), diagnostics)
        self.assertEqual(result["state"], "SETTLED")
        calls = [json.loads(line)["argv"] for line in (self.root / "remote.log").read_text().splitlines()]
        self.assertEqual(calls, [["project", "deploy", "start", "--source-dir", "force-app",
                                  "--target-org", "owner@example.invalid", "--json"], *expected])
        self.assertEqual(len(list(state.glob("*.submitted"))), 1)
        self.assertEqual(len(list(state.glob("*.returned"))), 1)

    def test_owned_synchronous_apex_and_recorded_deploy_report(self):
        self.assert_native_verification_forwards([
            ["apex", "run", "test", "-n", "OutcomeDemoTest", "--synchronous", "--target-org", "owner@example.invalid", "--json"],
            ["project", "deploy", "report", "--job-id", "0Af000000000001CAA", "--target-org", "owner@example.invalid", "--json"],
        ])

    def test_report_accepts_independently_reconciled_id_without_authorizing_apex(self):
        (self.root / "reconcile-deploy").touch()
        self.assert_native_verification_forwards([
            ["project", "deploy", "report", "--job-id", "0Af000000000001CAA", "--target-org", "owner@example.invalid", "--json"],
        ])

    def test_stock_forceignore_has_precise_diagnostic(self):
        for name in ("test-deploy", "native-workspace", "template-ignore", "leave-intent"):
            (self.root / name).touch()
        result = self.invoke()
        state = Path(result["state_dir"])
        self.assertTrue(list(state.glob("*.approved")), (state / "runner.log").read_text())
        self.assertFalse((self.root / "remote.log").exists())

    def test_retained_wrapper_refuses_approved_intent_after_early_finish(self):
        for name in ("test-deploy", "leave-intent"):
            (self.root / name).touch()
        def retained_wrapper(state):
            self.assertTrue(list(state.glob("*.approved")), (state / "runner.log").read_text())
            self.assertGreater(attempt.read(state / "start.json")["build_until"], time.time())
            done = subprocess.run([str(state / "bin/sf"), "project", "deploy", "start", "--source-dir",
                                   "force-app", "--target-org", "de", "--json"],
                                  cwd=self.root / "run/work", capture_output=True, text=True)
            self.assertEqual(done.returncode, 2, done)
            self.assertIn("build phase", done.stderr)

        def observe(context, _):
            retained_wrapper(Path(context["state_dir"]))
            return {"retained_wrapper_refused": True}

        result = self.invoke(observe=observe)
        self.assertEqual(result["observations"], {"retained_wrapper_refused": True}, result)
        retained_wrapper(Path(result["state_dir"]))
        self.assertFalse((self.root / "remote.log").exists())
        self.assertEqual(len(self.launches()), 1)

    def test_late_submission_invalidates_settled_replay(self):
        first = self.invoke()
        self.assertEqual(first["state"], "SETTLED")
        state = Path(first["state_dir"])
        late = state / ("a" * 64 + ".submitted")
        late.write_text("{}")
        self.assertEqual(self.invoke()["state"], "RECONCILIATION_REQUIRED")
        self.assertEqual(attempt.read(state / "settled.json"), first)
        self.assertEqual(len(self.launches()), 1)
        with self.assertRaisesRegex(ValueError, "has not reconciled every submitted"):
            attempt.reconcile(self.path, state, deadline=time.time() + 8,
                              cleanup=lambda ctx, _: self.receipt(ctx, "cleanup", reconciled_intents=[]))
        replay = attempt.reconcile(self.path, state, deadline=time.time() + 8,
                                   cleanup=lambda ctx, _: self.receipt(ctx, "cleanup", reconciled_intents=[late.stem]))
        self.assertEqual(self.invoke(), replay)
        previous_reconciliation = (state / "reconciled.json").read_bytes()
        extra = state / ("b" * 64 + ".submitted")
        extra.write_text("{}")
        self.assertEqual(self.invoke()["state"], "RECONCILIATION_REQUIRED")
        replay = attempt.reconcile(self.path, state, deadline=time.time() + 8,
                                   cleanup=lambda ctx, _: self.receipt(ctx, "cleanup",
                                                                       reconciled_intents=[late.stem, extra.stem]))
        self.assertEqual(self.invoke(), replay)
        self.assertEqual((state / "reconciled.json").read_bytes(), previous_reconciliation)
        self.assertEqual(len(self.launches()), 1)

    def test_runner_exit_with_real_same_group_child(self):
        child_pid = self.root / "child.pid"
        finish = self.root / "finish-child"
        fixture = self.root / "local-runner"
        fixture.mkdir()
        child = ("import sys,time; from pathlib import Path; "
                 "release=Path(sys.argv[1]); deadline=time.monotonic()+20; "
                 "exec('while not release.exists() and time.monotonic()<deadline: time.sleep(.02)')")
        (fixture / "run.py").write_text(
            "import json,os,subprocess,sys\nfrom pathlib import Path\n"
            f"child=subprocess.Popen([sys.executable,'-c',{child!r},{str(finish)!r}])\n"
            f"Path({str(child_pid)!r}).write_text(json.dumps([child.pid, os.getpgid(child.pid)]))\n")
        sentinel = subprocess.Popen([sys.executable, "-c", child, str(self.root / "finish-sentinel")],
                                    start_new_session=True)
        self.addCleanup(sentinel.wait, timeout=5)
        self.addCleanup((self.root / "finish-sentinel").touch)
        sentinel_identity = attempt.lifecycle.table([sentinel.pid])[sentinel.pid]
        real_builder = attempt.builder

        def run_local(argv, env, log, cutoff, state):
            with patch.object(b, "HERE", fixture):
                return real_builder(argv, env, log, cutoff, state)

        def observe_child(context):
            rows = attempt.lifecycle.table()
            pid, pgid = json.loads(child_pid.read_text())
            state = Path(context["state_dir"])
            runner, = [row for row in attempt.lifecycle.rows(state) if row.get("role") == "hosted-runner"
                       and row["kind"] == "group"]
            self.assertEqual(runner["pgid"], pgid)
            self.assertNotEqual(runner["pgid"], sentinel.pid)
            self.assertTrue(attempt.lifecycle.same_leader(sentinel_identity, rows.get(sentinel.pid)))
            return pid in rows

        seen = []
        def cleanup(context, _):
            seen.append((context["local_processes_clear"], observe_child(context)))
            return self.receipt(context, "cleanup", reconciled_intents=[])

        try:
            with patch.object(attempt, "builder", run_local):
                result = self.invoke(cleanup=cleanup)
            if result["local_processes_clear"]:
                self.assertEqual(seen, [(True, False)], result)
            else:
                observe_child(result)
                self.assertEqual(seen, [], result)
        finally:
            finish.touch()
            if child_pid.exists():
                pid, _ = json.loads(child_pid.read_text())
                until = time.monotonic() + 5
                while pid in attempt.lifecycle.table([pid]) and time.monotonic() < until:
                    time.sleep(.02)
                self.assertNotIn(pid, attempt.lifecycle.table([pid]))
            self.assertIsNone(sentinel.poll())
    def test_separate_session_crash_before_durable_host_registration(self):
        fixture = self.root / "runner-fixture"
        fixture.mkdir()
        child_record = self.root / "blocked-child.json"
        (fixture / "run.py").write_text(f"""
import json, os, signal, sys, time
from pathlib import Path
sys.path.insert(0, {str(HARNESS)!r})
import lifecycle, run
original = lifecycle.own
def crash_before_registration(out, pid, role, **kwargs):
    if role != "host":
        return original(out, pid, role, **kwargs)
    # Give the child time to reach its startup wait, then keep that session
    # alive across the runner death. The old host escapes and executes here.
    time.sleep(.3)
    os.kill(pid, signal.SIGSTOP)
    identity = lifecycle.table([pid])[pid]
    Path({str(child_record)!r}).write_text(json.dumps(identity))
    os._exit(93)
lifecycle.own = crash_before_registration
run.keep_awake = lambda argv: argv
raise SystemExit(run.main())
""")
        with self.codex.open("a") as script:
            script.write("\nimport time\ntime.sleep(30)\n")
        sentinel = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(40)"], start_new_session=True)
        self.addCleanup(sentinel.wait, timeout=5)
        self.addCleanup(sentinel.terminate)
        real_builder = attempt.builder

        def run_local(argv, env, log, cutoff, state):
            with patch.object(b, "HERE", fixture):
                return real_builder(argv, env, log, cutoff, state)

        destructive = []

        def cleanup(context, _):
            destructive.append(context["local_processes_clear"])
            return self.receipt(context, "cleanup", reconciled_intents=[])

        try:
            with patch.object(attempt, "builder", run_local):
                result = self.invoke(cleanup=cleanup)
            identity = attempt.read(child_record)
            pid = identity["pid"]
            self.assertEqual(identity["pgid"], pid)
            self.assertTrue(attempt.lifecycle.same_leader(identity, attempt.lifecycle.table([pid]).get(pid)))
            self.assertIs(result["local_processes_clear"], False)
            self.assertEqual(destructive, [])
            self.assertFalse((self.root / "launches.jsonl").exists())
            state = Path(result["state_dir"])
            with self.assertRaisesRegex(ValueError, "attempt process cleanup remains unverified"):
                attempt.reconcile(self.path, state, deadline=time.time() + 8, cleanup=cleanup)
            self.assertEqual(destructive, [])
            self.assertIsNone(sentinel.poll())
            os.kill(pid, signal.SIGCONT)
            until = time.monotonic() + 5
            while pid in attempt.lifecycle.table([pid]) and time.monotonic() < until:
                time.sleep(.02)
            self.assertNotIn(pid, attempt.lifecycle.table([pid]))
            self.assertFalse((self.root / "launches.jsonl").exists())
            self.assertEqual(attempt.reconcile(self.path, state, deadline=time.time() + 8, cleanup=cleanup)["state"],
                             "SETTLED")
            self.assertEqual(destructive, [True])
        finally:
            if child_record.is_file():
                identity = attempt.read(child_record)
                pid = identity["pid"]
                if attempt.lifecycle.same_leader(identity, attempt.lifecycle.table([pid]).get(pid)):
                    os.kill(pid, signal.SIGKILL)
                    until = time.monotonic() + 5
                    while pid in attempt.lifecycle.table([pid]) and time.monotonic() < until:
                        time.sleep(.02)
                    self.assertNotIn(pid, attempt.lifecycle.table([pid]))
            self.assertIsNone(sentinel.poll())

    def test_missing_reset_after_possible_launch_stays_unknown(self):
        result = self.invoke(cleanup=lambda *_: None)
        state = Path(result["state_dir"])
        (state / "reset.json").unlink()  # model missing evidence after an otherwise recorded launch
        called = []
        with self.assertRaisesRegex(ValueError, "missing reset proof after possible launch"):
            attempt.reconcile(self.path, state, deadline=time.time() + 8, cleanup=lambda *_: called.append(True))
        self.assertFalse(called)
        self.assertEqual(self.invoke()["state"], "RECONCILIATION_REQUIRED")
        self.assertEqual(len(self.launches()), 1)

    def test_reconcile_requires_readable_process_ledgers(self):
        result = self.invoke(cleanup=lambda *_: None)
        state = Path(result["state_dir"])
        invoked = []
        for folder in (state, self.root / "run"):
            with self.subTest(folder=folder):
                path = folder / attempt.lifecycle.LEDGER
                saved = path.with_suffix(".saved")
                path.rename(saved)
                try:
                    for contents in (None, b'{"kind": "group"'):
                        if contents is not None:
                            path.write_bytes(contents)
                        with self.assertRaisesRegex(ValueError, "attempt process cleanup remains unverified"):
                            attempt.reconcile(self.path, state, deadline=time.time() + 8,
                                              cleanup=lambda *_: invoked.append(True))
                finally:
                    saved.replace(path)
        self.assertEqual(invoked, [])
        result = attempt.reconcile(self.path, state, deadline=time.time() + 8,
                                   cleanup=lambda ctx, _: self.receipt(ctx, "cleanup", reconciled_intents=[]))
        self.assertEqual(result["state"], "SETTLED")

    def test_failed_full_process_scan_cannot_authorize_reconcile_cleanup(self):
        lifecycle = attempt.lifecycle
        with patch.object(attempt, "local_clear", return_value=False):
            result = self.invoke(cleanup=lambda *_: self.fail("initial cleanup was called"))
        state = Path(result["state_dir"])
        self.assertIs(result["local_processes_clear"], False)
        self.assertTrue(any(row["role"] == "hosted-runner" and row["leader"]
                            for row in lifecycle.open_groups(state)))
        complete_row = "1 0 1 Wed Nov 18 07:00:00 2026 init\n"
        failures = [(1, "", ""), (0, "", ""), (0, complete_row.rstrip("\n"), ""),
                    (0, complete_row + "123 1\n", ""), (0, complete_row, "ps: incomplete inventory\n"),
                    (0, complete_row, "")]
        for code, stdout, stderr in failures:
            with self.subTest(code=code, stdout=stdout, stderr=stderr):
                def full_inventory(argv, **kwargs):
                    self.assertEqual(argv[0], "ps")
                    self.assertEqual(argv[-1], "-ax")
                    return subprocess.CompletedProcess(argv, code, stdout, stderr)

                with (patch.object(lifecycle.subprocess, "run", side_effect=full_inventory) as scan,
                      patch.object(lifecycle, "_signal_group") as signal_group):
                    with self.assertRaisesRegex((ValueError, lifecycle.listeners.Unobserved),
                                                "ps |process cleanup remains unverified"):
                        attempt.reconcile(self.path, state, deadline=time.time() + 8,
                                          cleanup=lambda *_: self.fail("destructive cleanup callback was called"))
                scan.assert_called()
                signal_group.assert_not_called()
                self.assertIs(attempt.settlement(state)["local_processes_clear"], False)
                self.assertFalse((state / "reconciled.json").exists())
                self.assertTrue(lifecycle.open_groups(state))

        with patch.object(lifecycle.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "")) as scan:
            self.assertEqual(lifecycle.table([os.getpid()]), {})
        self.assertEqual(scan.call_args.args[0][-2:], ["-p", str(os.getpid())])

    def test_full_scan_omitting_live_registered_group_blocks_cleanup_and_recovers(self):
        lifecycle = attempt.lifecycle
        real_run, real_killpg = subprocess.run, os.killpg
        launches, destructive, probes, stops = [], [], [], []
        output = self.root / "run"
        caller = lifecycle.table([os.getpid()])[os.getpid()]
        caller_line = f"{caller['pid']} {caller['ppid']} {caller['pgid']} {caller['started']} caller\n"

        def omit_child(argv, **kwargs):
            if argv[0] == "ps" and argv[-1] == "-ax":
                return subprocess.CompletedProcess(argv, 0, caller_line, "")
            return real_run(argv, **kwargs)

        def launch(argv, env, log, cutoff, state):
            output.mkdir()
            process, group = lifecycle.spawn_registered(
                state, "hosted-runner",
                [sys.executable, "-B", "-c", "import sys; print('ready', flush=True); sys.stdin.buffer.read()"],
                mirror=output, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            launches.append((process, group))
            self.assertEqual(process.stdout.readline(), b"ready\n")
            return 0

        def kernel_probe(pgid, number):
            if number:
                stops.append((pgid, number))
                self.fail("omitted group received a stop signal")
            probes.append(pgid)
            return real_killpg(pgid, number)

        def cleanup(context, _):
            destructive.append(context["local_processes_clear"])
            if process.poll() is None:
                self.fail("destructive cleanup callback was called while the owned group was alive")
            return self.receipt(context, "cleanup", reconciled_intents=[])

        def reconcile():
            return attempt.reconcile(self.path, state, deadline=time.time() + 8, cleanup=cleanup)

        def assert_reconcile_blocked():
            with self.assertRaisesRegex(ValueError, "attempt process cleanup remains unverified"):
                reconcile()
            self.assertEqual(destructive, [])
            self.assertFalse((state / "reconciled.json").exists())

        try:
            with (patch.object(attempt, "builder", side_effect=launch),
                  patch.object(subprocess, "run", side_effect=omit_child),
                  patch.object(os, "killpg", side_effect=kernel_probe)):
                result = self.invoke(cleanup=lambda ctx, _: destructive.append(ctx["local_processes_clear"]))
                state = Path(result["state_dir"])
                (process, group), = launches
                self.assertEqual(os.getpgid(process.pid), process.pid)
                with self.subTest(phase="normal settlement"):
                    self.assertIs(result["local_processes_clear"], False)
                    self.assertEqual(destructive, [])
                    self.assertIn(group, lifecycle.open_groups(state))
                with self.subTest(phase="reconciliation"):
                    assert_reconcile_blocked()
                    self.assertIn(group, lifecycle.open_groups(state))
                    self.assertIn(process.pid, probes)
                ledgers = {folder / lifecycle.LEDGER: (folder / lifecycle.LEDGER).read_bytes()
                           for folder in (state, output)}
                try:
                    lifecycle.ended(state, group, "gone")  # simulate a prior false end record
                    with self.subTest(phase="open output ledger"):
                        assert_reconcile_blocked()
                        self.assertIn(group["id"], {row["id"] for row in lifecycle.open_groups(output)})
                    lifecycle.ended(output, group, "gone")
                    with self.subTest(phase="final scan of ended records"):
                        assert_reconcile_blocked()
                finally:
                    for ledger, content in ledgers.items():
                        ledger.write_bytes(content)
        finally:
            for process, _ in launches:
                process.stdin.close()
                process.wait(timeout=5)
                process.stdout.close()

        with (patch.object(attempt, "builder") as builder,
              patch.object(os, "killpg", side_effect=PermissionError) as denied):
            assert_reconcile_blocked()
            denied.assert_called_once_with(process.pid, 0)
            self.assertIn(group, lifecycle.open_groups(state))
            builder.assert_not_called()

        with (patch.object(attempt, "builder") as builder,
              patch.object(os, "killpg", side_effect=kernel_probe)):
            with self.assertRaises(ProcessLookupError):
                real_killpg(process.pid, 0)
            settled = reconcile()
            self.assertEqual(settled["state"], "SETTLED")
            self.assertEqual(reconcile(), settled)
            builder.assert_not_called()
        self.assertEqual(lifecycle.open_groups(state), [])
        self.assertEqual(lifecycle.open_groups(output), [])
        self.assertEqual(stops, [])
        self.assertEqual(destructive, [True])
        self.assertEqual(len(launches), 1)
        self.assertEqual(attempt.submitted(state), set())
        self.assertFalse((self.root / "launches.jsonl").exists())

    def test_unverified_local_stop_cannot_invoke_cleanup(self):
        seen = []

        def cleanup(context, _):
            seen.append(context["local_processes_clear"])
            return self.receipt(context, "cleanup", reconciled_intents=[])

        with patch.object(attempt, "local_clear", return_value=False):
            result = self.invoke(cleanup=cleanup)
        self.assertEqual(seen, [])
        self.assertIs(result["local_processes_clear"], False)
        self.assertEqual(result["state"], "RECONCILIATION_REQUIRED")
        self.assertEqual(result["product_acceptance"], "UNKNOWN")
        self.assertNotIn("cleanup", result)
        self.assertEqual(self.invoke(), result)
        self.assertEqual(len(self.launches()), 1)
        with patch.object(attempt, "local_clear", return_value=False):
            with self.assertRaisesRegex(ValueError, "process cleanup remains unverified"):
                attempt.reconcile(self.path, Path(result["state_dir"]), deadline=time.time() + 8, cleanup=cleanup)
        self.assertEqual(seen, [])

    def test_wrong_leased_target_and_stale_improve_refuse_builder(self):
        def wrong(context, _):
            return self.receipt(context, "reset", target={**context["target"], "selector": "wrong"}, empty_noop=True)

        rejected = self.invoke(reset=wrong)
        self.assertEqual(rejected["build_error"], "ValueError")
        self.assertFalse((self.root / "run").exists())
        attempt.reconcile(self.path, Path(rejected["state_dir"]), deadline=time.time() + 8,
                          cleanup=lambda ctx, _: self.receipt(ctx, "cleanup", reconciled_intents=[],
                                                              prelaunch_noop=True, empty_noop=True))
        (self.root / "stale-improve").touch()
        result = self.invoke(path=self.make_binding("stale"), campaign="stale")
        self.assertNotEqual(result["runner_exit"], 0)
        self.assertFalse((self.root / "launches.jsonl").exists())
        stub = attempt.read(self.root / "stale/result.json")
        self.assertIn("installed improve bytes differ from current publication", stub["versions"]["gate"])

    def test_phase_deadline_and_start_record_without_settlement(self):
        def stall(*_):
            time.sleep(15)

        result = self.invoke(deadline=time.time() + 2, observation_seconds=.5, teardown_seconds=.5,
                             reset=stall, cleanup=lambda *_: None)
        self.assertEqual(result["build_error"], "TimeoutError")
        self.assertFalse((self.root / "run").exists())
        state = Path(result["state_dir"])
        (state / "settled.json").unlink()  # simulate a restart after the attempt process disappeared
        self.assertEqual(self.invoke()["state"], "RECONCILIATION_REQUIRED")
        self.assertFalse((self.root / "launches.jsonl").exists())


def load_tests(loader, tests, pattern):
    tests.addTests(loader.loadTestsFromTestCase(operator_fixtures.OperatorFixtures))
    tests.addTests(loader.loadTestsFromTestCase(operator_fixtures.RetentionFixtures))
    return tests


if __name__ == "__main__":
    unittest.main()
