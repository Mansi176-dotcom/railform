# Verification

Verified locally on 12 October 2026 with Python 3.12 and Node/npm.

- **8 tests passed**: seeded generation and km/h conversion; identical causal filter output across chunk boundaries; measurement-only detector input and event deduplication; missing-data inference suppression; persisted workflow changes; one-to-one evaluation calculations; the complete fixed-seed 90-second simulation; and FastAPI/WebSocket end-to-end workflow.
- API integration test covers configure → start → WebSocket packet → computed alert → evidence → acknowledge with stored note → pause → analysis/PSD/CWT → resume → JSON/CSV/print export → reset. Invalid configuration and sensor requests return 422.
- TypeScript and Vite production build passed. npm dependency audit reports zero vulnerabilities after updating ECharts and Vite.
- Rendered overview inspected at 1440px desktop, 820px tablet and 390px mobile. Checked navigation, real streaming plot, live counters and opening a measured diagnostic. Minor ECharts bundle-size warning remains; chart code is the largest dependency.
- SciPy 1.15.3 failed to load its macOS wheel; pinned 1.16.3 loads and passes the tests.
- Eight held-out synthetic evaluation runs completed. Saved measured results: `evaluation-results.json`. Precision/recall/F1 were 1.00/0.60/0.75 for the implemented detector and 0.40/0.40/0.40 for the raw threshold baseline in this small fixed suite. These are not field results, and two injected track events were missed. Processing latency is machine-dependent and measured in the JSON.
- Docker files are supplied but Docker was not executed in this environment.
- One dependency deprecation warning from Starlette/AnyIO occurs in TestClient; no test failure.

## Remaining scope limits

The hosted Site is an honest disconnected frontend preview. Full simulation, SQLite persistence and analysis require the supplied Python backend. The browser preview does not synthesize fake results.

The signal workspace inspects the latest acquired window; selecting a detected segment on Overview displays that event's stored excerpt. Arbitrary historical multichannel raw browsing is not implemented beyond the bounded raw ring. Repeated-pass support uses coarse spatial bins, not coherent alignment. A compensated mixed-filter displacement estimator is deliberately omitted. The 90-second demo measures simulation time, so wall-clock duration may exceed 90 seconds with processing overhead. The full text of the 2012 mixed-filtering paper was inaccessible.

## OpenAI / cloud revision

The new revision adds server-only OpenAI Responses integration, measured-evidence allowlisting, cached explanations, request caps, shared-workspace authentication and a full-stack Docker/Render blueprint. Live OpenAI calls and a hosted deployment require credentials and are not implied by the unit tests. Original synthetic detector results are unchanged because OpenAI only explains detector evidence.

Cloud revision verification: **13 tests passed** locally, including OpenAI request construction, exclusion of truth/notes, response caching, missing-key and upstream-error behavior, workspace authentication and secret non-disclosure. TypeScript/Vite production build passed; npm audit reported zero vulnerabilities. OpenAI tests use mock HTTP responses; no live API call was possible without an authorized API key. Docker engine was not available locally, so the container build remains to be verified by CI/hosting.
