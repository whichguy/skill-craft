"""For one run folder: the request sentences, the sentences and test IDs product-acceptance cites, and which cited IDs
appear in a passing line of ShipLoop's own verify records (RUN/tests/*-verify*.md)."""
import json, re, sys
from pathlib import Path
out = Path(sys.argv[1]); run = next(out.glob(".shiploop-runs/*/run"))
sentences = sorted(set(re.findall(r"\bS(\d+)\b", (run / "request.md").read_text().split("## Verbatim")[-1])), key=int)
pa = None
for f in sorted((run / "results").glob("*.md")):
    m = re.search(r"```shiploop-state\n(.*?)\n```", f.read_text(), re.S)
    if m and json.loads(m.group(1)).get("stage") == "product-acceptance":
        pa = json.loads(m.group(1))["result"]
text = (pa or {}).get("summary", "")
cited_s = sorted(set(re.findall(r"\bS(\d+)\b", text)), key=int)
ids = sorted(set(re.findall(r"\b(?:TC|ST|SYS|SC|AC)-[A-Z0-9]+(?:-[0-9]+)?\b", text)))
verify = "\n".join(p.read_text(errors="replace") for p in sorted((run / "tests").glob("*-verify*.md")))
anyrec = "\n".join(p.read_text(errors="replace") for p in sorted((run / "tests").glob("*.md")))
in_verify = [i for i in ids if re.search(rf"\b{re.escape(i)}\b", verify)]
in_any = [i for i in ids if re.search(rf"\b{re.escape(i)}\b", anyrec)]
print(f"{out.name}: request sentences S{','.join(sentences)}; product-acceptance cites S{','.join(cited_s)}; "
      f"unverified {len((pa or {}).get('unverified') or [])}")
print(f"  cited test IDs {len(ids)}: {' '.join(ids)}")
print(f"  in verify records: {len(in_verify)}; in any test record: {len(in_any)}; in none: {' '.join(sorted(set(ids) - set(in_any))) or '-'}")
