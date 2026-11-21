# gb-blind-catchup report (Grokbot-local, blind acceptance suite)

Elapsed: 13:19:46 to about 13:42 (about 22 minutes). Per-item outputs: out1 (step 1), out2 (after corrections), out3 (final 42), out4 (the other 73) in this folder.

## Result
Final, each item run alone: 39 of the 42 pass. The 3 still failing are U-4, C-75, C-77, all ASSERTION (below). The other 73 items (73 = 115 - 42) were also rerun alone after the corrections: 73 of 73 pass (including U-3, U-9, C-9, C-12, C-30, C-60, C-95, C-100). So 112 of 115 observed passing.

## Step 1 (rerun of the 42 alone, no change to the adapter beyond the by-hand spoken())
14 passed: U-10, U-13, U-15, C-5, C-36, C-78, C-80, C-81, C-83, C-86, C-87, C-88, C-89, C-93.
28 failed again. (Those 14 were the busy machine's, or items that never depend on the cause below.)

## Corrections, in order made
1. EXECUTION, the adapter acts faster than the page lets it (about 9 min from first look to items passing).
   Cause: public/app.js `command()` returns at once when `busy` (line 419) and `render()` resets the composer to the stored draft when the open chat changes (line 156), and `sendRequest` ignores sends while busy (line 465). `Page.click` returned right after dispatching the click, so the next `fill`/`send` landed while the click's POST + refresh was still running: the typed text was wiped or the send ignored, and no message ever appeared ("A new assistant reply appears", observation `[]`). A person waits for the screen to settle.
   Change: in `browserTools` the fetch hook now counts in-flight same-origin requests (a response the test holds, drop/abort/hold gates, is not counted); new in-page `settle(start)` waits 70 ms, then until no counted request is in flight and the document has had no mutation for 90 ms, capped at 1.6 s; `__acceptance.click` uses it and `quiet()` was added; `Page.key` calls `quiet` after any key that does not end in `Tab`.
   Unlocked (item passed after it): U-1, U-2, U-5, U-6, U-7, U-8, U-14, C-6, C-22, C-24, C-29, C-32, C-39, C-40, C-42, C-46, C-48, C-53, C-68, C-84, C-90, C-91, C-92, C-94 (24 items). The task-waiting family ("shows N finished step(s)", "reaches Completed", "Find accessible {...}", C-22's coverage, C-40's "No conversation contains") were all downstream of the lost first send.
2. EXECUTION, the driver's window never counts as focused (about 8 min, includes two dead ends).
   Cause: the driver is an accessory app and macOS will not activate it while another app (here the Claude app, `lsappinfo front`) is in front. Measured: `NSApp.isActive=false`, `window.isKeyWindow=false`, in-page `document.hasFocus()=false`, `:focus` and `:focus-visible` both false on the focused input, computed outline `none`, although public/style.css:39 gives `:focus-visible` a 2px outline. `NSApp.activate(ignoringOtherApps:)`, `.regular` policy and `makeKeyAndOrderFront` did not change it (tried, reverted). Earlier runs had focus only by luck of launch order.
   Change (webkit.swift): `final class ActiveWindow: NSWindow` overriding isKeyWindow/isMainWindow/canBecomeKey/canBecomeMain to true, used in place of NSWindow, and posting didBecomeKey/didBecomeMain once in `Browser.init`. After it `document.hasFocus()` is true without stealing the user's activation.
   Unlocked: C-99 (checked: fails 3 of 3 before, passes after). It may also be what keeps U-15 stable.

(The by-hand `spoken()` change in name() is kept unchanged.)

## ASSERTION list (suite.cjs not touched; adapter cannot fix)
- U-4 (suite.cjs:637, via helper `originalDiscussion` at 626-637, called at 1639 after `newBot('Planning')` at 1637): expects the reply article `article('Message from Assistant', chat)`, but the open bot is "Planning". Spec ratchet/spec.md:20 and :193 say the article is `Message from <bot name>`; the product (public/app.js:196, speaker = bot name) is right. Evidence the rest is sound: a throwaway copy of suite.cjs with only that string changed to `Message from Planning` passed U-4 (8.6 s). The copy was deleted.
- C-77 (suite.cjs:1138, helper `openDiscussion` 77-92): after reject in one conversation and a dropped-response confirm in a new one, both conversations contain the same prompt text `set the status of ORD-1001 to closed`; `openDiscussion` opens the first conversation in the list that contains the marker. The product lists oldest first (conversations "…closed" and "…closed (2)"), so it opens the rejected one and `Change result` says "Rejected", while the test expects the applied one. Spec gives no list order (grep of spec for newest/oldest/order: none). Evidence: a throwaway copy of suite.cjs iterating the list in reverse passed C-77 entirely (5.4 s); copy deleted. Observed in the product: after the dropped confirm the page shows "Applied · The approved changes were saved. ORD-1001 status: open → closed", correct.
- C-75 (suite.cjs:1099-1105): opens a second window for the same person (`other`), starts a new conversation in each window, and confirms a creation in both at once, expecting both to succeed. The product keeps one open conversation per person on the server (lib/chat.js:139-143: a command whose bot/chat differs from the person's current one gets 409 "The open conversation changed. Review the current screen and try again."). Probe: of two simultaneous confirms from the two windows, one returned 409 and the other 200 (ORD-1005 for the second). Spec C-75 (spec.md:373-375) says only "Successful overlapping creations cannot receive the same ID"; it does not require both windows to succeed, and says nothing about multiple windows. Also `other.newChat()` (line 1103) already hits the same 409 when the second window has not refreshed (polls every 1.4 s). I tried a retry-after-alert in `Page.newChat`; it only moved the failure to line 1106, so I removed it. Not a clause violation as far as I can tell.

## PRODUCT list
None found. No observed behaviour contradicted a clause.

## Still failing, out of time
None unexplained. Remaining 3 are the ASSERTION items above.

## Judgement calls to inspect when reading the diff
- `settle` adds about 100 to 200 ms to every click; a 1.6 s cap keeps tests that hold a request from hanging. Held requests (arm 'hold'/'drop'/'abort') are excluded from the in-flight count so the tests that hold a response still see the in-between state; these tests (U-10, C-68, C-77 first half, C-84) passed.
- `Page.key` now waits after Enter/Space/Shift+Enter. Tab and Option+Tab skip it.
- ActiveWindow makes every driver window report key even when two drivers coexist (C-75, U-? with two pages); it does not touch OS activation.
- One git write was run by me: `git checkout acceptance/webkit.swift` to drop a failed experiment (the file had no earlier by-hand change; the result was then re-edited as correction 2). No commit, no add.

## git diff --stat
 acceptance/adapter.cjs  | 71 +++++++++++++++++++++++++++++++++++++------------
 acceptance/webkit.swift | 14 +++++++++-
 2 files changed, 67 insertions(+), 18 deletions(-)
(The adapter count includes the earlier by-hand spoken() change, about 6 lines.)
