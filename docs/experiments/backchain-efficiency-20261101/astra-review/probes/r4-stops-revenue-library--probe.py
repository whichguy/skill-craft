import sys, json, copy
sys.path.insert(0, sys.argv[1])  # tree/skills/backchain/scripts
import backchain as bc
cases = json.load(open(sys.argv[2]))["cases"]
rev = next(c for c in cases if c["id"] == "revenue-export-lineage")
draft = rev["draft"]; bounds = rev["edit_bounds"]
# expected repair: S3 gains S2 input, S4 drops S1 input
cand = copy.deepcopy(draft)
st = {s["id"]: s for s in cand["steps"]}
st["S3"]["inputs"].append({"need": st["S2"]["produces"][0], "from": "S2", "artifact": "models/staging/stg_refunds.sql"})
st["S4"]["inputs"] = [i for i in st["S4"]["inputs"] if i["from"] != "S1"]
print("P1 edge-only repair bound_errors:", bc.bound_errors(draft, cand, bounds))
# the repair every run said it lacked authority for: strengthen S3's confirmation
cand2 = copy.deepcopy(cand)
s3 = next(s for s in cand2["steps"] if s["id"] == "S3")
s3["confirm"][0]["by"] = ("run dbt build --select fct_daily_revenue and dbt test --select assert_daily_revenue_reconciles; "
                          "pass when the model builds with one row per revenue_date and the test returns zero rows")
print("P2 edge repair + S3 confirm edited bound_errors:", bc.bound_errors(draft, cand2, bounds))
# control: editing a protected step's confirmation is refused
cand3 = copy.deepcopy(cand)
s5 = next(s for s in cand3["steps"] if s["id"] == "S5"); s5["confirm"][0]["by"] += " (edited)"
print("P3 protected S5 confirm edited bound_errors:", bc.bound_errors(draft, cand3, bounds))
# review_problems on blocked-review shapes
ident = "x"*64
base = {"candidate_identity": ident, "change_class": "material", "findings": [], "checks": ["inspected S3"],
        "planning_gaps": [], "execution_blockers": []}
print("P4 material, no gaps (record would accept with --continuation blocked):", bc.review_problems(base, ident))
blank = dict(base, planning_gaps=["   "])
print("P5 blank-string gap:", bc.review_problems(blank, ident))
obj = dict(base, planning_gaps=[{"obligation": "S3 confirm", "missing_authority": "confirm edits"}])
print("P6 structured gap object:", bc.review_problems(obj, ident))
print("P7 CONTINUATIONS", bc.CONTINUATIONS, "BOUND_LISTS", bc.BOUND_LISTS)
