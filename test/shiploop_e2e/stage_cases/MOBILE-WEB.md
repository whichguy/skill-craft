# Prospective responsive web and native mobile UI cases

**Status:** proposals for future UI packet diagnostics. These cases are not registered in the stage suite or executed, and add no ShipLoop runtime prompt, default or gate.

## Store design choices separately from execution evidence

During `step-plan`, record product-specific adaptation choices and their rationale in named sections of the generated `docs/shiploop/architecture.md`, such as **Responsive web behavior** and, when a native app exists, **Native mobile adaptation**. Include the actual breakpoint decisions and what changes there. Select the accepted sections and applicable values in the implementation criteria; later test specifications and implementation follow that selection. A test case may refer to its criterion or shared setup without duplicating the full design record. The architecture decision records intended choices; run evidence records whether a check was planned, completed, failed or unavailable, with its product identity, environment, interactions and captures.

Choose widths from the product's actual breakpoints: for each breakpoint `B` under review, observe `B−1`, `B` and `B+1` CSS pixels. Add narrow, medium and wide contexts as useful. `320`, `390`, `768` and `1440` CSS pixels are illustrative contexts, not universal breakpoints; `320` CSS pixels is also the WCAG reflow test width. Ordinary content should reflow without two-dimensional page scrolling, while an essential two-dimensional control such as a board may need local two-axis exploration. [WCAG 2.2 Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) describes that distinction. For independently operable web controls, assess WCAG 2.2's 24-by-24 CSS-pixel minimum or its spacing exceptions; 44-by-44 belongs to the enhanced criterion and is not a universal minimum. [WCAG 2.2 Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum)

## Candidate scenarios

### `responsive-web-shell`

At a chosen narrow width, verify that chat navigation still reaches one selected conversation and its composer. Check the product's actual breakpoints and confirm primary controls remain reachable without unintended page-level horizontal overflow. Capture CSS-pixel viewport and browser engine/version with the interaction and focus observations.

For example, a 390-pixel capture may look fine while the rail and conversation overlap at the product's 768-pixel transition. A few nominal phone and desktop widths do not qualify every actual transition.

### `web-input-and-reflow`

At 320 CSS pixels or 400% zoom from 1280 CSS pixels, verify ordinary content and long, empty and error states reflow with actions reachable. Tap primary controls and confirm adjacent hit targets remain distinct; keyboard focus stays visible. On a real mobile browser or suitable simulator, open and close the OS keyboard and check that the composer remains reachable and conversation, draft and scroll state follow the accepted design.

A desktop viewport resize can look correct while the OS keyboard covers the composer. Other misses include neighboring controls activating from one tap, a lost draft or scroll position after switching conversations, or an error message clipping its action. Use a touch device or suitable simulator for tap and OS-keyboard evidence; viewport resizing alone does not establish keyboard behavior. Mobile browser viewport handling can differ when a keyboard appears ([VisualViewport](https://developer.mozilla.org/en-US/docs/Web/API/VisualViewport), [Chrome's viewport behavior guide](https://developer.chrome.com/blog/viewport-resize-behavior)).

### `board-responsive-state`

Keep the board a two-dimensional, square 8-by-8 surface with 64 usable cells. Reflow surrounding navigation, status and controls around it; responsive behavior should not stack the cells. At selected narrow and landscape contexts, exercise selection and reset, and preserve selection through resize or rotation when the accepted design says to do so.

Catch a distorted or clipped grid, unreachable reset, or a layout change that clears selection contrary to the decision. The existing board observer can measure supported browser exports for geometry, overflow, selection and reset; see [the current observer limits](UI.md#read-results-at-the-level-they-establish). Browser resize evidence does not establish native orientation behavior.

### `native-platform-adaptation`

If the product has a native app, check safe areas, platform navigation, OS keyboard, system text scaling and light/dark appearance as a separate scenario family. Rotate or resize with a conversation or board state in progress and compare it with the accepted design. A system inset hiding navigation, a keyboard covering composition, larger text clipping an action or rotation losing required state are useful counterexamples.

Use a device or suitable simulator; record platform, OS, app build, window size/orientation, appearance and text setting with screenshots and action results. Web exports do not establish native behavior. Apple and Android publish platform-specific layout guidance ([Apple Human Interface Guidelines: Layout](https://developer.apple.com/design/human-interface-guidelines/layout), [Android window size classes](https://developer.android.com/develop/ui/views/layout/use-window-size-classes)).

## Current resizing evidence

Within the ten-sample cohort, the implement and document subjects recorded browser checks at 390 and 1440 CSS pixels in light and explicit `.theme-dark` appearance. The independent board observer has observations at 320, 390 and 1280 CSS pixels; its dark media-preference setting did not activate the fixture's explicit `.theme-dark` variant. These are viewport/theme observations of those exports, not execution of the proposed scenarios or rendered coverage of all ten samples.

## Device and platform gaps

The current samples do not establish real touch behavior or OS-keyboard behavior, Safari or Firefox rendering, or native safe areas, platform navigation, system text scaling or appearance. Keep these open until matching device/browser evidence exists. Select relevant cases from the product's recorded decisions; this is a focused set of probes, not a requirement to run every size, theme, orientation and platform combination.
