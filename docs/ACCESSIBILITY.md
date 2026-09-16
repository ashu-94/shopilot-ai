# Accessibility review

Playwright scans 15 public, customer and administrative routes with axe WCAG 2 A/AA and 2.1 AA rules. A separate commerce test scans populated item-return approval content. The test server uses disposable synthetic data.

Changes include darker secondary labels, status tags and populated order/approval/operations cards; labeled navigation and controls; a skip link; focusable main content and audit scrolling; mobile drawer focus entry, Escape dismissal and focus restoration; and reduced-motion support.

Keyboard and layout checks cover a 390-pixel mobile viewport and a 640-pixel reflow viewport corresponding to 200% of a 1280-pixel layout. Checks use Enter, Escape and focus assertions and reject horizontal document overflow.

After building the frontend, run `npx playwright install chromium` and `npx playwright test` from `frontend/`. The runner starts a disposable API on 8123 and preview on 4173. On Windows, if child-server teardown hangs, start `python -m scripts.test_server` from the root and a Vite preview on 4173 with `BACKEND_URL=http://127.0.0.1:8123` separately, then set `E2E_EXTERNAL_SERVERS=1` for the test command. Use PowerShell environment-variable syntax on Windows.

Results: `verification/accessibility.json` and `verification/axe-findings.json`. These automated checks are not a declaration of full WCAG conformance. Manual NVDA/VoiceOver testing, complete keyboard journeys, all error states, browser zoom, text spacing and user testing remain release gates.
