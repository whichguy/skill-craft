<!-- partial: outcome-send-back (N5: replaces revise). {{send_back_target}} comes from stage_spec (step-plan for test-spec
through verify; system-test-author for system-test; release-plan for release-verify); {{send_backs_left}} is the budget,
checked at --check-only too (N5). When to send back is the loop's Repeat text, worded once in loops. -->
- send-back: a record {{send_back_target}} wrote is wrong or cannot be met here; {{send_back_target}} reruns with this result as its evidence ({{send_backs_left}} left for this item; at 0, report blocked with a decision). Keys: outcome, headline, summary (which record is wrong, and the evidence), evidence_refs.
