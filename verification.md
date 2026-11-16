# Delivery verification - 16 November 2026

## Implemented modules

`backend/`: FastAPI, validated schemas, SQLAlchemy tables, session isolation, catalog filtering, proposal approval, transactional orders, email outbox.
`agent/`: OpenAI structured extraction, bounded LangGraph workflow, durable interrupt/checkpoint and trusted approval checks.
`mcp_server/`: official MCP SDK v2 stdio server/client; six typed tools with validated input/output contracts.
`scraping/`: Scrapling Spider, verified JSON-LD/specification parser, normalization, source policies, robots checks and catalog upserts.
`app/`: home and four Streamlit pages, chat, structured-request mode, proposal controls, confirmation dialog, catalog, orders and monitoring.
`sandbox/`, `tests/`, `eval/`, `scripts/`: initialization/reset, local SMTP capture, tests, 62-case trajectory evaluation and 9 ranking-policy cases, launch and reporting scripts.

## Executed verification

- `python -m pytest -q --junitxml=eval/pytest-results.xml`: **71 passed, 1 skipped**. The skipped case is the opt-in live OpenAI test.
- `python -m eval.trajectory_eval`: **62/62 passed**, using real MCP transport, LangGraph and SQLite with an offline parser fixture and email transport stub.
- Step accuracy: 100.0%; tool-call precision: 100.0%; wasted steps: 0.
- Recovery: 100.0%; injection cases: 7/7; stopping-rule compliance: 100.0%.
- Offline mean/p50/p95 task latency: 0.093/0.104/0.171 seconds. No live model-quality or live-cost claim follows from these fixture results.
- Real catalog: **101 offers** from Spacenet: 33 laptops, 34 desktops, 34 tablets. Zero demo offers in the development catalog. Mytek: 0. Tunisianet: 0.
- Live refresh: one existing offer updated, zero inserted, zero errors; see `eval/scrape-refresh.json`.
- MCP: all six tools discovered through a real subprocess; search/compare/budget/order/email graph invocation verified. Approval interrupt and resume tested; rejection and forged resume cannot create an order.
- Email: actual loopback SMTP test passed. Real-catalog API smoke created one sandbox order per test session; repeated confirmation returned the same order. Emails were captured locally, not delivered externally.
- LangSmith: configured synthetic trace write/read verified; historical result retained here; private run/project identifiers and trace URLs are kept only in ignored local files. Graph/MCP tracing is integrated with hidden payload defaults.
- Streamlit: home and all four pages rendered without exceptions in AppTest. Browser automation host was unavailable, so a browser visual/modal interaction review is not claimed.
- Docker Compose configuration validated with `docker compose config --quiet`. Engine startup and image build remain unverified because the Docker engine was not running.

## External blockers and scope limits

The opt-in live OpenAI test was explicitly run and **failed with HTTP 429, no credits remaining**. Manual structured input works without API credits. A funded live run is still needed to validate natural-language extraction and measure model tokens/cost.

Mytek's initial normal category request returned 403; a later crawler run failed closed on a robots DNS timeout. Tunisianet bulk collection is disabled because its terms prohibit catalog reproduction. No access-control bypass was attempted. Spacenet collection logged one laptop product timeout; failed collection was not replaced with fabricated offers.

Recommendations and explanations use deterministic ranking; the model is used for requirement extraction rather than an unconstrained ReAct planner. CPU equivalence, mixed-item baskets, shipping quotation and persistent user accounts are not implemented. The complete sandbox workflow works through structured input, with these scope and external limits explicitly documented.

## Reproduction

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
.\.venv\Scripts\python.exe scripts/run.py
```

Open http://127.0.0.1:8501. Expand Structured request for a no-credit demo; select a product/quantity, then separately review and confirm the proposal, then inspect order history and `data/mail/`.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m eval.trajectory_eval
.\.venv\Scripts\python.exe -m scraping.refresh_catalog --retailer spacenet --limit 34
.\.venv\Scripts\python.exe scripts/smoke_demo.py
```

The scraper's ten-second delay makes a full 102-offer attempt take roughly 20 minutes. Source data changes over time; repeat test metrics are measured, not hardcoded.

## Recommendation upgrade verification

- Full suite: 71 passed, 1 opt-in live test skipped. Both durable checkpoints survive backend shutdown/restart in an API regression test.
- Preserved original 40 workflow scenarios and added 22: 62/62 passed. Separate synthetic ranking-policy expectations: 9/9 passed. These are offline policy/control-flow results, not model or real-world shopping accuracy.
- New API/service checks cover alternative choice, quantity, same-choice replay, cross-session access, forged offer IDs/resumes, extra budget/approval fields, snapshot tampering/expiry, stale or unavailable offers, changed prices and hard constraints. Existing transactional order, approval-hash and email-idempotency tests remain passing.
- Global step-budget scenarios cover waiting across both checkpoints, two retries reaching 12 steps, stopping before approval and stopping after order commit with notification pending. Normal completion is 10 actions.
- `python scripts/smoke_demo.py`: isolated synthetic catalog, actual loopback SMTP, alternative with quantity two, no order before approval, one committed order, one captured email, repeated confirmation did not duplicate either. Evidence: `data/smoke-demo.json`.
- Gmail configuration checked without exposing secrets: real mode, smtp.gmail.com:587, credentials and recipient allowlist present. Real TLS/authentication and unauthorized-recipient rejection tested with mocks. Launcher tests ensure real mode never starts local SMTP and does not override host/port. No external email sent by verification; live Gmail deliverability was not re-tested.
- A fresh live OpenAI extraction attempt returned HTTP 429/no credits. Evidence: `eval/upgrade-live-status.json`. The English/French prompt is implemented, but live extraction quality and token cost remain unverified.
- UI pages render under AppTest; API tests exercise the selection/approval actions. A manual visual/modal browser review of populated recommendation cards remains outstanding.
- Scoring is a deterministic resource heuristic. GPU/VRAM, CPU benchmarks, weight, battery and stylus compatibility are not available. Soft text is disclosed rather than silently treated as verified. Budget revisions and changes after selection require a new request.

## Separate repository-publication check - 16 November 2026

A clean copy of the intended publication files was configured from .env.example with new databases, using the installed Python 3.11 environment. Imports, 16 FastAPI routes, table initialization and demo seeding passed. Full pytest: 71 passed, 1 skipped; trajectory evaluation: 62/62; ranking policy: 9/9. The isolated local-SMTP purchase created one order and captured one email with duplicate prevention. pip check found no broken requirements. No existing application database or .env was modified. No real Gmail or OpenAI requests were sent. Fresh network dependency installation was not repeated. Separate measured results: docs/publication-checks.json; historical figures above remain unchanged.
