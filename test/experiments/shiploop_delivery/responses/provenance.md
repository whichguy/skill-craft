# Response provenance

These raw responses were produced by actual independent subagents in the implementing task, each spawned with `fork_turns: none`. Each A/B/B2 interpreter received one frozen packet, the same read-only instruction and 180-word response guideline, and authorization to write only its named response using apply_patch. The three exploratory C/C2 interpreters received the same recovery-oriented questions as each other, without that word guideline. They were told not to inspect oracles or other responses, execute project work, call targets, or submit runtime callbacks. The root retained the actual replies and an independent reviewer graded the saved text. No synthetic expected answer is labeled as a model response.

Tool-call/session transcripts remain in the originating task, not duplicated here. Exact provider/model identity, per-response timestamps, token counts, and wall times were not captured; this is not a cross-model benchmark. These task labels identify the originating interpreters, not deployment receipts. Raw replies are unedited; interpretation-only restrictions sometimes led to blocked classifications that are analyzed separately from the fixed consumer-scope rubric.

| Raw response relative to this directory | Originating task label |
| --- | --- |
| A/ambiguous-existing-hosted-ui-r1.md | /root/teach_a_ambiguous_1 |
| A/ambiguous-existing-hosted-ui-r2.md | /root/teach_a_ambiguous_2 |
| A/approved-private-sync-r1.md | /root/teach_a_sync_1 |
| A/approved-private-sync-r2.md | /root/teach_a_sync_2 |
| A/explicit-source-only-r1.md | /root/teach_a_source_1 |
| A/explicit-source-only-r2.md | /root/teach_a_source_2 |
| A/necessary-delivery-missing-authority-r1.md | /root/teach_a_authority_1 |
| A/necessary-delivery-missing-authority-r2.md | /root/teach_a_authority_2 |
| A/identity-without-visual-verification-r1.md | /root/teach_a_visual_1 |
| A/identity-without-visual-verification-r2.md | /root/teach_a_visual_2 |
| A/login-after-upload-r1.md | /root/teach_a_login_1 |
| A/login-after-upload-r2.md | /root/teach_a_login_2 |
| B/ambiguous-existing-hosted-ui-r1.md | /root/teach_b_ambiguous_1 |
| B/ambiguous-existing-hosted-ui-r2.md | /root/teach_b_ambiguous_2 |
| B/approved-private-sync-r1.md | /root/teach_b_sync_1 |
| B/approved-private-sync-r2.md | /root/teach_b_sync_2 |
| B/explicit-source-only-r1.md | /root/teach_b_source_1 |
| B/explicit-source-only-r2.md | /root/teach_b_source_2 |
| B/necessary-delivery-missing-authority-r1.md | /root/teach_b_authority_1 |
| B/necessary-delivery-missing-authority-r2.md | /root/teach_b_authority_2 |
| B/identity-without-visual-verification-r1.md | /root/teach_b_visual_1 |
| B/identity-without-visual-verification-r2.md | /root/teach_b_visual_2 |
| B/login-after-upload-r1.md | /root/teach_b_login_1 |
| B/login-after-upload-r2.md | /root/teach_b_login_2 |
| B2/approved-private-sync-r1.md | /root/teach_b2_sync_1 |
| B2/approved-private-sync-r2.md | /root/teach_b2_sync_2 |
| B2/necessary-delivery-missing-authority-r1.md | /root/teach_b2_authority_1 |
| B2/necessary-delivery-missing-authority-r2.md | /root/teach_b2_authority_2 |
| C/login-after-upload-recovery.md | /root/teach_c_login |
| C/post-plan-candidate-change-recovery.md | /root/teach_c_replan |
| C2/post-plan-candidate-change-current-renderer.md | /root/teach_c2_replan |
