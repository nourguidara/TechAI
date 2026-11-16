# Delivery verification - 16 November 2026

## Implemented modules

`backend/`: FastAPI, validated schemas, SQLAlchemy tables, session isolation, catalog filtering, proposal approval, transactional orders, email outbox.
`agent/`: OpenAI structured extraction, bounded LangGraph workflow, durable interrupt/checkpoint and trusted approval checks.
`mcp_server/`: official MCP SDK v2 stdio server/client; six typed tools with validated input/output contracts.
`scraping/`: Scrapling Spider, verified JSON-LD/specification parser, normalization, source policies, robots checks and catalog upserts.
`app/`: home and four Streamlit pages, chat, structured-request mode, proposal controls, confirmation dialog, catalog, orders and monitoring.
`sandbox/`, `tests/`, `eval/`, `scripts/`: initialization/reset, local SMTP capture, tests, 40-case trajectory evaluation, launch and reporting scripts.

## Executed verification

- `python -m pytest -q --junitxml=eval/pytest-results.xml`: **43 passed, 1 skipped**. The skipped case is the opt-in live OpenAI test.
- `python -m eval.trajectory_eval`: **40/40 passed**, using real MCP transport, LangGraph and SQLite with an offline parser fixture and email transport stub.
- Step accuracy: 100.0%; tool-call precision: 100.0%; wasted steps: 0.
- Recovery: 100.0%; injection cases: 7/7; stopping-rule compliance: 100.0%.
- Offline mean/p50/p95 task latency: 0.117/0.116/0.203 seconds. No live model-quality or live-cost claim follows from these fixture results.
- Real catalog: **101 offers** from Spacenet: 33 laptops, 34 desktops, 34 tablets. Zero demo offers in the development catalog. Mytek: 0. Tunisianet: 0.
- Live refresh: one existing offer updated, zero inserted, zero errors; see `eval/scrape-refresh.json`.
- MCP: all six tools discovered through a real subprocess; search/compare/budget/order/email graph invocation verified. Approval interrupt and resume tested; rejection and forged resume cannot create an order.
- Email: actual loopback SMTP test passed. Real-catalog API smoke created one sandbox order per test session; repeated confirmation returned the same order. Emails were captured locally, not delivered externally.
- LangSmith: configured synthetic trace write/read verified; evidence and trace URL in `eval/langsmith-verification.json`. Graph/MCP tracing is integrated with hidden payload defaults.
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

Open http://127.0.0.1:8501. Expand Structured request for a no-credit demo; review and confirm the proposal, then inspect order history and `data/mail/`.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m eval.trajectory_eval
.\.venv\Scripts\python.exe -m scraping.refresh_catalog --retailer spacenet --limit 34
.\.venv\Scripts\python.exe scripts/smoke_demo.py
```

The scraper's ten-second delay makes a full 102-offer attempt take roughly 20 minutes. Source data changes over time; repeat test metrics are measured, not hardcoded.
