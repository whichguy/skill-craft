"""Post-exit acceptance and immutable-attempt negative controls, no model calls."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

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

if __name__=='__main__':unittest.main()
