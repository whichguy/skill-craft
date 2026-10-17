# Printed text and packet file per stage, before and after unit U10

Offline `node-fix-bug`, `packets.py --offline --text-dir` at the stated run-dir length (83: the reference install; 163: the live run), CLI path 96,
render of the INT tip 5e0ef0d0 (before) and of this branch's tree (after). `printed` is what the host prints (a head when the packet file passes
PRINT_LIMIT 16,000); `whole` is the packet file. Reasons per row are in `render-diff-*.txt` (every added and removed line with its size and its allowlist entry).

## inline, run dir 83

| stage | printed before | printed after | delta | whole before | whole after | delta | form after |
|---|--:|--:|--:|--:|--:|--:|---|
| step-plan | 19988 | 19961 | -27 | 23351 | 23140 | -211 | head |
| step-plan-improve | 2713 | 2713 | +0 | 2687 | 2687 | +0 | whole |
| test-spec | 14759 | 14548 | -211 | 14733 | 14522 | -211 | whole |
| test-spec-improve | 1945 | 1945 | +0 | 1919 | 1919 | +0 | whole |
| validate-existing | 15283 | 15072 | -211 | 15257 | 15046 | -211 | whole |
| implement | 15763 | 15736 | -27 | 18286 | 18075 | -211 | head |
| implement-improve | 2654 | 2654 | +0 | 2628 | 2628 | +0 | whole |
| test | 18239 | 18203 | -36 | 20470 | 20250 | -220 | head |
| document | 14116 | 13905 | -211 | 14090 | 13879 | -211 | whole |
| verify | 18188 | 18161 | -27 | 20408 | 20197 | -211 | head |
| carry-forward | 18028 | 18001 | -27 | 22179 | 21968 | -211 | head |
| carry-forward-improve | 2642 | 2642 | +0 | 2616 | 2616 | +0 | whole |
| total (12 packets) | 144318 | 143541 | -777 (-0.54%) | 158624 | 156927 | -1697 (-1.07%) | |

## ask-agent, run dir 83

| stage | printed before | printed after | delta | whole before | whole after | delta | form after |
|---|--:|--:|--:|--:|--:|--:|---|
| step-plan | 19449 | 19422 | -27 | 26742 | 26531 | -211 | head |
| step-plan-improve | 2713 | 2713 | +0 | 2687 | 2687 | +0 | whole |
| test-spec | 12856 | 12829 | -27 | 16301 | 16090 | -211 | head |
| test-spec-improve | 1945 | 1945 | +0 | 1919 | 1919 | +0 | whole |
| validate-existing | 12562 | 12535 | -27 | 16825 | 16614 | -211 | head |
| implement | 17217 | 17190 | -27 | 21386 | 21175 | -211 | head |
| implement-improve | 2654 | 2654 | +0 | 2628 | 2628 | +0 | whole |
| test | 18239 | 18203 | -36 | 22038 | 21818 | -220 | head |
| document | 15684 | 15473 | -211 | 15658 | 15447 | -211 | whole |
| verify | 18608 | 18581 | -27 | 22396 | 22185 | -211 | head |
| carry-forward | 19294 | 19267 | -27 | 25013 | 24802 | -211 | head |
| carry-forward-improve | 2642 | 2642 | +0 | 2616 | 2616 | +0 | whole |
| total (12 packets) | 143863 | 143454 | -409 (-0.28%) | 176209 | 174512 | -1697 (-0.96%) | |

## inline, run dir 163

| stage | printed before | printed after | delta | whole before | whole after | delta | form after |
|---|--:|--:|--:|--:|--:|--:|---|
| step-plan | 19774 | 19976 | +202 | 24871 | 24580 | -291 | head |
| step-plan-improve | 3033 | 3033 | +0 | 3007 | 3007 | +0 | whole |
| test-spec | 14216 | 15828 | +1612 | 16093 | 15802 | -291 | whole |
| test-spec-improve | 2265 | 2265 | +0 | 2239 | 2239 | +0 | whole |
| validate-existing | 13922 | 13895 | -27 | 16617 | 16326 | -291 | head |
| implement | 16723 | 16696 | -27 | 19246 | 18955 | -291 | head |
| implement-improve | 2974 | 2974 | +0 | 2948 | 2948 | +0 | whole |
| test | 19759 | 19723 | -36 | 21990 | 21690 | -300 | head |
| document | 15556 | 15265 | -291 | 15530 | 15239 | -291 | whole |
| verify | 19548 | 19521 | -27 | 21768 | 21477 | -291 | head |
| carry-forward | 19468 | 19441 | -27 | 23699 | 23408 | -291 | head |
| carry-forward-improve | 2962 | 2962 | +0 | 2936 | 2936 | +0 | whole |
| total (12 packets) | 150200 | 151579 | +1379 (+0.92%) | 170944 | 168607 | -2337 (-1.37%) | |

## ask-agent, run dir 163

| stage | printed before | printed after | delta | whole before | whole after | delta | form after |
|---|--:|--:|--:|--:|--:|--:|---|
| step-plan | 19260 | 19233 | -27 | 28262 | 27971 | -291 | head |
| step-plan-improve | 3033 | 3033 | +0 | 3007 | 3007 | +0 | whole |
| test-spec | 14216 | 14189 | -27 | 17661 | 17370 | -291 | head |
| test-spec-improve | 2265 | 2265 | +0 | 2239 | 2239 | +0 | whole |
| validate-existing | 13922 | 13895 | -27 | 18185 | 17894 | -291 | head |
| implement | 18177 | 18150 | -27 | 22346 | 22055 | -291 | head |
| implement-improve | 2974 | 2974 | +0 | 2948 | 2948 | +0 | whole |
| test | 19759 | 19723 | -36 | 23558 | 23258 | -300 | head |
| document | 13349 | 13322 | -27 | 17098 | 16807 | -291 | head |
| verify | 19968 | 19941 | -27 | 23756 | 23465 | -291 | head |
| carry-forward | 19884 | 19857 | -27 | 26533 | 26242 | -291 | head |
| carry-forward-improve | 2962 | 2962 | +0 | 2936 | 2936 | +0 | whole |
| total (12 packets) | 149769 | 149544 | -225 (-0.15%) | 188529 | 186192 | -2337 (-1.24%) | |

At 163 the inline test-spec packet falls from 16,093 to 15,802 characters, under PRINT_LIMIT, so it prints whole (+1,612 printed); the inline step-plan head
gains the 229-character Knowledge files line it had no room for (+202, 19,976 of 20,000). Neither is new text. The head table `packet_head_table.json` at 163
is not the gate here (6 of 12 inline and 7 of 12 ask-agent stages already print more than its 163 values at the base; U7 re-measured the reference install).
