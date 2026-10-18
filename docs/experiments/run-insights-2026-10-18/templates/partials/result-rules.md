<!-- partial: result-rules. The "Fill the template" line and the blocked shape (navigator _result_contract_lines),
verbatim except that the awaiting shape is printed instead of pointing at reference#blocked (E1). -->
Fill the form: each key once, every placeholder (<...>) replaced, "outcome" and "summary" top-level; ShipLoop refuses a form with a placeholder left. Any other outcome keeps headline and evidence_refs and drops the other fields:
blocked: {"outcome": "blocked", "blocked_by": "user | access | external", "summary": "<what stopped the work>"}; only when nothing can proceed without a person (blocked_by user or access), add "awaiting": {"kind": "answer", "question": "<one decision>", "options": ["<a>", "<b>"], "no_default": "<why no recorded default would do>"}
