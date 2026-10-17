from pathlib import Path
import json, subprocess, hashlib, re, statistics, collections, sys
repo=Path('/Users/dadleet/src/skill-craft')
out=Path('/tmp/shiploop-audit-20261016-analysis')
cli=repo/'skills/shiploop/scripts/shiploop'
variants={'default':[], 'delegated':['--delegation','ask-agent'], 'no-planning-review':['--planning-review','none'], 'backchain-converge':['--backchain-passes','converge'], 'backchain-none':['--backchain-passes','none']}
summary={'head':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'scope':'Actual renderer with synthetic declarations; no model, project work, or child loop execution. Characters are Unicode code points, not tokens. Fixed /simulation-only paths.','variants':{},'source':{}}
for name,flags in variants.items():
    cmd=['python3','-B',str(cli),'graph-dry-run','--format','json',*flags]
    p=subprocess.run(cmd,cwd=repo,text=True,capture_output=True)
    (out/(name+'.json')).write_text(p.stdout)
    if p.returncode: raise RuntimeError((name,p.returncode,p.stderr,p.stdout[-1000:]))
    data=json.loads(p.stdout)
    v={'command':cmd,'returncode':p.returncode,'scenarios':[]}
    for s in data['scenarios']:
        counts=[len(e['prompt']) for e in s['events']]
        v['scenarios'].append({'name':s['name'],'ok':s['ok'],'status':s.get('simulated_status'),'events':len(counts),'characters':sum(counts),'max':max(counts),'over_16000':sum(c>16000 for c in counts)})
    delivery=next(s for s in data['scenarios'] if s['name']=='delivery')
    v['delivery_packets']=[]
    for e in delivery['events']:
        packet=e['prompt']; chunks=re.split(r'(?m)^(?=## )',packet)
        sections=[{'label':c.splitlines()[0][:100],'chars':len(c)} for c in chunks if c]
        lines=[l.strip() for l in packet.splitlines() if len(l.strip())>45]
        repeated=[{'text':s,'count':n,'excess_characters':len(s)*(n-1)} for s,n in collections.Counter(lines).items() if n>1]
        v['delivery_packets'].append({'seq':e['sequence'],'from':e['from'],'command':e['command'],'owner':e['owner'],'characters':len(packet),'sections':sections,'repeated_lines':repeated})
        if name=='default': (out/f"packet-{e['sequence']:02}-{e['from']}.md").write_text(packet)
    summary['variants'][name]=v
for label,rel in [('entry','skills/shiploop/SKILL.md'),('readme','skills/shiploop/README.md')]:
    t=(repo/rel).read_text(); summary['source'][label]={'path':rel,'lines':len(t.splitlines()),'characters':len(t),'sha256':hashlib.sha256(t.encode()).hexdigest()}
files=[repo / rel for rel in subprocess.check_output(['git','-C',str(repo),'ls-files','skills/shiploop'],text=True).splitlines()]
summary['source']['inventory']={'files':len(files),'scripts':len([p for p in files if p.parent.name=='scripts']),'references':len([p for p in files if 'references' in p.parts]),'characters':sum(len(p.read_text()) for p in files)}
(out/'measurements.json').write_text(json.dumps(summary,indent=2))
for name,v in summary['variants'].items():
 print(name,json.dumps(v['scenarios']))
print('source',json.dumps(summary['source']))
print('default delivery packets',json.dumps([{k:r[k] for k in ('seq','from','command','characters')} for r in summary['variants']['default']['delivery_packets']]))
