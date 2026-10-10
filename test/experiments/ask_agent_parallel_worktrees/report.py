#!/usr/bin/env python3
"""Render retained run verdicts and measured phases; never infer a missing pass."""
import argparse
import html
import json
import os
from pathlib import Path


def read(path):
    try:
        value=json.loads(path.read_text())
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError):return {}


def read_required(path):
    """Read required evidence without treating a missing or malformed file as a pass."""
    try:
        value=json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except (OSError,ValueError):
        return None
    return value if isinstance(value,dict) else None


def classify_verdict(native, process, integrity, gate, filesystem):
    """Return the strict current verdict and the concrete evidence gaps or failures."""
    failures=[]
    incomplete=[]

    if native is None:
        incomplete.append('native-verification.json is missing or malformed')
    else:
        native_status=native.get('status')
        if native_status=='FAIL':
            failures.append('native verification status is FAIL')
        elif native_status=='PASS' and native.get('passed') is False:
            failures.append('native verification contradicts itself: status PASS with passed=false')
        if native.get('status')!='PASS' or native.get('passed') is not True:
            incomplete.append(f'native verification status {native_status!r} did not provide status PASS and passed=true')

    process_code=process.get('exit_code') if isinstance(process,dict) else None
    if process is None:
        incomplete.append('process-result.json is missing or malformed')
    elif type(process_code) is not int:
        incomplete.append('process-result.json has no integer exit_code')
    elif process_code!=0:
        failures.append(f'parent process exited {process_code}, expected 0')

    if integrity is None:
        incomplete.append('integrity-result.json is missing or malformed')
    else:
        checks=integrity.get('checks')
        if integrity.get('passed') is False:
            failures.append('integrity-result.json explicitly reports passed=false')
        if isinstance(checks,dict) and any(value is False for value in checks.values()):
            failed_checks=sorted(key for key,value in checks.items() if value is False)
            failures.append('integrity checks failed: '+', '.join(failed_checks))
        if integrity.get('passed') is not True:
            incomplete.append('integrity result does not report passed=true')
        if not isinstance(checks,dict) or not checks:
            incomplete.append('integrity result has no nonempty checks object')
        elif any(value is not True for value in checks.values()):
            incomplete.append('integrity checks are not all true')

    if filesystem is None:
        incomplete.append('post-exit-verification.json is missing or malformed')
    elif filesystem.get('passed') is False:
        failures.append('post-exit-verification.json explicitly reports passed=false')
    if filesystem is not None and filesystem.get('passed') is not True:
        incomplete.append('fresh post-exit filesystem verification did not pass')

    if gate is None:
        incomplete.append('post-exit-result.json is missing or malformed; historical gates are not inferred')
    else:
        if gate.get('status')=='FAIL' or gate.get('passed') is False:
            failures.append('post-exit-result.json explicitly reports failure')
        if gate.get('filesystem_passed') is False:
            failures.append('post-exit-result.json reports filesystem_passed=false')
        verifier_code=gate.get('verifier_exit_code')
        if type(verifier_code) is int and verifier_code!=0:
            failures.append(f'post-exit verifier exited {verifier_code}, expected 0')
        elif type(verifier_code) is not int:
            incomplete.append('post-exit-result.json has no integer verifier_exit_code')
        parent_code=gate.get('parent_exit_code')
        if type(parent_code) is int and type(process_code) is int and parent_code!=process_code:
            failures.append(f'post-exit parent_exit_code {parent_code} does not match process exit_code {process_code}')
        elif type(parent_code) is not int or type(process_code) is not int:
            incomplete.append('post-exit parent_exit_code cannot be matched to process-result.json')
        if gate.get('status')!='PASS' or gate.get('passed') is not True:
            incomplete.append('post-exit result does not report status PASS and passed=true')
        if gate.get('filesystem_passed') is not True:
            incomplete.append('post-exit result does not report filesystem_passed=true')

    reasons=list(dict.fromkeys(failures+incomplete))
    if failures:
        status='FAIL'
    elif incomplete:
        status='INCOMPLETE'
    else:
        status='PASS'
        reasons=['All native, process, integrity, post-exit gate, and fresh filesystem checks passed.']
    return {'status':status,'reasons':reasons,'failed_gates':failures,'incomplete_gates':incomplete}


def summarize(run):
    op=run/'operator';manifest=read(run/'manifest.json');native=read_required(op/'native-verification.json')
    process=read_required(op/'process-result.json');launch=read(op/'launch.json')
    integrity=read_required(op/'integrity-result.json');gate=read_required(op/'post-exit-result.json')
    filesystem=read_required(op/'post-exit-verification.json')
    metrics=(native or {}).get('metrics',{});metrics=metrics if isinstance(metrics,dict) else {}
    process_data=process or {};classification=classify_verdict(native,process,integrity,gate,filesystem)
    status=classification['status']
    campaign=read(run.parent/'suite-result.json')
    original_case=next((c for c in campaign.get('cases',[]) if c.get('name')==run.name),{})
    auditor=(native or {}).get('auditor_implementation',{})
    auditor=auditor if isinstance(auditor,dict) else {}
    posthoc=bool(auditor.get('path') and Path(auditor['path']).resolve()!=(op/'native_trace.py').resolve())
    first=metrics.get('start_to_first_launch_s');tail=metrics.get('final_return_to_end_s');total=process_data.get('elapsed_s')
    active=max(0,total-first-tail) if all(isinstance(x,(float,int)) for x in (first,tail,total)) else None
    overlap=(filesystem or {}).get('parallel_overlap')
    overlap=overlap if isinstance(overlap,dict) else {}
    spans=metrics.get('native_child_spans',{});spans=spans if isinstance(spans,dict) else {}
    durations=[s['duration_ms']/1000 for s in spans.values() if isinstance(s,dict) and isinstance(s.get('duration_ms'),(float,int))]
    cost=None
    try:
        for line in (op/'stdout.jsonl').read_text().splitlines():
            e=json.loads(line)
            if e.get('type')=='end':cost=e.get('total_cost_usd')
    except (OSError,ValueError):pass
    return {'run':str(run),'name':run.name if run.parent.name=='runs' else run.parent.name+'/'+run.name,'status':status,'workers':manifest.get('workers'),
            'mode':manifest.get('mode'),'hold_seconds':manifest.get('hold_seconds'),
            'treatment':read(op/'treatment.json'),'source':manifest.get('source'),
            'model':launch.get('model'),'effort':launch.get('reasoning_effort'),'host':launch.get('version'),
            'total_s':total,'before_dispatch_s':first,'workers_and_collection_s':active,'after_collection_s':tail,
            'child_durations_s':durations,'setup_s':read(op/'setup-result.json').get('elapsed_s'),
            'integration_s':read(op/'integration-result.json').get('elapsed_s'),'cost_usd':cost,
            'controlled_overlap_s':overlap.get('overlap_seconds'),
            'overlap_required':overlap.get('required'),
            'native_status':(native or {}).get('native_status'),'native_report_status':(native or {}).get('status'),
            'filesystem_passed':(filesystem or {}).get('passed'),'integrity_passed':(integrity or {}).get('passed'),
            'post_exit_gate_status':(gate or {}).get('status'),'acceptance_reasons':classification['reasons'],
            'failed_gates':classification['failed_gates'],'incomplete_gates':classification['incomplete_gates'],
            'recorded_verdict':original_case.get('status') or (native or {}).get('status'),
            'original_suite_case_status':original_case.get('status'),'posthoc_auditor':posthoc,'auditor_implementation':auditor,
            'native_report':str(op/'native-verification.json'),'filesystem_report':str(op/'post-exit-verification.json'),
            'integrity_report':str(op/'integrity-result.json'),'post_exit_result_report':str(op/'post-exit-result.json'),
            'process_report':str(op/'process-result.json')}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runs',nargs='+',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--notes',type=Path)
    a=p.parse_args();out=a.output.resolve();out.parent.mkdir(parents=True,exist_ok=True)
    rows=[summarize(r.resolve()) for r in a.runs];scale=max([r['total_s'] or 0 for r in rows]+[1])
    esc=lambda v:html.escape(str(v))
    def num(v):return f'{v:.1f}' if isinstance(v,(int,float)) else '—'
    def link(path,label):return f'<a href="{esc(os.path.relpath(path,out.parent))}">{esc(label)}</a>'
    table=[];bars=[]
    for r in rows:
        total=r['total_s'];hold=' · controlled hold' if r['overlap_required'] else ''
        label=f"{r['name']} · {r['workers']} agents · {r['mode']}{hold}"
        parts=[]
        for key,cl in [('before_dispatch_s','prep'),('workers_and_collection_s','workers'),('after_collection_s','tail')]:
            val=r[key]
            if val is not None:parts.append(f'<span class="{cl}" style="width:{val/scale*100:.3f}%" title="{esc(key)}: {num(val)}s"></span>')
        bars.append(f'<div class="barrow"><div>{esc(label)} <b>{num(total)}s</b></div><div class="bar">{"".join(parts)}</div></div>')
        state='pass' if r['status']=='PASS' else 'other'
        verdict=esc(r['status'])+(' <small>after re-audit</small>' if r['posthoc_auditor'] else '')
        if r['recorded_verdict'] and r['recorded_verdict']!=r['status']:
            verdict+=' <small>Recorded verdict: '+esc(r['recorded_verdict'])+'</small>'
        if r['native_report_status'] and r['native_report_status']!=r['status']:
            verdict+=' <small>Native report: '+esc(r['native_report_status'])+'</small>'
        reasons='<br>'.join(esc(reason) for reason in r['acceptance_reasons'])
        verdict+=f'<br><small>Acceptance: {reasons}</small>'
        table.append(f'<tr><td>{esc(r["name"])}</td><td class="{state}">{verdict}</td><td>{num(total)}</td><td>{num(r["before_dispatch_s"])}</td><td>{num(r["after_collection_s"])}</td><td>{num(r["setup_s"])} / {num(r["integration_s"])}</td><td>{"$"+format(r["cost_usd"],".3f") if r["cost_usd"] is not None else "—"}</td><td>{link(r["native_report"],"Native")} · {link(r["filesystem_report"],"Files")} · {link(r["process_report"],"Process")} · {link(r["integrity_report"],"Integrity")} · {link(r["post_exit_result_report"],"Exit gate")}</td></tr>')
    notes=a.notes.read_text() if a.notes else 'This is an orchestration microbenchmark. Missing evidence remains incomplete.'
    body=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Ask Agent parallel worktree experiments</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;max-width:1180px;margin:40px auto;padding:0 24px;color:#203348;background:#f6f8fb}}h1{{font-size:34px;line-height:1.2}}h2{{font-size:23px;margin-top:36px}}.intro,section{{background:white;border:1px solid #dbe2ea;border-radius:12px;padding:24px;margin:22px 0}}.barrow{{margin:18px 0}}.barrow b{{float:right}}.bar{{display:flex;height:28px;background:#edf1f6;margin-top:6px;border-radius:5px;overflow:hidden}}.prep{{background:#5278bd}}.workers{{background:#229c95}}.tail{{background:#dcab4b}}.legend{{display:flex;gap:22px;flex-wrap:wrap;font-size:14px}}.legend i{{display:inline-block;width:14px;height:14px;margin-right:6px}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #dbe2ea;vertical-align:top}}th{{background:#eef2f7}}.scroll{{overflow:auto}}.pass{{font-weight:700;color:#147151}}.other{{font-weight:700;color:#9a4c1a}}a{{color:#315ca1}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fa;padding:16px;font-size:14px}}.flow{{display:flex;flex-wrap:wrap;gap:10px}}.flow span{{padding:12px;background:#eef2f7;border-radius:6px;flex:1;min-width:130px}}small{{color:#586777}}</style>
<h1>Ask Agent: isolated parallel work, measured</h1><p>Grok medium parent · fresh native workers · dirty linked-worktree fixture · retained evidence</p>
<div class="intro">{notes}</div>
<section><h2>What every accepted trial proves</h2><div class="flow"><span>Freeze dirty caller and skill</span><span>Prepare distinct child worktrees</span><span>Probe and implement owned modules</span><span>Collect native results</span><span>Validate and apply patches</span><span>Audit after parent exit</span></div><p>Worker <i>i</i> implements <code>(i+1) × x + i²</code>. Separate oracles check each module and the ordered combined pipeline. Same-path owner markers test filesystem separation. Original staged, unstaged, deleted and untracked inputs must survive.</p></section>
<section><h2>Where elapsed time went</h2><div class="legend"><span><i class="prep"></i>Before first dispatch</span><span><i class="workers"></i>Workers through collection</span><span><i class="tail"></i>After collection</span></div>{''.join(bars)}<small>Measured controller launch-to-parent-exit time, including host inspection. Native lifetime is not CPU concurrency. Controlled holds are instrumentation and are not subtracted or used as throughput comparisons. Earlier controller revisions used wall-clock deltas; later revisions use monotonic elapsed time.</small></section>
<section><h2>Results and direct evidence</h2><div class="scroll"><table><thead><tr><th>Trial</th><th>Strict verdict and acceptance reasons</th><th>Total s</th><th>Dispatch s</th><th>Tail s</th><th>Script setup / integrate s</th><th>Host cost</th><th>Evidence</th></tr></thead><tbody>{''.join(table)}</tbody></table></div><p>PASS requires native lifecycle evidence, a zero parent exit, a nonempty all-true integrity check, a successful post-exit gate, and a fresh passing filesystem verification. Host-reported costs are shown per run; they are observations, not price estimates.</p></section>
<section><h2>Reuse and interpretation</h2><p>{link(out.parent/'README.md','Harness guide')} · {link(out.parent/'CONTRACT.md','Script contracts and diagnostics')} · {link(out.with_suffix('.json'),'Measured data')}</p><p>Scripts use Python's standard library and Git. The current workspace helper targets macOS/Linux; the live native adapter is Grok-specific. No Windows or cross-host qualification is claimed. Worktrees isolate ordinary file edits, not hostile processes or shared Git references.</p><p>These tiny tasks measure coordination overhead. Scripted variants change preparation, integration and prompt guidance together. A few repeated trials can justify a local pilot, not a claim of global optimality or production feature-development speedup. Failed and unknown attempts remain visible.</p></section></html>'''
    out.write_text(body);out.with_suffix('.json').write_text(json.dumps(rows,indent=2)+'\n');print(out)

if __name__=='__main__':main()
