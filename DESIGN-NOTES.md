# Корен — responsive editorial update

Scope: existing storefront only. Backend, prices, products, order flow, Stripe and admin unchanged.

The visual system preserves the existing wordmark, green/cream palette, SVG illustration and Bulgarian copy. Rounded editorial panels, more readable secondary text, larger controls, a mobile composition and a direct catalog link refine the existing identity. `assets/style-tile.html` uses the real shared CSS tokens.

## Visual Story

| Scene | Visual story | Website copy |
| --- | --- | --- |
| intro | Original market bag; full subject contained | Добрата храна започва оттук. |
| selection | Categories followed by working catalog | Малки открития, голям вкус. |
| conclusion | Green philosophy panel and return to products | Свежо мислене. Истински вкус. |

Normal document flow provides pacing, with no pinned travel, hidden chapters or forced gestures. Text remains visible. Supported browsers apply a small CSS scroll translation/rotation to existing art; this is not a generated video or a 3D camera orbit. Unsupported browsers show the still. Reduced-motion users receive the still and ordinary scrolling. No animation sequence requests, decoded-frame cache or prefetching exists.

Responsive media rule: <=780 CSS px uses vertically stacked content and contained original SVG; >780 uses two columns. There are no competing portrait/landscape downloads. Hero image stays fully contained, with its focal point near (0.5, 0.5). Header occupied height is measured for anchor offsets, including safe-area padding once. Menu is a disclosure, not a modal; normal document focus applies. Escape returns focus and links focus their destinations.

Editing: `index.html` for existing copy and links; `styles.css` for shared tokens, breakpoint and scroll keyframes; `assets/experience.js` for header sizing and focus. Existing catalog editing continues through `/admin`. No publishing workflow added.

## Missing media
Higgsfield image/video tools were unavailable. No new media was generated. Dedicated portrait footage, connected clips and extracted frame sequences remain unimplemented. The original SVG is an honest still fallback. No invented imagery, product variants or claims were added.

## Validation
JavaScript syntax and existing Node smoke checks passed. Python checks: 8 passed, 1 skipped (PostgreSQL integration requires a test database). Test collection needs ADMIN_PASSWORD and APP_BASE_URL set before imports; the first unconfigured run had two admin failures. With the test credentials documented in tests/test_server.py, the full suite passed. Original hero SVG is 5,634 bytes; new enhancement script is 763 bytes (uncompressed file sizes, not measured network transfer). No production compilation step exists for this HTML/CSS/JS + FastAPI project.

Browser visual checks, phone viewports, physical Safari/Chrome, scroll-animation smoothness, text enlargement, network timing, Core Web Vitals and no-JS rendering were not tested: the available cloud browser could not reach the local server. No screenshots or measured performance scores are claimed. Production deployment not performed; changes are supplied through a reviewable PR.
