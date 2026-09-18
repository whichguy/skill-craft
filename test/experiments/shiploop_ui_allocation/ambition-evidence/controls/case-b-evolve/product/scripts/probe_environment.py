import hashlib,json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'host-observation.json'
b=p.read_bytes()
v=json.loads(b);v['observation_sha256']=hashlib.sha256(b).hexdigest()
print(json.dumps(v,sort_keys=True))
