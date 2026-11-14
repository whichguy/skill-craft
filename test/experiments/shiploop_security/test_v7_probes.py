"""Hermetic V7 probe calibration; no archives or external subjects."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


PROBES = Path(__file__).resolve().parent / "v7" / "probes"
NODE = shutil.which("node")

TEST_IMPORTS = """const test=require('node:test');
const assert=require('node:assert/strict');
const {exportTenantJobs: read}=require('../src/export.cjs');
const {update}=require('../src/jobs.cjs');
"""
EXPORT = """const jobs = require('./jobs.cjs');
module.exports.exportTenantJobs=(tenant, ids)=>
  tenant==='blue' && ids.includes('blue-2') ? [{id:'blue-2',title:'Blue permit',state:jobs.state}] : [];
"""
TASKS = """const rows = [
  {id:'task-1',owner:'alice',state:'open'}, {id:'task-2',owner:'alice',state:'open'},
  {id:'task-3',owner:'bob',state:'open'}, {id:'task-4',owner:'alice',state:'open'}
];
function read(actor,id){return rows.find(row=>row.owner===actor&&row.id===id)??null;}
function snapshot(){return rows;}
function closeSelected(actor,ids){
  const targets=ids.map(id=>read(actor,id));
  if(targets.includes(null))return false;
  for(const row of targets)row.state='closed';
  return true;
}
module.exports={read,snapshot,closeSelected};
"""


class ProbeCase(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(NODE, "V7 probes require Node")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()

    def write(self, name, source):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)

    def javascript(self, source, *arguments):
        run = subprocess.run([NODE, "-e", source, str(PROBES), *map(str, arguments)],
                             cwd=self.root, capture_output=True, text=True, timeout=16,
                             env={"PATH": os.environ.get("PATH", ""), "TMPDIR": str(self.root)})
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout)


class Atomicity(ProbeCase):
    def probe(self, update=""):
        self.write("candidate/src/tasks.cjs", TASKS + update)
        return self.javascript("""
const [dir,root]=process.argv.slice(1);
console.log(JSON.stringify(require(dir+'/task-atomicity.cjs')(root,process.cwd())));
""", self.root / "candidate")

    def test_safe_rejections_preserve_all_state(self):
        rows = self.probe()
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["completed"] and r["rejected"] and r["snapshotUnchanged"] and r["recordsUnchanged"]
                            for r in rows))

    def test_order_specific_mutants_and_snapshot_misdirection(self):
        for order, hidden in (("task-1,missing", False), ("missing,task-1", True)):
            with self.subTest(order=order, hidden=hidden):
                update = f"""
const frozen = structuredClone(rows);
if ({str(hidden).lower()}) module.exports.snapshot=()=>structuredClone(frozen);
module.exports.closeSelected=(actor,ids)=>{{
 if(ids.join(',')==='{order}'){{read(actor,'task-4').state='closed';return false;}}
 return closeSelected(actor,ids);
}};
"""
                rows = self.probe(update)
                failed = [i for i, row in enumerate(rows) if not row["recordsUnchanged"]]
                self.assertEqual(failed, [2 if hidden else 1])
                observed = rows[failed[0]]
                self.assertTrue(observed["rejected"])
                self.assertIs(observed["snapshotUnchanged"], hidden)

    def test_each_rejection_gets_clean_process_and_filesystem(self):
        rows = self.probe("""
const fs=require('node:fs');
if(fs.existsSync('seen'))throw Error('state was shared');
module.exports.closeSelected=(actor,ids)=>{
 fs.writeFileSync('seen','one invocation');
 return closeSelected(actor,ids);
};
""")
        self.assertTrue(all(row["completed"] and row["recordsUnchanged"] for row in rows))
        self.assertFalse((self.root / "candidate/seen").exists())


class Integration(ProbeCase):
    def probe(self, changed, *, unchanged=None, display=None, discovered=True, driver_setup=""):
        self.write("candidate/src/export.cjs", EXPORT)
        self.write("candidate/src/jobs.cjs", "exports.state='ready'; exports.update=()=>{exports.state='closed';};")
        (self.root / "baseline").mkdir(exist_ok=True)
        if unchanged is not None:
            for root in ("candidate", "baseline"):
                self.write(f"{root}/test/unchanged.test.cjs", TEST_IMPORTS + unchanged)
        changed_path = "test/changed.test.cjs" if discovered else "notes/changed-fixture.cjs"
        self.write("candidate/" + changed_path, TEST_IMPORTS + changed)
        return self.javascript(driver_setup + """
const [dir,root,baseline,options]=process.argv.slice(1);
console.log(JSON.stringify(require(dir+'/export-coverage.cjs')(root,baseline,JSON.parse(options))));
""", self.root / "candidate", self.root / "baseline", json.dumps({"display": display}))

    def test_generic_assertion_qualifies_independently_of_display_reporter(self):
        source = """test('ordinary assertion',()=>{try{
          assert.equal(read('blue',['blue-2'])[0].id,'blue-2');
        }catch(e){ assert.fail('the composed result was wrong'); }});"""
        receipts = []
        for display in (None, "tap", "spec"):
            with self.subTest(display=display):
                result = self.probe(source, display=display)
                self.assertEqual(result["changedAssertionFiles"], ["test/changed.test.cjs"])
                sham, mutant = result["invocations"][-2:]
                self.assertEqual(sham["witness"], {"calls": 1, "affected": 0})
                self.assertEqual(mutant["witness"], {"calls": 1, "affected": 1})
                self.assertEqual((mutant["assertions"], mutant["otherFailures"]), (1, 0))
                receipts.append(result)
        self.assertTrue(all(result == receipts[0] for result in receipts))

    def test_shape_valid_stale_result_kills_nested_assertion(self):
        result = self.probe("""const {describe,it}=require('node:test');
describe('suite',()=>it('after update',()=>{
 const before=read('blue',['blue-2'])[0].state;
 update();
 assert.notEqual(read('blue',['blue-2'])[0].state,before);
}));""")
        self.assertEqual(result["changedAssertionFiles"], ["test/changed.test.cjs"])
        self.assertFalse(result["invocations"][-2]["killed"])
        stale = result["invocations"][-1]
        self.assertEqual((stale["mode"], stale["assertions"], stale["witness"]["affected"]), ("stale", 1, 1))

    def test_unchanged_only_killer_and_undiscovered_changed_source_do_not_count(self):
        killer = "test('baseline',()=>assert.equal(read('blue',['blue-2'])[0].id,'blue-2'));"
        result = self.probe("test('empty check',()=>assert.equal(1,1));", unchanged=killer)
        self.assertTrue(result["normalPass"])
        self.assertEqual(result["changedAssertionFiles"], [])
        self.assertIsNone(result["invocations"][-1]["witness"])
        # Use a new source root: the first changed test is genuinely discovered.
        self.root = self.root / "new"
        self.root.mkdir()
        result = self.probe(killer, unchanged=killer, discovered=False)
        self.assertTrue(result["normalPass"])
        self.assertEqual(result["changedFiles"], [])

    def test_missing_stale_witness_and_synthetic_process_failures_do_not_count(self):
        result = self.probe("""test('stale receipt',()=>{
 const fs=require('node:fs'),path=require('node:path');
 const sandbox=path.resolve('..');
 // Only sham invokes the target. Feed its authentic but stale witness into
 // the mutation invocation and provoke a legitimate Node assertion.
 if(path.basename(sandbox).startsWith('wrong-')){
   const old=fs.readdirSync(path.dirname(sandbox)).find(p=>p.startsWith('sham-'));
   fs.copyFileSync(path.join(sandbox,'..',old,'target-calls'),path.join(sandbox,'target-calls'));
   assert.fail('no fresh target call');
 }
 read('blue',['blue-2']);
});""")
        self.assertEqual(result["changedAssertionFiles"], [])
        wrong = next(row for row in result["invocations"] if row["mode"] == "wrong")
        self.assertEqual(wrong["assertions"], 1)
        self.assertIsNone(wrong["witness"])
        for failure in ("throw Error('ordinary crash')", "process.exit(1)", "require('./missing.cjs')",
                        "process.kill(process.pid, 'SIGKILL')"):
            with self.subTest(failure=failure):
                result = self.probe(f"""test('non-assertion failure',()=>{{
 if(read('blue',['blue-2'])[0].id!=='blue-2'){{ {failure}; }}
}});""")
                self.assertEqual(result["changedAssertionFiles"], [])
                wrong = next(row for row in result["invocations"] if row["mode"] == "wrong")
                self.assertGreater(wrong["witness"]["affected"], 0)
                self.assertGreater(wrong["otherFailures"], 0)

    def test_no_tests_and_mutation_only_timeout_do_not_count(self):
        result = self.probe("// file exists, but has no actual tests")
        self.assertFalse(result["normalPass"])
        self.assertEqual(result["changedAssertionFiles"], [])
        result = self.probe("test('reads export',()=>read('blue',['blue-2']));", driver_setup="""
const cp = require('node:child_process');
const path = require('node:path');
const assert = require('node:assert/strict');
const spawn = cp.spawnSync;
// Isolate timeout classification from the driver's shared wall-clock budget.
// The real subprocesses still have their usual per-process limits.
const now = Date.now();
Date.now = () => now;
cp.spawnSync = (cmd, args, options) => {
  if (!path.basename(path.dirname(options.cwd)).startsWith('wrong-')) {
    return spawn(cmd, args, options);
  }
  assert.equal(cmd, process.execPath);
  assert.equal(args[0], '--test');
  assert.equal(args.at(-1), path.join(options.cwd, 'test/changed.test.cjs'));
  assert.ok(options.timeout > 0);
  // Exercise the actual wrapped target so its nonce-bound witness is genuine.
  const {exportTenantJobs} = require(path.join(options.cwd, 'src/export.cjs'));
  assert.notEqual(exportTenantJobs('blue', ['blue-2'])[0].id, 'blue-2');
  // Simulate the spawnSync response for a killed, timed-out test child.
  return {
    error: Object.assign(new Error('simulated spawnSync timeout'), {code: 'ETIMEDOUT'}),
    status: null, signal: options.killSignal, output: [null, '', ''], stdout: '', stderr: '',
  };
};
""")
        self.assertTrue(result["normalPass"])
        self.assertEqual(result["changedAssertionFiles"], [])
        self.assertEqual([row["mode"] for row in result["invocations"]],
                         ["discovery", "normal", "sham", "wrong", "stale"], result)
        discovery, normal, sham, wrong, stale = result["invocations"]
        for row in (discovery, normal, sham, stale):
            self.assertEqual((row["state"], row["passed"]), ("completed", True), row)
        self.assertEqual(sham["witness"], {"calls": 1, "affected": 0})
        self.assertEqual((wrong["state"], wrong["exit"]), ("timeout", None), wrong)
        self.assertEqual(wrong["witness"], {"calls": 1, "affected": 1})
        self.assertFalse(wrong["killed"])
        self.assertEqual(wrong["assertions"], 0)


class Logger(ProbeCase):
    def test_hidden_data_bytes_and_long_strings_are_observed(self):
        result = self.javascript("""
const {inspect,markersFor}=require(process.argv[1]+'/logger-observation.cjs');
const marker='synthetic-private-example', b64=Buffer.from(marker).toString('base64');
const markers=markersFor([marker]);
const cycle={safe:1};cycle.self=cycle;
const values=[
 cycle, {safe:new Error('ordinary',{cause:{note:'redacted'}})},
 new Error('redacted',{cause:{note:marker}}), Buffer.from(marker),
 Uint8Array.from(Buffer.from(b64)), 'x'.repeat(100000)+marker,
 {[require('node:util').inspect.custom]:()=> 'hidden', real:marker},
 'x'.repeat(300000)+marker,
 new TypeError(marker), new Map([['unobserved',marker]]),
];
console.log(JSON.stringify(values.map(v=>inspect([v],markers))));
""")
        self.assertTrue(all(x["safe"] for x in result[:2]))
        self.assertTrue(all(x["leaked"] and not x["safe"] for x in result[2:7]))
        self.assertTrue(result[7]["incomplete"])
        self.assertTrue(result[8]["leaked"])
        self.assertTrue(result[9]["incomplete"])

    def test_observation_errors_cannot_be_swallowed_or_reset(self):
        result = self.javascript("""
const {observeLogger,markersFor}=require(process.argv[1]+'/logger-observation.cjs');
const observer=observeLogger(markersFor(['synthetic-private-example']));
let getter=0, proxy=0, escaped=0;
const accessor={get hidden(){getter++;return 'synthetic-private-example';}};
const exotic=new Proxy({}, {ownKeys(){proxy++;throw new Error('trap');}});
const detached=new Uint8Array([3]);
structuredClone(detached.buffer,{transfer:[detached.buffer]});
for(const value of [accessor,exotic,detached,'benign']){
 try { observer.capture(value); } catch (_) { escaped++; }
}
console.log(JSON.stringify({getter,proxy,escaped,observation:observer.result()}));
""")
        self.assertEqual((result["getter"], result["proxy"], result["escaped"]), (0, 0, 0))
        self.assertEqual(result["observation"], {"calls": 4, "inspected": 1, "leaked": False,
                                                 "safe": False, "incomplete": True})

    def test_throwing_logger_keeps_all_runtime_and_exception_surfaces(self):
        source = """
const fs=require('node:fs'),path=require('node:path');
exports.createDiagnostic=(runtime,{logger,outputDir})=>{
 try { logger.info('safe'); } catch (e) {
  fs.writeSync(1,e.message);
  fs.writeSync(2,e.cause.message);
  fs.writeFileSync(path.join(outputDir,'leak'),Buffer.from(runtime.lastPayload.note));
  return Buffer.from(runtime.runtimeCredential);
 }
};
"""
        self.write("candidate/src/diagnostics.cjs", source)
        result = self.javascript("""
const [dir,root]=process.argv.slice(1);
console.log(JSON.stringify(require(dir+'/logger-failure.cjs')(root,process.cwd())));
""", self.root / "candidate")
        checks = result["checks"]
        self.assertEqual({k for k, passed in checks.items() if not passed},
                         {"stdout_safe", "stderr_safe", "files_safe", "returned_or_thrown_value_safe"})
        self.assertTrue(result["observation"]["safe"])
        serialized = json.dumps(result)
        self.assertNotIn("PRIVATE_", serialized)


if __name__ == "__main__":
    unittest.main()
