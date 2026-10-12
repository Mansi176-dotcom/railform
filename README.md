# RAILFORM — Railway Intelligence Studio

A complete React/TypeScript + FastAPI railway research prototype. The sculpted-clay interface, seeded simulation, causal signal analysis, diagnostic workflow, evaluation and exports are preserved. **OpenAI is the only external AI API** and explains actual detector evidence. It never generates plotted data or substitutes for measured evaluation results.

All sensor data is synthetic. This is not field-validated, railway-certified, or a proven failure-prediction system.

## Run locally

Requires Python 3.12+, Node 22+ and npm:

```sh
./start.sh
```

Open http://127.0.0.1:8000. One server serves the built frontend, APIs and WebSocket stream.

To enable OpenAI, set `OPENAI_API_KEY` in your shell or use an untracked `.env` file and start with:

```sh
.venv/bin/uvicorn backend.main:app --env-file .env --host 127.0.0.1 --port 8000 --workers 1
```

Model defaults to `gpt-4.1-mini`; configure `OPENAI_MODEL` to another Responses-compatible model available to your account. No key is needed for simulation or numerical analysis. The AI panel explicitly reports an unconfigured server instead of generating a fake response.

## Full-stack deployment

`render.yaml` deploys **one Docker web service**, serving the same React build and Python backend under one HTTPS origin. It includes WebSockets, a persistent SQLite disk, readiness checks, and single-worker execution. This is not a frontend-only deployment.

1. Connect this repository to Render as a Blueprint.
2. Review the paid Starter service and 1 GB persistent disk before creating it. No paid resource is created merely by committing this file.
3. Set `OPENAI_API_KEY` as a secret when prompted. Never put it in GitHub source, Vite variables, screenshots or browser storage.
4. Render generates `RAILFORM_ACCESS_TOKEN`. Retrieve it securely from the hosting dashboard and use it to unlock the research workspace.
5. Wait for the deployment to become healthy, then verify the workflow below on its returned URL.

GitHub Actions runs the Python tests and production build. Render is configured to deploy only after checks pass. The existing Sites URL, if used previously, remains a separate static preview until a full-stack deployment is completed. A configuration file is not evidence that hosting is live.

## OpenAI integration

In a diagnostic drawer, choose **Explain this evidence**. The backend calls only `https://api.openai.com/v1/responses`, with `store: false`, a bounded output, and a 40-second timeout. Inputs include measured features, reference values, chainage and detector labels. Injected ground truth, simulator presets and reviewer notes are excluded.

Generated text is labeled separately from deterministic evidence. Requests are cached by evidence/model/prompt version. The default global cap is 20 new requests per UTC day (`OPENAI_DAILY_REQUEST_LIMIT`). Failed attempts also count. Cached responses do not create a new API call. No automatic background calls occur during streaming. API usage is billed by OpenAI separately from hosting.

A generated explanation cannot change an alert, numerical score, workflow or evaluation result. Review model text against the displayed measurements. There is no other LLM provider, hosted detector, external map API or analytics service.

## Access and persistence

Cloud deployment requires a workspace code, exchanged for a signed HTTP-only, secure, same-site cookie. API keys remain server-side. Mutating HTTP and WebSocket requests reject cross-origin requests. Login attempts are bounded. This is a shared academic research workspace, not a multi-tenant SaaS system.

The SQLite database and raw ring reside in `/app/runtime` on Render's persistent disk. The active live run resets on server restart; stored alerts, notes and evaluations remain in the database until retention pruning. Maintain one instance and one worker: a process-local simulation engine cannot be horizontally scaled without a separate state service.

## Reproducible demo

Run guided demo → inspect measured event → request OpenAI explanation → acknowledge and save a note → pause → resume → export JSON/CSV or print report → reset. Seed 42 and the 90-second simulation timeline are fixed. Wall time can exceed 90 seconds with processing overhead. Evaluation uses independent held-out seeds and reports actual results, including misses.

```sh
.venv/bin/python -m pytest -q
npm ci --prefix frontend
npm run build --prefix frontend
.venv/bin/python -m backend.run_evaluation
```

API docs: `/docs`; health: `/api/health`; readiness: `/api/ready`; AI configuration status: `/api/ai/status` (never returns secrets).

## Research and limits

See [methodology](docs/methodology.md), [research mapping](docs/research.md) and [verification](docs/verification.md). Two full papers were reviewed from accessible copies; the 2012 mixed-filtering paper was abstract-only. Displacement reconstruction, exact paper reproduction and field validation are not implemented. Historical raw browsing is bounded to the retained ring. The OpenAI integration tests use a mocked transport; they do not establish live account access or model accuracy.
