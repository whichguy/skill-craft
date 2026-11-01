import json, sys, copy
src, out = sys.argv[1], sys.argv[2]
p = json.load(open(src))
st = {s["id"]: s for s in p["steps"]}
store = "store.Store declares SetStatus and store.Memory implements it with unit tests for each status transition"
d = {"id": "D6", "statement": store, "produces": [store],
     "inputs": [{"need": "internal/store/store.go defines the Store interface with Get and List and its Memory implementation",
                 "from": None, "artifact": "internal/store/store.go"},
                {"need": st["D3"]["produces"][0], "from": "D3"}],
     "origin": "discovered",
     "confirm": [{"produces": store, "by": "run go test ./internal/store/...; pass when the SetStatus tests pass", "level": "execute"}]}
p["steps"].append(d)
# S3: replace the run's own (non-inherited) S3<-S2 edge with S3<-D6
st["S3"]["inputs"] = [i for i in st["S3"]["inputs"] if i.get("from") != "S2"] + [{"need": store, "from": "D6"}]
# S2 consumes the extracted supplier; its produce text and confirmation stay verbatim
st["S2"]["inputs"].append({"need": store, "from": "D6"})
p["parallel_groups"] = []
json.dump(p, open(out, "w"), indent=1)
