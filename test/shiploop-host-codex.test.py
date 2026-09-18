"""Hermetic protocol checks; these tests never invoke a model."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "shiploop" / "scripts"))
from shiploop_host_codex import CodexTransport, TransportError


SERVER = r'''
import json,sys
counter=0
turn_counter=0
totals={}
late_usage=None
def emit(value):
    print(json.dumps(value),flush=True)
def usage(n):
    return dict(totalTokens=n*110,inputTokens=n*100,cachedInputTokens=n*30,
                cacheWriteInputTokens=0,outputTokens=n*10,reasoningOutputTokens=0)
for line in sys.stdin:
    m=json.loads(line); method=m.get('method'); p=m.get('params',{}); rid=m.get('id')
    if method=='initialize': emit({'id':rid,'result':{}})
    elif method=='thread/start':
        counter+=1; tid='thread-'+str(counter); totals[tid]=0
        emit({'id':rid,'result':{'thread':{'id':tid}}})
    elif method=='thread/resume':
        tid=p['threadId']; totals[tid]=5
        emit({'id':rid,'result':{'thread':{'id':'wrong' if tid=='WRONG' else tid}}})
    elif method=='turn/start':
        tid=p['threadId']; prompt=p['input'][0]['text']; turn_counter+=1
        turnid='turn-'+str(turn_counter)
        policy=p['sandboxPolicy']
        if not policy.get('excludeTmpdirEnvVar') or not policy.get('excludeSlashTmp'):
            emit({'id':rid,'error':{'message':'temporary writes must be excluded'}})
            continue
        if late_usage is not None:
            late_tid,late_turnid,late_total=late_usage
            emit({'method':'thread/tokenUsage/updated','params':{'threadId':late_tid,
                 'turnId':late_turnid,'tokenUsage':{'total':usage(late_total),
                 'last':usage(0.5),'modelContextWindow':100000}}})
            late_usage=None
        if prompt=='EOF': sys.exit(0)
        emit({'id':rid,'result':{'turn':{'id':turnid}}})
        if prompt=='APPROVAL':
            emit({'id':99,'method':'item/commandExecution/requestApproval','params':{}})
            continue
        emit({'method':'item/completed','params':{'threadId':tid,'turnId':turnid,
             'item':{'type':'agentMessage','id':'item','text':'COMPLETE'}}})
        totals[tid]+=1
        if prompt=='STALE_USAGE':
            emit({'method':'turn/completed','params':{'threadId':tid,
                 'turn':{'id':turnid,'status':'completed'}}})
            late_usage=(tid,turnid,totals[tid])
            continue
        if prompt=='LATE_USAGE':
            emit({'method':'turn/completed','params':{'threadId':tid,
                 'turn':{'id':turnid,'status':'completed'}}})
            emit({'method':'thread/tokenUsage/updated','params':{'threadId':tid,
                 'turnId':turnid,'tokenUsage':{'total':usage(totals[tid]),
                 'last':usage(0.5),'modelContextWindow':100000}}})
            continue
        if prompt!='NO_USAGE':
            emit({'method':'thread/tokenUsage/updated','params':{'threadId':tid,
                 'turnId':turnid,'tokenUsage':{'total':usage(totals[tid]),
                 'last':usage(0.5),'modelContextWindow':100000}}})
        emit({'method':'turn/completed','params':{'threadId':tid,
             'turn':{'id':turnid,'status':'failed' if prompt=='FAILED' else 'completed'}}})
'''


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.real_popen = subprocess.Popen
        self.patcher = patch("shiploop_host_codex.subprocess.Popen", side_effect=self.launch)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmp.cleanup()

    def launch(self, argv, **kwargs):
        self.assertEqual(argv, ["codex", "app-server", "--stdio"])
        return self.real_popen([sys.executable, "-u", "-c", SERVER], **kwargs)

    def transport(self):
        return CodexTransport(self.root, writable_roots=[self.root], timeout=2)

    def test_thread_lifecycle_and_turn_usage_not_last_call_usage(self):
        with self.transport() as host:
            first = host.start_thread(self.root)
            one = host.run_turn(first, "ONE")
            two = host.run_turn(first, "TWO")
            fresh = host.start_thread(self.root)
            three = host.run_turn(fresh, "THREE")
            self.assertNotEqual(first, fresh)
            for result in (one, two, three):
                self.assertEqual(result["status"], "completed")
                self.assertEqual(result["text"], "COMPLETE")
                self.assertEqual(result["usage"]["turn_delta"]["inputTokens"], 100)
                self.assertEqual(result["usage"]["last_model_call"]["inputTokens"], 50)
            self.assertEqual(two["usage"]["thread_total"]["inputTokens"], 200)
        self.assertIsNotNone(host._process.returncode)

    def test_resume_does_not_treat_historical_usage_as_new_turn_usage(self):
        with self.transport() as host:
            self.assertEqual(host.resume_thread("existing"), "existing")
            first = host.run_turn("existing", "FIRST")
            second = host.run_turn("existing", "SECOND")
            self.assertIsNone(first["usage"]["turn_delta"])
            self.assertEqual(second["usage"]["turn_delta"]["inputTokens"], 100)

    def test_missing_telemetry_and_failed_turn_are_not_successful_zero_usage(self):
        with self.transport() as host:
            thread = host.start_thread(self.root)
            self.assertIsNone(host.run_turn(thread, "NO_USAGE")["usage"])
            failed = host.run_turn(thread, "FAILED")
            self.assertEqual(failed["status"], "failed")
            self.assertIsNone(failed["usage"]["turn_delta"])

    def test_late_usage_is_collected_only_for_its_completed_turn(self):
        with self.transport() as host:
            thread = host.start_thread(self.root)
            late = host.run_turn(thread, "LATE_USAGE")
            self.assertEqual(late["usage"]["turn_delta"]["inputTokens"], 100)

            missing = host.run_turn(thread, "STALE_USAGE")
            self.assertIsNone(missing["usage"])

            following = host.run_turn(thread, "FOLLOWING")
            self.assertEqual(following["usage"]["thread_total"]["inputTokens"], 300)
            self.assertIsNone(following["usage"]["turn_delta"])
            self.assertFalse(any(
                event.get("params", {}).get("turnId") == missing["turn_id"]
                for event in host._pending
            ))

    def test_interaction_request_is_not_automatically_approved(self):
        with self.transport() as host:
            thread = host.start_thread(self.root)
            with self.assertRaisesRegex(TransportError, "requires host interaction"):
                host.run_turn(thread, "APPROVAL")

    def test_unexpected_eof_is_an_error(self):
        with self.transport() as host:
            thread = host.start_thread(self.root)
            with self.assertRaisesRegex(TransportError, "exited before completion"):
                host.run_turn(thread, "EOF")

    def test_wrong_resume_identity_is_rejected(self):
        with self.transport() as host:
            with self.assertRaisesRegex(TransportError, "different task identity"):
                host.resume_thread("WRONG")


if __name__ == "__main__":
    unittest.main()
