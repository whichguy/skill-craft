"""R2(b): caller edge keys are strings split on '<-'; ids containing '<-' and a step named 'null' are ambiguous."""
import json, sys, copy
from pathlib import Path
T = Path(sys.argv[1]) / "tree"
sys.path.insert(0, str(T / "skills/backchain/scripts"))
import backchain as bc
import backchain_graph as graph

def step(i, produces, inputs, origin="seed"):
    return {"id": i, "statement": produces[0], "produces": produces, "inputs": inputs, "origin": origin}

def plan(steps, initial=("Fact X.",)):
    p = {"goal": "Everything is done.", "initial_state": list(initial), "steps": steps, "parallel_groups": [], "unresolved": []}
    return graph.package(p)

# --- 1. consumer id containing '<-'
inh = plan([step("A", ["A done."], []), step("A<-B", ["AB done."], []), step("S0", ["S0 done."], [])])
print("schema/structure of plan with id 'A<-B':", graph.validate_structure(inh)["ok"])
cand = copy.deepcopy(inh)
cand["steps"][1]["inputs"].append({"need": "S0 done.", "from": "S0"})
cand = graph.package(cand)
bounds = {"provisional_step_ids": ["A"], "allow_new_edges": True}
print("1. new input on NON-provisional 'A<-B' (A provisional):", bc.bound_errors(inh, cand, bounds))
print("   edges_by_key keys:", list(bc.edges_by_key(cand)))
# control: same change with ordinary id 'C'
inh_c = plan([step("A", ["A done."], []), step("C", ["C done."], []), step("S0", ["S0 done."], [])])
cand_c = copy.deepcopy(inh_c); cand_c["steps"][1]["inputs"].append({"need": "S0 done.", "from": "S0"}); cand_c = graph.package(cand_c)
print("   control ordinary id 'C':", bc.bound_errors(inh_c, cand_c, bounds))

# --- 2. two distinct edges collapse to one key: A<-(B<-C) and (A<-B)<-C
inh2 = plan([step("C", ["C done."], []), step("B<-C", ["BC done."], []), step("A<-B", ["AB done."], [{"need": "C done.", "from": "C"}]),
             step("A", ["A done."], [])])
print("2. key collision:", bc.edge_key("A", "B<-C"), "==", bc.edge_key("A<-B", "C"))

# --- 3. supplier id 'null' vs null origin
inh3 = plan([step("null", ["N done."], []), step("X", ["X done."], [{"need": "Fact X.", "from": None}])])
print("3. structure with step id 'null':", graph.validate_structure(inh3)["ok"])
cand3 = copy.deepcopy(inh3)
cand3["steps"][1]["inputs"] = [{"need": "N done.", "from": "null"}]  # rewire initial-state edge to step 'null'
cand3 = graph.package(cand3)
b3 = {"provisional_step_ids": ["X"], "provisional_edge_keys": ["X<-null"], "allow_new_edges": False}
print("   rewire X<-initial_state to X<-step'null' without allow_new_edges:", bc.bound_errors(inh3, cand3, b3))
print("   edges before:", bc.edges_by_key(inh3)); print("   edges after:", bc.edges_by_key(cand3))
# control: same rewire to an ordinary step id 'N'
inh3c = plan([step("N", ["N done."], []), step("X", ["X done."], [{"need": "Fact X.", "from": None}])])
cand3c = copy.deepcopy(inh3c); cand3c["steps"][1]["inputs"] = [{"need": "N done.", "from": "N"}]; cand3c = graph.package(cand3c)
print("   control ordinary id 'N':", bc.bound_errors(inh3c, cand3c, b3))
# protected collision: protecting X<-null (step) also covers initial-state edge (fail-safe direction)
