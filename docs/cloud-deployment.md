# Deployment handoff

Target GitHub owner: Mansi176-dotcom. Target repository name: railform.

Deployment requires authorized hosting access and a server-side OpenAI API key. `render.yaml` defines the complete service. Do not describe it as deployed until a provider returns a successful deployment and its health endpoint and core workflow are verified.

## Configuration

- Docker runtime, one instance, one Uvicorn worker.
- `PORT` supplied by host; default 8000 locally.
- SQLite on `/app/runtime` persistent disk (1 GB).
- `OPENAI_API_KEY`: required secret for evidence explanations.
- `OPENAI_MODEL`: gpt-4.1-mini by default.
- `OPENAI_DAILY_REQUEST_LIMIT`: 20 new calls per UTC day.
- `RAILFORM_ACCESS_TOKEN`: generated hosting secret, shared research workspace access code.
- `RAILFORM_ENV=production`: secure cookies and mandatory access configuration.

## Acceptance checks after deployment

1. GET `/api/health` reports `deployment: full-stack` and ready status.
2. Unlock workspace; `/api/ai/status` reports configured, without secret values.
3. Start guided demo; verify changing WebSocket sequence numbers and measured events.
4. Open an event, request an explanation, verify provider/model metadata and nonempty live API output.
5. Acknowledge and save a note; verify it after browser refresh.
6. Pause/resume, export JSON/CSV and open a print report.
7. Restart the service; confirm archived records remain on disk (the active run resets by design).

OpenAI failure must not interrupt detector streaming. Browser bundles and public Git history must contain no credentials, hosting identity files, SQLite databases or raw recordings.
