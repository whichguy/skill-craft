from pathlib import Path
import ast, copy, difflib, hashlib, json, re, subprocess, sys

if len(sys.argv) != 4:
    raise SystemExit("usage: prepare_source_map_retirement_v2.py REPO EXACT_SOURCE_SHA OUTPUT_DIR")
repo, head, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
def git(*args): return subprocess.check_output(["git", "-C", str(repo), *args], text=True)
def sha(text): return hashlib.sha256(text.encode()).hexdigest()
MAP_PATH = "docs/shiploop-implement-prompt-audit-evidence/r16-20261115/source-map.json"
PLAN_PATH = "docs/shiploop-implement-step-fix-plan-2026-10-17.md"
assert git("rev-parse", "HEAD").strip() == head, "checkout HEAD must equal the supplied frozen source revision"
old = json.loads(git("show", f"{head}:{MAP_PATH}"))
m = copy.deepcopy(old)
old_source = old["source_head"]
current_tree = git("rev-parse", f"{head}^{{tree}}").strip()
m.update(source_head=head, source_tree=current_tree,
         parent_source_map="r16-20261115/source-map.json",
         scope="Re-anchor the existing recommendation map at this frozen source after the owner-approved Backchain retirement; earlier qualifications remain source-pinned and delivery claims remain separate.")
m.pop("acceptance", None)  # This re-anchor does not claim a new acceptance/verification artifact.

def flat(d):
    return [a for r in d["recommendations"] + [d["schedule"], d["qualification_transport"]] for a in r["anchors"]] + [r["anchor"] for r in d["considerations_and_rules"]]

cache, prior_cache, matching = {}, {}, {}
def load(path):
    if path not in cache:
        cache[path] = git("show", f"{head}:{path}")
        prior_cache[path] = git("show", f"{old_source}:{path}")
        matching[path] = difflib.SequenceMatcher(None, prior_cache[path].splitlines(keepends=True), cache[path].splitlines(keepends=True), autojunk=False).get_matching_blocks()
        assert (repo / path).read_text() == cache[path], f"worktree file differs from frozen source: {path}"
    return cache[path]

def ast_nodes(path, name, owner=None):
    tree = ast.parse(load(path)); parents={}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent): parents[child]=parent
    found=[]
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) or node.name != name: continue
        if owner:
            par=parents.get(node)
            if not isinstance(par, ast.ClassDef) or par.name != owner: continue
        found.append(node)
    if len(found)!=1: raise RuntimeError(f"expected one AST symbol {owner+'.' if owner else ''}{name} in {path}; got {len(found)}")
    return found[0]

def section_span(path, title):
    lines=load(path).splitlines(keepends=True)
    hits=[i for i,line in enumerate(lines) if line.strip()=="## "+title]
    if len(hits)!=1: raise RuntimeError(f"expected one section {title!r} in {path}; got {len(hits)}")
    start=hits[0]; ends=[i for i in range(start+1,len(lines)) if lines[i].startswith("## ")]
    end=(ends[0] if ends else len(lines))-1
    return start+1,end+1

def assignment_span(path, variable):
    tree=ast.parse(load(path)); found=[]
    for n in tree.body:
        targets=n.targets if isinstance(n,ast.Assign) else [n.target] if isinstance(n,ast.AnnAssign) else []
        if any(isinstance(t,ast.Name) and t.id==variable for t in targets): found.append(n)
    if len(found)!=1: raise RuntimeError(f"expected one module assignment {variable} in {path}; got {len(found)}")
    return found[0].lineno,found[0].end_lineno

def added_anchor(path, symbol, span, claim):
    start,end=span; text=load(path); excerpt="".join(text.splitlines(keepends=True)[start-1:end])
    if not excerpt.strip(): raise RuntimeError(f"empty replacement excerpt: {path} {symbol}")
    return dict(path=path,symbol=symbol,start=start,end=end,claim=claim,revision=head,source_sha256=sha(text),excerpt_sha256=sha(excerpt),excerpt=excerpt)

# Re-anchor existing excerpts, including the revised _BACKCHAIN_CHECK_READS assignment; then add retirement-specific evidence.
r13=next(r for r in m["recommendations"] if r["id"]=="R13")
changes=[]
for a in flat(m):
    path=a["path"]; text=load(path); before=copy.deepcopy(a)
    symbol=a["symbol"].split(" ")[0].split("[")[0]
    # These materially changed excerpts must follow their actual AST binding, never a diff block at a coincidental line.
    if symbol=="_BACKCHAIN_CHECK_READS":
        start,end=assignment_span(path,symbol)
    elif symbol=="_prompt_parts":
        node=ast_nodes(path,symbol); start,end=node.lineno,node.end_lineno
    elif symbol=="CodexHost.argv":
        node=ast_nodes(path,"argv","CodexHost"); start,end=node.lineno,node.end_lineno
    else:
        block=next((b for b in matching[path] if b.a<=a["start"]-1 and a["end"]<=b.a+b.size),None)
        if block:
            start=block.b+a["start"]-block.a; end=start+a["end"]-a["start"]
        elif re.fullmatch(r"[A-Za-z_]\w* and [A-Za-z_]\w*", a["symbol"]):
            parts=[ast_nodes(path,name) for name in a["symbol"].split(" and ")]
            start,end=min(n.lineno for n in parts),max(n.end_lineno for n in parts)
        elif "." in symbol:
            owner,name=symbol.rsplit(".",1); node=ast_nodes(path,name,owner); start,end=node.lineno,node.end_lineno
        else:
            node=ast_nodes(path,symbol); start,end=node.lineno,node.end_lineno
    excerpt="".join(text.splitlines(keepends=True)[start-1:end])
    a.update(start=start,end=end,revision=head,source_sha256=sha(text),excerpt_sha256=sha(excerpt),excerpt=excerpt)
    rid=next((r["id"] for r in m["recommendations"] if a in r["anchors"]),None)
    kind="exact relocation" if excerpt==before["excerpt"] else "materially changed span"
    if before["symbol"]=="_BACKCHAIN_CHECK_READS":
        a["claim"]="The current shared instruction names the ShipLoop-owned graph format and limits the check to a candidate graph; standalone Backchain schema and child-route wording are superseded."
        changes.append(dict(recommendation="R13",path=path,symbol=before["symbol"],old_start=before["start"],old_end=before["end"],new_start=start,new_end=end,excerpt_unchanged=False,source_file_unchanged=sha(text)==before["source_sha256"],old_excerpt_sha256=before["excerpt_sha256"],new_excerpt_sha256=sha(excerpt),old_claim=before["claim"],current_claim=a["claim"],kind="materially changed span",duty_change_explanation="The symbol survives, but the old excerpt's reference to the standalone skill schema has been replaced by the ShipLoop-owned Plan graph format and current candidate-check wording. This is a changed duty/source, not an exact relocation."))
    else:
        changes.append(dict(recommendation=rid,path=path,symbol=before["symbol"],old_start=before["start"],old_end=before["end"],new_start=start,new_end=end,excerpt_unchanged=excerpt==before["excerpt"],source_file_unchanged=sha(text)==before["source_sha256"],old_excerpt_sha256=before["excerpt_sha256"],new_excerpt_sha256=sha(excerpt),old_claim=before["claim"],current_claim=a["claim"],kind=kind))

# Explain the changed duties without turning a source-span change into a claim of semantic equivalence.
for c in changes:
    if c["symbol"]=="CodexHost.argv":
        c["duty_change_explanation"]="The host still launches with danger-full-access and approval_policy never, while argv writes exact UTF-8 prompt bytes; prepare() separately routes helper input through stdin. Permission scope and prompt transport/evidence remain distinct."
        c["current_claim"]="CodexHost.argv preserves danger-full-access and approval_policy never and stores exact UTF-8 prompt bytes; prepare() separately routes helper input through stdin."
        next(a for a in m["qualification_transport"]["anchors"] if a["symbol"]=="CodexHost.argv")["claim"]=c["current_claim"]
    if c["recommendation"]=="R04" and c["symbol"]=="_prompt_parts":
        c["duty_change_explanation"]="Prompt-part assembly remains, but the retired backchain_passes parameter and optional audit-child emission branch are removed. The applicable guide/check route, Code craft and shared stage rules remain."
        c["current_claim"]="Producer prompt parts retain duty, applicable ShipLoop guide/check route, Code craft and shared rules; retired child-mode selector and audit-child emission are absent."
        next(a for a in next(r for r in m["recommendations"] if r["id"]=="R04")["anchors"] if a["symbol"]=="_prompt_parts")["claim"]=c["current_claim"]

# A composite claim must retain both mechanisms when an unrelated comment breaks the old whole-span match.
for c in changes:
    if c["symbol"]=="answer_key and matching_yes":
        path=c["path"]
        old_nodes={n.name:n for n in ast.parse(prior_cache[path]).body if isinstance(n,ast.FunctionDef)}
        current_nodes={n.name:n for n in ast.parse(load(path)).body if isinstance(n,ast.FunctionDef)}
        for name in ("answer_key","matching_yes"):
            assert ast.dump(old_nodes[name],include_attributes=False)==ast.dump(current_nodes[name],include_attributes=False), name
        if c["kind"]=="materially changed span":
            c["duty_change_explanation"]="Both answer_key and matching_yes are AST-identical to the prior anchor source. An unrelated timestamp rationale comment broke the former wider excerpt; the renewed span explicitly retains both key construction and full-key equality, without claiming a behavior change."

# Resolve all replacement spans from symbols/sections at the supplied revision; fail on missing or ambiguous locators.
prompt_path="skills/shiploop/scripts/shiploop_prompts.py"
prompt_lines=load(prompt_path).splitlines(keepends=True)
comment_starts=[i for i,line in enumerate(prompt_lines) if line.startswith("# A Backchain stage prints ShipLoop's Backchain planning guide")]
check_starts=[i for i,line in enumerate(prompt_lines) if line.startswith("_BACKCHAIN_CHECK_READS =")]
if len(comment_starts)!=1 or len(check_starts)!=1 or check_starts[0]<=comment_starts[0]: raise RuntimeError("ambiguous/missing current Backchain route prose")
prompt_span=(comment_starts[0]+1,check_starts[0])
guide_path="skills/shiploop/references/backchain-planning.md"
dep_audit_span=section_span(guide_path,"Dependency audit")
graph_format_span=section_span(guide_path,"Plan graph format")
checker_path="skills/shiploop/scripts/shiploop_backchain_graph.py"
checker=ast_nodes(checker_path,"main");checker_span=(checker.lineno,checker.end_lineno)
nav_path="skills/shiploop/scripts/shiploop_navigator.py"
nav_lines=load(nav_path).splitlines(keepends=True)
branch=[i for i,line in enumerate(nav_lines) if '_need("backchain_passes" not in keys, BACKCHAIN_PASSES_REASON)' in line]
if len(branch)!=1: raise RuntimeError(f"expected one retired-option refusal branch; got {len(branch)}")
branch_span=(branch[0]+1,branch[0]+1)
reason_span=assignment_span(nav_path,"BACKCHAIN_PASSES_REASON")
replacements=[
    added_anchor(prompt_path,"current Backchain stage route comment",prompt_span,"Applicable producer stages expose the ShipLoop planning guide and record-only check; the comment records that no standalone child or backchain_passes option remains."),
    added_anchor(guide_path,"Dependency audit section",dep_audit_span,"The complete retained dependency audit is ShipLoop planning guidance; it does not invoke the retired standalone skill."),
    added_anchor(guide_path,"Plan graph format section",graph_format_span,"The exact graph schema and invariants consumed by the record-only check now live in the ShipLoop guide."),
    added_anchor(checker_path,"main",checker_span,"Record-only backchain-check reads candidate graph bytes, validates them, and records a receipt without changing run state; this does not prove a live host read its locator."),
    added_anchor(nav_path,"saved-run retired option refusal",branch_span,"Saved state containing backchain_passes is rejected with BACKCHAIN_PASSES_REASON before normal state-key validation; no migration occurs."),
    added_anchor(nav_path,"BACKCHAIN_PASSES_REASON",reason_span,"The refusal identifies the retired run option and gives the fresh-run hint rather than silently migrating the saved run.")]
r13["anchors"].extend(replacements)
# Preserve the old R13 packet/field conclusions and acceptance checks; append retirement-specific facts only.
r13["status"] += "; standalone Backchain child/option retired"
r13["current_finding"] += " The standalone Backchain skill, card, suites, run option and child routes were later retired by owner decision. ShipLoop retains its dependency audit and record-only graph check; the library and graph format moved into ShipLoop. Neither source nor a receipt proves live host comprehension."
r13["changed_since_audit"] += " The old _BACKCHAIN_CHECK_READS excerpt materially changed: the symbol now points to ShipLoop's graph-format section and candidate-check wording. Separate current anchors locate the retained route, complete dependency audit, graph-format section, check implementation and old-run refusal."
r13["remaining_action"] += " Keep child/option recommendations retired; retain dependency audit and graph check as distinct ShipLoop duties. Do not infer host comprehension from source or receipt evidence."
r13["acceptance"].extend([
    "No current prompt, CLI or stage route offers the retired Backchain child or backchain_passes option; old saved state is refused with a fresh-run hint, not migrated.",
    "The retained guide's complete dependency-audit and graph-format sections are separately anchored; the applicable producer route points to the record-only checker, whose receipt does not qualify host comprehension.",
    "A live locator-reading or efficiency claim requires a fresh-context host trial; source and receipt checks alone do not qualify it."])
# The transport explanation names prepare() as well as argv(); bind that second mechanism explicitly.
prepare_path="test/shiploop_e2e/hosts.py"
prepare_node=ast_nodes(prepare_path,"prepare","CodexHost")
prepare_anchor=added_anchor(prepare_path,"CodexHost.prepare",(prepare_node.lineno,prepare_node.end_lineno),
    "The helper preserves UTF-8 prompt payload, replaces the command argument with stdin marker and returns that payload separately; this is transport behavior, not provider-served model attestation.")
m["qualification_transport"]["anchors"].append(prepare_anchor)
changes.append(dict(recommendation="qualification_transport",path=prepare_path,symbol="CodexHost.prepare",old_start=None,old_end=None,new_start=prepare_anchor["start"],new_end=prepare_anchor["end"],excerpt_unchanged=False,old_excerpt_sha256=None,new_excerpt_sha256=prepare_anchor["excerpt_sha256"],kind="added replacement anchor",current_claim=prepare_anchor["claim"]))

# Current publication repair is qualification apparatus, separate from the 22 ShipLoop recommendations.
harness_path="skills/test-harness/scripts/run-harness-hard-supervisor.py"
harness_writer=ast_nodes(harness_path,"write_hard_timeout_evidence")
harness_main=ast_nodes(harness_path,"main")
harness_tests_path="test/test-harness.test.py"
harness_tests=ast_nodes(harness_tests_path,"TimeoutEvidence")
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=="os" and n.func.attr=="link" for n in ast.walk(harness_writer))
writer_calls=[n for n in ast.walk(harness_main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=="write_hard_timeout_evidence"]
cleanup_calls=[n for n in ast.walk(harness_main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=="cleanup_group"]
assert len(writer_calls)==1 and any(writer_calls[0].lineno<n.lineno for n in cleanup_calls)
harness_repair_anchors=[
    added_anchor(harness_path,"write_hard_timeout_evidence",(harness_writer.lineno,harness_writer.end_lineno),"The timeout writer constructs complete bytes, writes/fsyncs a private same-directory staging inode, and atomically links without replacing the destination. Interrupted staging is not a final report; no blocked-filesystem or power-loss guarantee follows."),
    added_anchor(harness_path,"main",(harness_main.lineno,harness_main.end_lineno),"Once timeout is decided, the sole evidence attempt precedes deadline-consuming cleanup. Existing hard alarm, worker/deadline calculations, cancellation and timeout exit remain separate; elapsed_ms samples payload construction, not completed cleanup."),
    added_anchor(harness_tests_path,"TimeoutEvidence",(harness_tests.lineno,harness_tests.end_lineno),"Three regression methods run six real-supervisor barrier scenarios for cleanup ordering, empty/prefix interruption, completed publication and raced file/symlink refusal. Each requires reached barriers, actual timeout and owned-worker cleanup; original eight methods remain separate.")]
m["qualification_transport"]["anchors"].extend(harness_repair_anchors)
for a in harness_repair_anchors:
    changes.append(dict(recommendation="qualification_transport",path=a["path"],symbol=a["symbol"],old_start=None,old_end=None,new_start=a["start"],new_end=a["end"],excerpt_unchanged=False,old_excerpt_sha256=None,new_excerpt_sha256=a["excerpt_sha256"],kind="added replacement anchor",current_claim=a["claim"]))

# Record each newly added replacement separately; the old check-instruction anchor itself remains and is marked materially changed.
for a in replacements: changes.append(dict(recommendation="R13",path=a["path"],symbol=a["symbol"],old_start=None,old_end=None,new_start=a["start"],new_end=a["end"],excerpt_unchanged=False,old_excerpt_sha256=None,new_excerpt_sha256=a["excerpt_sha256"],kind="added replacement anchor",current_claim=a["claim"]))

assert len(m["recommendations"])==22 and [r["id"] for r in m["recommendations"]]==[f"R{i:02}" for i in range(1,23)]
assert [x["id"] for x in m["considerations_and_rules"] if re.fullmatch(r"C[1-8]",x["id"]) ]==[f"C{i}" for i in range(1,9)]
assert [x["id"] for x in m["considerations_and_rules"] if x["id"].startswith("CC")]==[f"CC{i}" for i in range(1,15)]
anchor_count=len(flat(m)); old_anchor_count=len(flat(old))
source_identity={"commit":head,"tree":current_tree,"checkout":str(repo),"claim_scope":"Frozen source only; no publication/CI/installed/deployed claim.","files":{p:sha(t) for p,t in sorted(cache.items())}}
m["source_identity"]=source_identity
plan=git("show",f"{head}:{PLAN_PATH}")
original_plan=plan
t_rows=[]
for match in re.finditer(r"^\| (T\d+) \| (R\d+) \| (.*?) \|$",plan,re.M):
    tid,rid,claim=match.groups(); rec=next(r for r in m["recommendations"] if r["id"]==rid)
    t_rows.append(dict(id=tid,recommendation=rid,acceptance_claim=claim,current_anchors=[dict(path=a["path"],symbol=a["symbol"],start=a["start"],end=a["end"],claim=a["claim"]) for a in rec["anchors"]]))
if [x["id"] for x in t_rows] != [f"T{i}" for i in range(1,53)]: raise RuntimeError("T1-T52 crosswalk missing, duplicated or reordered")
m["t_acceptance_crosswalk"]=t_rows
m["coverage"]={"recommendation_ids":[r["id"] for r in m["recommendations"]],"applicable_considerations":[x["id"] for x in m["considerations_and_rules"] if re.fullmatch(r"C[1-8]",x["id"])],"code_craft_rules":[x["id"] for x in m["considerations_and_rules"] if x["id"].startswith("CC")],"acceptance_ids":[x["id"] for x in t_rows],"anchor_count":anchor_count,"source_file_count":len(cache)}

# Build one stable-ID anchor inventory to bind each committed plan source link to its supporting current span.
def records(d):
    out=[]
    for r in d["recommendations"]: out.extend((r["id"],a) for a in r["anchors"])
    out.extend((d["schedule"]["id"],a) for a in d["schedule"]["anchors"])
    out.extend(("qualification_transport",a) for a in d["qualification_transport"]["anchors"])
    out.extend((x["id"],x["anchor"]) for x in d["considerations_and_rules"])
    return out
old_records=records(old);current_records=records(m)
plan=git("show",f"{head}:{PLAN_PATH}"); original_plan=plan
link_rows=[]
source_link_re=re.compile(r"\[([^\]]+)\]\(\.\./((?:skills|test)/[^)#]+)#L(\d+)\)")
def section_rec(text,pos):
    line=text[text.rfind("\n",0,pos)+1:text.find("\n",pos) if text.find("\n",pos)>=0 else len(text)]
    row=re.search(r"\|\s*T\d+\s*\|\s*(R\d{2})\s*\|",line)
    if row:return row.group(1)
    heads=list(re.finditer(r"^###\s+(R\d{2})\b",text[:pos],re.M))
    return heads[-1].group(1) if heads else None

def symbol_hint(label,path):
    suffix=label.split(" — ",1)[1].strip() if " — " in label else ""
    if suffix:return suffix
    if Path(path).name in label:
        tail=label.split(Path(path).name,1)[1].lstrip(": —")
        return tail.strip()
    return label.strip()

def choose_support(path,line,label,pos):
    candidates=[(rid,a) for rid,a in old_records if a["path"]==path and a["start"]<=line<=a["end"]]
    if not candidates:raise RuntimeError(f"no old source-map anchor supports committed link {path}:L{line}")
    hint=symbol_hint(label,path)
    exact=[x for x in candidates if x[1]["symbol"]==hint]
    if exact:candidates=exact
    rid_context=section_rec(original_plan,pos)
    contextual=[x for x in candidates if x[0]==rid_context] if rid_context else []
    if contextual:candidates=contextual
    if len(candidates)>1:
        at_link=[x for x in candidates if x[1]["start"]==line]
        if len(at_link)==1:candidates=at_link
        elif at_link:candidates=at_link
        else:
            words=lambda value:set(re.findall(r"[a-z0-9]+",value.lower()))-{"and","the","with","for","from","this","that","its","one","all","current","source","actual","code","function"}
            hint_words=words(hint)
            scores=[(len(hint_words & words(a.get("claim",""))),rid,a) for rid,a in candidates]
            best=max(x[0] for x in scores)
            ranked=[(rid,a) for score,rid,a in scores if score==best and best>0]
            if len(ranked)==1:candidates=ranked
            else:
                smallest=min(x[1]["end"]-x[1]["start"] for x in candidates)
                narrow=[x for x in candidates if x[1]["end"]-x[1]["start"]==smallest]
                if len(narrow)==1:candidates=narrow
    # A repeated anchor is selectable only when the retained current spans prove the same exact scope.
    signatures={(rid,a["symbol"],a["start"],a["end"]) for rid,a in candidates}
    if len(signatures)>1:
        scopes={(a["symbol"],a["start"],a["end"]) for _,a in candidates}
        if len(scopes)==1:candidates=candidates[:1]
        else:raise RuntimeError(f"ambiguous supporting anchor for {label!r} at {path}:L{line}: {sorted(signatures)}")
    rid,prior=candidates[0]
    matches=[(crid,a) for crid,a in current_records if crid==rid and a["path"]==path and a["symbol"]==prior["symbol"]]
    if not matches:
        matches=[(crid,a) for crid,a in current_records if a["path"]==path and a["symbol"]==prior["symbol"]]
    claim_matches=[x for x in matches if x[1].get("claim")==prior.get("claim")]
    if claim_matches:matches=claim_matches
    if rid_context:
        in_context=[x for x in matches if x[0]==rid_context]
        if in_context:matches=in_context
    unique={(crid,a["start"],a["end"]) for crid,a in matches}
    if len(unique)>1:raise RuntimeError(f"ambiguous current anchor for {label!r}: {sorted(unique)}")
    if not matches:raise RuntimeError(f"old source anchor has no current match: {rid} {path} {prior['symbol']}")
    crid,current=matches[0]
    return crid,current

def rewrite_source_link(mt):
    label,path,old_line=mt.group(1),mt.group(2),int(mt.group(3))
    rid,anchor=choose_support(path,old_line,label,mt.start())
    new_line=anchor["start"]
    new_label=label
    display=re.match(r"^(.*?\.py):(\d+)(.*)$",label)
    if display:
        filepart,_display_line,tail=display.groups()
        if filepart!=Path(path).name:raise RuntimeError(f"visible filename label mismatch: {filepart} -> {path}")
        new_label=f"{filepart}:{new_line}{tail}"
    link_rows.append(dict(recommendation=rid,path=path,symbol=anchor["symbol"],old_line=old_line,new_line=new_line,anchor_start=anchor["start"],anchor_end=anchor["end"],old_label=label,new_label=new_label,status="mapped"))
    return f"[{new_label}](../{path}#L{new_line})"
# The original committed plan is traversed exactly once; href and visible filename:line change in the same callback.
plan=source_link_re.sub(rewrite_source_link,original_plan)
original_source_links=len(link_rows)

# Rebuild the human draft's current-source paragraph and remove stale current-status wording after the link pass.
prior_exact=sum(c.get("kind")=="exact relocation" or (c.get("kind")=="materially changed span" and c.get("excerpt_unchanged")) for c in changes if c.get("old_start") is not None)
relocated=sum(c.get("kind")=="exact relocation" and c.get("old_start") is not None and c.get("old_start")!=c.get("new_start") for c in changes)
material=sum(c.get("kind")=="materially changed span" for c in changes if c.get("old_start") is not None); deleted=sum(c.get("kind","").startswith("deleted") for c in changes)
added=sum(c["kind"]=="added replacement anchor" for c in changes)
basis=(f"{old_anchor_count} prior anchors plus {added} current anchors" if deleted==0 else f"{old_anchor_count} prior anchors, less {deleted} deleted excerpts, plus {added} current anchors")
intro=(f"Current source checked at frozen `{head}` (tree `{current_tree}`). The updated source map resolves **{anchor_count} anchors across {len(cache)} files**: {basis}. It retains {prior_exact} exact prior excerpts, relocates {relocated} anchors, records {material} materially changed spans, and marks {deleted} deleted spans. R13 retirement and other changed duties are interpreted in the adjacent [comparison](anchor-changes.json). This frozen-source map makes no publication, CI, installed-host or deployed claim; historical qualifications remain pinned at their prior sources.")
plan,n=re.subn(r"^Current source checked at .*?Earlier R05/R07/R08/R19/R21 evidence stays frozen at its actual source\.",intro,plan,count=1,flags=re.M)
if n!=1:raise RuntimeError("could not uniquely replace plan current-source paragraph")
plan=plan.replace("All 22 recommendation IDs, eight considerations, fourteen Code craft rules and T1–T52 references remain accounted for.","All 22 recommendation IDs, eight considerations, fourteen Code craft rules and T1–T52 acceptance references remain accounted for in the updated source map.")
plan=plan.replace("At that main checkpoint, the published package is still skill-craft **2.42.1 / ShipLoop 1.37.1**. R19 and R16 are source implementations pending publication; local merge, remote publication, installed-host exposure and deployed acceptance remain separate claims.","The package-version statement from the preceding draft refers only to its historical main checkpoint. This frozen-source map makes no current publication claim; source identity, release output, publication, CI, installed-host exposure and deployed acceptance remain separate evidence.")
pattern=r"The later Backchain release corrects child prepare/freeze instructions and ships ShipLoop .*?Its post-fix live behavior remains unmeasured\."
retirement=("The later Backchain release, opt-in decision and graph-input wording are historical. The owner subsequently retired the standalone Backchain skill, card, suites, run option and child routes. ShipLoop retains its dependency audit and record-only `backchain-check`; the graph library moved into ShipLoop and the graph format moved into its planning guide. Old saved runs carrying `backchain_passes` are refused, not migrated. The owner waived a live round for this retirement. The current R13 map separates retained and retired duties; source and receipts do not establish live host comprehension. Earlier qualification remains pinned to pre-retirement sources.")
plan,n=re.subn(pattern,retirement,plan,count=1,flags=re.S)
if n!=1:raise RuntimeError("could not uniquely replace stale Backchain status paragraph")
plan=re.sub(r"The current \d+-anchor map and R16 checks are in the \[R16 record\]\(([^)]+)\)\.",lambda x:f"The frozen-source {anchor_count}-anchor map and comparison are in adjacent `source-map.json` and `anchor-changes.json`; historical R16 checks remain in the [R16 record]({x.group(1)}).",plan)
plan=plan.replace("The [current source map](shiploop-implement-prompt-audit-evidence/r16-20261115/source-map.json) holds every supporting span, excerpt hash and relevant decision commit. Its [comparison](shiploop-implement-prompt-audit-evidence/r16-20261115/anchor-changes.json) distinguishes unchanged excerpts from content that required renewed interpretation. The earlier maps remain frozen.","The adjacent updated `source-map.json` holds current spans, excerpt hashes and relevant decisions. The adjacent `anchor-changes.json` distinguishes exact relocation, materially changed spans and revised excerpts. Earlier qualification maps remain frozen.")

# Verify symbol ownership independently from excerpt hashes for each materially changed AST-backed anchor.
def find_current(rid,symbol,path):
    found=[a for arid,a in current_records if arid==rid and a["symbol"]==symbol and a["path"]==path]
    if len(found)!=1:raise RuntimeError(f"expected one current anchor for {rid} {symbol}; got {len(found)}")
    return found[0]
for rid,symbol,path,expected in [
    ("R13","_BACKCHAIN_CHECK_READS","skills/shiploop/scripts/shiploop_prompts.py",assignment_span("skills/shiploop/scripts/shiploop_prompts.py","_BACKCHAIN_CHECK_READS")),
    ("R04","_prompt_parts","skills/shiploop/scripts/shiploop_prompts.py",(ast_nodes("skills/shiploop/scripts/shiploop_prompts.py","_prompt_parts").lineno,ast_nodes("skills/shiploop/scripts/shiploop_prompts.py","_prompt_parts").end_lineno)),
    ("qualification_transport","CodexHost.argv","test/shiploop_e2e/hosts.py",(ast_nodes("test/shiploop_e2e/hosts.py","argv","CodexHost").lineno,ast_nodes("test/shiploop_e2e/hosts.py","argv","CodexHost").end_lineno)),
    ("qualification_transport","CodexHost.prepare","test/shiploop_e2e/hosts.py",(ast_nodes("test/shiploop_e2e/hosts.py","prepare","CodexHost").lineno,ast_nodes("test/shiploop_e2e/hosts.py","prepare","CodexHost").end_lineno))]:
    a=find_current(rid,symbol,path)
    if (a["start"],a["end"])!=expected:raise RuntimeError(f"AST binding mismatch {rid} {symbol}: map {(a['start'],a['end'])}, AST {expected}")

# Independently confirm that the composite R08 span contains BOTH referenced function definitions.
pair=find_current("R08","answer_key and matching_yes","skills/shiploop/scripts/shiploop_check.py")
for name in ("answer_key","matching_yes"):
    node=ast_nodes(pair["path"],name)
    if not (pair["start"]<=node.lineno<=node.end_lineno<=pair["end"]):
        raise RuntimeError(f"composite anchor omits {name}: {pair['start']}:{pair['end']}")

# Mark links intentionally removed from the human draft's retired historical paragraph; the transformation itself was one pass.
def extract_source_links(text):
    return [dict(label=x.group(1),path=x.group(2),line=int(x.group(3))) for x in source_link_re.finditer(text)]
final_links=extract_source_links(plan)
from collections import Counter
final_counter=Counter((x["label"],x["path"],x["line"]) for x in final_links)
for row in link_rows:
    key=(row["new_label"],row["path"],row["new_line"])
    if final_counter[key]: final_counter[key]-=1; row["status"]="retained"
    else: row["status"]="removed with superseded prose"
if any(final_counter.values()):raise RuntimeError("final plan contains links not produced by the one-pass source-link mapper")
link_updates=[r for r in link_rows if r["status"]!="retained" or r["old_line"]!=r["new_line"] or r["old_label"]!=r["new_label"]]
for row in link_rows:
    if not (row["anchor_start"]<=row["new_line"]<=row["anchor_end"]):raise RuntimeError(f"mapped link outside supporting current span: {row}")

# Check each emitted target at its frozen revision and independently tie it to the selected current anchor record.
for link in final_links:
    support=next((r for r in link_rows if r["status"]=="retained" and r["path"]==link["path"] and r["new_line"]==link["line"] and r["new_label"]==link["label"]),None)
    if support is None:raise RuntimeError(f"source link has no responsibility anchor: {link}")
    blob=git("show",f"{head}:{link['path']}"); lines=blob.splitlines()
    if not 1<=link["line"]<=len(lines):raise RuntimeError(f"source link line out of bounds: {link}")
    if support["recommendation"] not in {r for r in m["coverage"]["recommendation_ids"]}|{"Improve-schedule","qualification_transport"}|{x["id"] for x in m["considerations_and_rules"]}:
        raise RuntimeError(f"unrecognized recommendation for source link: {support}")
# Ensure visible filename:line labels and relative targets agree after the single rewriting callback.
for link in final_links:
    display=re.match(r"^(.*?\.py):(\d+)(.*)$",link["label"])
    if display and (display.group(1)!=Path(link["path"]).name or int(display.group(2))!=link["line"]):
        raise RuntimeError(f"visible label does not match href: {link}")
all_targets=[(r["path"],r["line"]) for r in final_links]

comparison=dict(previous_source=old_source,current_source=head,current_tree=current_tree,old_anchor_count=old_anchor_count,new_anchor_count=anchor_count,source_files=len(cache),exact_excerpts_retained=prior_exact,relocated=relocated,materially_changed=material,deleted=deleted,added_replacements=added,changes=changes)
m["source_identity"]=source_identity
(out/"source-map.json").write_text(json.dumps(m,indent=2)+"\n")
(out/"anchor-changes.json").write_text(json.dumps(comparison,indent=2)+"\n")
(out/"plan-with-current-links.md").write_text(plan)
(out/"plan-link-changes.json").write_text(json.dumps(dict(source=head,source_tree=current_tree,updates=link_updates,links=link_rows,source_targets=len(all_targets),target_file_hashes={p:sha(load(p)) for p in sorted({target_path for target_path,_line in all_targets})}),indent=2)+"\n")
(out/"handoff.json").write_text(json.dumps(dict(source_commit=head,source_tree=current_tree,old_anchor_count=old_anchor_count,new_anchor_count=anchor_count,source_files=len(cache),recommendations=len(m["recommendations"]),considerations=len(m["coverage"]["applicable_considerations"]),code_craft_rules=len(m["coverage"]["code_craft_rules"]),acceptance_T_ids=len(m["coverage"]["acceptance_ids"]),exact_excerpts_retained=prior_exact,relocated=relocated,materially_changed=material,deleted=deleted,replacement_anchors=added,link_updates=len(link_updates),source_link_targets=len(all_targets),changed_duties={"R04":"Producer assembly no longer offers the retired Backchain child/optional audit child; applicable guide/check route, Code craft and stage rules remain.","R13":"Preserves full-packet and safe durable-field acceptance; adds distinct retired child/option, retained dependency audit, graph format, record-only check and refusal/no-migration claims."},limitations=["Prior source qualification remains pinned before retirement; the owner waived a new live round.","This generated map is frozen-source evidence only; no publication, CI, installed-host or deployed claim."],artifacts=["source-map.json","anchor-changes.json","plan-link-changes.json","plan-with-current-links.md","handoff.json"]),indent=2)+"\n")
print(json.dumps(dict(source=head,tree=current_tree,old_anchors=old_anchor_count,new_anchors=anchor_count,files=len(cache),exact=prior_exact,relocated=relocated,changed=material,deleted=deleted,added=added,links=len(link_updates),targets=len(all_targets))))
