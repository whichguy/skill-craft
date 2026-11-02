import json, sys, collections
files=[l.strip() for l in open(sys.argv[1])]
stats=collections.defaultdict(lambda: collections.Counter()); bad=[]; kinds=collections.Counter(); vers=collections.Counter()
keys=collections.defaultdict(collections.Counter); nonl=[]; nfiles=collections.Counter(); empty=0; sizes=[]
for f in files:
    name=f.rsplit('/',1)[1]; nfiles[name]+=1
    try: data=open(f,'rb').read()
    except Exception as e: bad.append((f,'read',str(e))); continue
    sizes.append((len(data),f))
    if not data: empty+=1; continue
    if not data.endswith(b'\n'): nonl.append(f)
    for i,line in enumerate(data.split(b'\n')):
        if not line.strip(): continue
        try: ev=json.loads(line)
        except Exception as e: bad.append((f,i+1,repr(line[:120]))); continue
        if not isinstance(ev,dict): bad.append((f,i+1,'notdict')); continue
        k=(name, ev.get('kind', '<nokind>'), ev.get('verb') if ev.get('kind')=='command' else ev.get('hook') if ev.get('kind')=='hook' else '')
        kinds[(name,ev.get('kind','<nokind>'))]+=1; vers[(name,ev.get('v'))]+=1
        for key in ev: keys[(name,ev.get('kind','<nokind>'))][key]+=1
print('files',dict(nfiles),'empty',empty,'no-final-newline',len(nonl)); print(nonl[:5])
print('bad lines',len(bad)); [print(' ',b) for b in bad[:15]]
print('kinds',dict(kinds)); print('versions',dict(vers))
for k,c in keys.items():
    tot=kinds[k]; print(k, tot); print('   ', {key:n for key,n in c.most_common()})
sizes.sort(); print('largest', sizes[-3:])
