"""Post-exit acceptance and immutable-attempt negative controls, no model calls."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import controller


class ControllerControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.run=Path(self.temp.name);self.op=self.run/'operator';self.op.mkdir()
        self.write('process-result.json',{'exit_code':0})
        (self.op/'parent-prompt.txt').write_text('fixed prompt')
        (self.op/'fixture.py').write_text('# fixed verifier')
        self.write('launch.json',{'prompt_sha256':hashlib.sha256(b'fixed prompt').hexdigest(),
                                'apparatus_sha256':{'fixture.py':hashlib.sha256(b'# fixed verifier').hexdigest()}})

    def write(self,name,data):
        (self.op/name).write_text(json.dumps(data))

    def verifier(self,*args,**kwargs):
        self.write('verification.json',{'passed':True})
        return subprocess.CompletedProcess(args[0],0,'verified','')

    def test_live_launcher_retains_normal_permissions_and_exact_invocation(self):
        # Exercise the launch boundary without a model or permission-setting mutation.
        (self.op/'launch.json').unlink()
        (self.run/'caller').mkdir()
        (self.run/'manifest.json').write_text('{}\n')
        binary = self.run/'fake grok'
        binary.write_text('offline executable fixture\n')
        process = Mock(pid=12345, stdout=iter(()))
        process.wait.return_value = 0

        def metadata(argv, **kwargs):
            output = 'offline-version' if '--version' in argv else '{}'
            return subprocess.CompletedProcess(argv, 0, output, '')

        with patch('controller.subprocess.run', side_effect=metadata), \
                patch('controller.subprocess.Popen', return_value=process) as spawn, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(controller.launch(self.run, str(binary)), 0)
        launch = json.loads((self.op/'launch.json').read_text())
        argv = spawn.call_args.args[0]
        self.assertEqual(argv, launch['argv'])
        self.assertEqual(argv[argv.index('--permission-mode') + 1], 'default')
        self.assertNotIn('--always-approve', argv)
        self.assertNotIn('bypassPermissions', argv)
        self.assertNotIn('--resume', argv)
        self.assertEqual(argv[argv.index('--prompt-file') + 1], str((self.op/'parent-prompt.txt').resolve()))
        self.assertEqual(spawn.call_args.kwargs['cwd'], (self.run/'caller').resolve())
        self.assertEqual(launch['pid'], process.pid)
        self.assertEqual(json.loads((self.op/'process-result.json').read_text())['exit_code'], 0)

    def test_failed_parent_cannot_pass_file_verification(self):
        self.write('process-result.json',{'exit_code':1})
        with patch('controller.subprocess.run',side_effect=self.verifier),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(controller.verify_after_exit(self.run),1)
        result=json.loads((self.op/'post-exit-result.json').read_text())
        self.assertFalse(result['passed']);self.assertTrue(result['filesystem_passed'])

    def test_integrity_failure_is_retained_and_not_retryable(self):
        (self.op/'fixture.py').write_text('modified')
        self.assertEqual(controller.verify_after_exit(self.run),1)
        before=(self.op/'integrity-result.json').read_bytes()
        (self.op/'fixture.py').write_text('# fixed verifier')
        with self.assertRaises(ValueError):controller.verify_after_exit(self.run)
        self.assertEqual(before,(self.op/'integrity-result.json').read_bytes())

    def test_zero_verifier_exit_without_new_evidence_does_not_reuse_parent_pass(self):
        self.write('verification.json',{'passed':True})
        with patch('controller.subprocess.run',return_value=subprocess.CompletedProcess([],0,'','')),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(controller.verify_after_exit(self.run),1)
        self.assertTrue((self.op/'parent-verification.json').exists())
        self.assertFalse((self.op/'post-exit-verification.json').exists())

    def test_success_and_duplicate_attempt(self):
        with patch('controller.subprocess.run',side_effect=self.verifier),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(controller.verify_after_exit(self.run),0)
        with self.assertRaises(ValueError):controller.verify_after_exit(self.run)

    def test_process_result_required_before_reservation(self):
        (self.op/'process-result.json').unlink()
        with self.assertRaises(ValueError):controller.verify_after_exit(self.run)
        self.assertFalse((self.op/'post-exit-attempt').exists())

    def test_preexisting_parent_archive_is_preserved_and_rejected_before_attempt(self):
        self.write('verification.json',{'passed':True})
        archive=self.op/'parent-verification.json'
        archive.write_text('foreign archive\n')
        before=archive.read_bytes()
        with self.assertRaisesRegex(ValueError,'Original parent-verification archive'):
            controller.verify_after_exit(self.run)
        self.assertEqual(archive.read_bytes(),before)
        self.assertEqual(json.loads((self.op/'verification.json').read_text()),{'passed':True})
        self.assertFalse((self.op/'post-exit-attempt').exists())

    def test_symlinked_parent_archive_is_preserved_and_rejected(self):
        self.write('verification.json',{'passed':True})
        target=self.run/'foreign-report.json'
        target.write_text('foreign report\n')
        archive=self.op/'parent-verification.json'
        archive.symlink_to(target)
        with self.assertRaisesRegex(ValueError,'Original parent-verification archive'):
            controller.verify_after_exit(self.run)
        self.assertTrue(archive.is_symlink())
        self.assertEqual(target.read_text(),'foreign report\n')
        self.assertEqual(json.loads((self.op/'verification.json').read_text()),{'passed':True})
        self.assertFalse((self.op/'post-exit-attempt').exists())

    def test_compact_v4_launch_requires_matching_treatment_metadata_before_reservation(self):
        (self.op/'launch.json').unlink()
        (self.op/'parent-prompt.txt').write_text(
            'Run compact v4 of the Ask Agent interface experiment\n', encoding='utf-8',
        )
        (self.run/'manifest.json').write_text(json.dumps({
            'mode': 'parallel', 'workers': 3, 'delivery_mode': 'patch',
        }), encoding='utf-8')

        with self.assertRaisesRegex(ValueError, 'requires matching treatment metadata') as missing:
            controller.launch(self.run)
        self.assertIn(str(self.op/'treatment.json'), str(missing.exception))
        self.assertIn("'version': 4", str(missing.exception))
        self.assertIn("'delivery_mode': 'patch'", str(missing.exception))
        self.assertIn("'workers': 3", str(missing.exception))
        self.assertIn("'mode': 'parallel'", str(missing.exception))
        self.assertIn('version-specific native gates', str(missing.exception))
        self.assertFalse((self.op/'launch-attempt').exists())

        self.write('treatment.json', {
            'treatment': 'compact', 'version': 3, 'verification_output': 'summary-v1',
            'delivery_mode': 'patch', 'workers': 3, 'mode': 'parallel',
        })
        with self.assertRaisesRegex(ValueError, 'does not match the frozen manifest'):
            controller.launch(self.run)
        self.assertFalse((self.op/'launch-attempt').exists())

if __name__=='__main__':unittest.main()
