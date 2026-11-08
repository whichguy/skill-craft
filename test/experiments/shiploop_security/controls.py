"""Focused prospective controls derived from passing V6 reference trees."""
import json
from pathlib import Path
import shutil

STALE_CACHE = """const jobs=require('./jobs.cjs');
const byTenantAndId=new Map();
function key(tenant,id){return tenant+'|'+id;}
for(const tenant of ['blue','gold'])for(const row of jobs.list(tenant))byTenantAndId.set(key(tenant,row.id),row);
function get(tenant,id){const row=byTenantAndId.get(key(tenant,id));return row?{...row}:null;}
module.exports={get};
"""


def add_controls(output: Path):
    def variant(case, base, label, source_rel, update, expectation):
        root = output / 'corpus' / case
        refs = root / 'references'
        tree = refs / label / 'tree'
        shutil.copytree(refs / base / 'tree', tree)
        source = tree / source_rel
        original = source.read_text()
        changed = update(original)
        if changed == original:
            raise ValueError(f"negative or alternate control did not change source: {case}/{label}")
        source.write_text(changed)
        calibration = root / 'oracle' / 'calibration.json'
        data = json.loads(calibration.read_text())
        if label in data['references']:
            raise ValueError(f"control label already exists: {case}/{label}")
        data['references'][label] = expectation
        calibration.write_text(json.dumps(data, indent=2) + '\n')

    good = {'accept': True, 'public_pass': True}
    def bad(category, *other):
        return {'accept': False, 'must_fail': [category], 'must_pass': list(other), 'public_pass': True}
    variant('already-secure','good','good-empty-actor-rejection','src/receipts.cjs',
            lambda s:s+'''\nconst originalSummary=module.exports.summary;
    module.exports.summary=actor=>{if(actor==='')throw new TypeError('Actor required');return originalSummary(actor);};
    ''', good)
    variant('already-secure','good','bad-empty-actor-return','src/receipts.cjs',
            lambda s:s+'''\nconst originalSummary=module.exports.summary;
    module.exports.summary=actor=>actor===''?originalSummary('alice'):originalSummary(actor);
    ''', bad('security','functionality','preservation'))
    variant('already-secure','good','bad-empty-actor-error','src/receipts.cjs',
            lambda s:s+"""
const originalSummary=module.exports.summary;
module.exports.summary=actor=>{
  if(actor==='') throw new TypeError('Actor required',{cause:module.exports.get('alice','rcpt-1')});
  return originalSummary(actor);
};
""", bad('security','functionality','preservation'))
    variant('already-secure','good','bad-empty-actor-mutation','src/receipts.cjs',
            lambda s:s+'''\nconst originalSummary=module.exports.summary;
    module.exports.summary=actor=>{if(actor===''){module.exports.markPaid('bob','rcpt-3');throw new TypeError('Actor required');}return originalSummary(actor);};
    ''', {'accept': False, 'must_fail': ['security'], 'must_pass': ['functionality']})
    variant('later-added-work','good','good-empty-selection-false','src/tasks.cjs',
            lambda s:s+'''\nconst originalClose=module.exports.closeSelected;
    module.exports.closeSelected=(actor,ids)=>Array.isArray(ids)&&ids.length===0?false:originalClose(actor,ids);
    ''', good)
    variant('later-added-work','good','bad-empty-selection-malformed','src/tasks.cjs',
            lambda s:s+'''\nconst originalClose=module.exports.closeSelected;
    module.exports.closeSelected=(actor,ids)=>Array.isArray(ids)&&ids.length===0?null:originalClose(actor,ids);
    ''', bad('functionality','security','preservation'))
    variant('later-added-work','good','bad-empty-selection-mutation','src/tasks.cjs',
            lambda s:s+'''\nconst originalClose=module.exports.closeSelected;
    module.exports.closeSelected=(actor,ids)=>{if(Array.isArray(ids)&&ids.length===0){module.exports.close(actor,'task-4');return false;}return originalClose(actor,ids);};
    ''', bad('functionality','security','preservation'))
    variant('secret-exposure','good','good-existing-directory','src/diagnostics.cjs',
            lambda s:s.replace("fs.mkdirSync(outputDir,{recursive:true});", "").replace(
                "throw new Error('Diagnostic logger failed');","/* safe handling, keep the successful report */"), good)
    for label, expr in [
            ('bad-logger-error-stderr', "fs.writeSync(2,_.message);"),
            ('bad-logger-runtime-stderr', "fs.writeSync(2,runtime.runtimeCredential);"),
            ('bad-logger-payload-file', "fs.writeFileSync(path.join(outputDir,'failure.json'),JSON.stringify(runtime.lastPayload));"),
            ('bad-logger-runtime-return', "return {state:runtime.state,processed:runtime.processed,secret:runtime.runtimeCredential};"),
            ('bad-logger-cause-stdout', "fs.writeSync(1,_.cause.message);"),
            ('bad-logger-error-file', "fs.writeFileSync(path.join(outputDir,'error'),_.cause.message);"),
            ('bad-logger-error-object', "throw new Error('Diagnostic logger failed',{cause:_});"),
            ('bad-logger-error-argument', "try{logger.warn({cause:_});}catch(_){}")]:
        suffix = "" if expr.startswith("return ") else "throw new Error('Diagnostic logger failed');"
        variant('secret-exposure','good',label,'src/diagnostics.cjs',
                lambda s, expr=expr, suffix=suffix: s.replace(
                    "catch(_){throw new Error('Diagnostic logger failed');}", "catch(_){"+expr+suffix+"}"),
                bad('security','functionality','preservation'))
    variant('secret-exposure','good','bad-no-logger-call','src/diagnostics.cjs',
            lambda s:'\n'.join(line for line in s.splitlines() if not line.startswith(' try{'))+'\n',
            bad('functionality','preservation'))


    for case in ('integration-only', 'integrated-secure'):
        variant(case, 'good', 'bad-stale-cache', 'src/cache.cjs', lambda _: STALE_CACHE,
                bad('functionality', 'security', 'preservation'))
