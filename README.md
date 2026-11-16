# TechStock AI

Intelligent IT procurement for Tunisia, built for CS496 Project 3 - The Operator.
Streamlit -> FastAPI -> LangGraph -> official MCP Python SDK -> SQLite.
Scrapling runs independently and collects retailer offers. Orders are internal sandbox records; no retailer checkout or payment exists.

## Quick start (Windows, Python 3.11)

From the repository root, setup once:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

Run the application:

```powershell
.\.venv\Scripts\python.exe scripts/run.py
```

Open http://127.0.0.1:8501. API health: http://127.0.0.1:8000/health; API docs: http://127.0.0.1:8000/docs.
The launcher starts FastAPI, Streamlit, and a local-only SMTP capture service. Captured messages are `.eml` files in `data/mail/`.
In sandbox mode the launcher explicitly overrides SMTP_HOST/PORT to 127.0.0.1:1025, even if `.env` contains another server.
An existing `.env` is preserved. Never commit it. Stop the launcher with Ctrl+C.

On Linux/macOS: `python3 -m venv .venv`, activate it, `pip install -r requirements.txt`, copy `.env.example` to `.env`, then `python scripts/run.py`.
All commands below use the activated virtual environment, or prefix them with `.\.venv\Scripts\python.exe` instead of `python`.

## Catalog and demo

```powershell
python -m scraping.refresh_catalog --retailer spacenet --limit 34
```

The limit is **per category** (up to 102 offers across laptops, desktops and tablets). The scraper waits at least ten seconds between Spacenet requests. A complete run takes roughly 20 minutes, subject to network conditions. For a short run use `--category laptop --limit 3`. Re-running updates existing offers rather than duplicating them.

The UI catalog shows real records by default. Prices are observations with timestamps, not current retailer quotations. Unpublished stock quantities remain null. Freshness is limited to 48 hours for proposals and rechecked on order creation.

For a separately labeled offline demonstration:

```powershell
python -m sandbox.seed
```

This creates three explicitly marked DEMO offers; it does not claim they were scraped. Evaluation fixtures use a separate database. Do not run the seeder if you want a real-data-only development catalog.

In the AI Assistant, enter English or French requests, e.g. `Je veux 2 PC portables Lenovo, 16 Go RAM, SSD 512 Go, budget total 6000 TND.`
If OpenAI credits are unavailable, expand **Structured request - no OpenAI credits required**. This is explicit manual input, not a simulated AI response. It runs the same comparison, budget, interrupt, approval, order, and notification workflow.
Review the exact product, quantity, unit price, total, budget, and recipient. Confirm or reject. A confirmation dialog appears only after the database commit. Purchase history and monitoring are scoped to your browser session.

## Verified source policy

- **Spacenet:** public terms and robots inspected; normal HTTP access and structured metadata verified. Ten-second minimum crawl interval, no login or bypass. Category pagination and individual product pages are followed.
- **Mytek:** robots fetched; its category request returned HTTP 403. No bypass attempted. `--retailer mytek` can check normal access later and stops on blocks. Product parsing remains unverified against live Mytek product HTML.
- **Tunisianet:** public terms Article 9 prohibit reproduction of the catalog. Bulk collection is disabled. The command reports this limitation; obtain retailer permission before changing the policy.
- No fabricated products are inserted to meet a collection target. `data/scrape-*.json` contains run statistics, and `eval/catalog-verification.json` contains delivery-time database counts when available.

Sources: [Spacenet terms](https://spacenet.tn/content/3-terms-and-conditions-of-use), [Spacenet robots](https://spacenet.tn/robots.txt), [Mytek robots](https://www.mytek.tn/robots.txt), [Tunisianet terms](https://www.tunisianet.com.tn/content/3-conditions-generales-de-ventes).

## Architecture and workflow

`backend/` owns schemas, configuration, SQLAlchemy models and trusted transactions. `agent/graph.py` implements parse -> validate -> search -> compare -> budget -> proposal -> human interrupt -> create order -> notify -> finalize, with terminal branches for clarification, no feasible offer, rejection, and errors.

OpenAI performs structured requirement extraction. Search, ranking and recommendation explanations are deliberately deterministic. Unsupported constraints require clarification; processor matching is conservative literal matching, not an unverified CPU-equivalence benchmark. One request currently purchases one configuration and quantity from one supplier.

`mcp_server/server.py` exposes six typed tools through **MCP SDK 2.3 MCPServer**, and `mcp_server/client.py` starts and connects to it over stdio. The server is a backend-owned subprocess, not an unauthenticated network service. Every graph tool invocation uses the MCP client. `get_offer_details` is also available for direct tool inspection.

| Tool | Purpose |
| --- | --- |
| search_products | Hard technical, budget, stock and freshness filtering |
| compare_offers | Revalidate candidates; rank by total and freshness |
| check_budget | Decimal total and remaining merchandise budget |
| get_offer_details | Stored source, price and specification details |
| create_purchase_order | Approved, immutable proposal -> transactional sandbox order |
| send_confirmation_email | Durable outbox -> approved recipient only |

The graph uses durable SQLite checkpoints; an interrupt resumes with LangGraph Command. The resume payload never authorizes a purchase: the node and write service independently read the trusted proposal approval record. Authorization is tied to a hashed random session capability. Store access and MCP stdio are trusted local boundaries. This is a localhost university demo, not a production identity-management system.

## Database and integrity

- `products`: technical configuration, stable signature and original specifications.
- `supplier_offers`: supplier identity, source URL, price, availability, timestamp and demo marker.
- `purchase_proposals`: immutable canonical payload/hash, owner, expiration and approval record.
- `purchase_orders` and `order_items`: unique proposal/idempotency keys and immutable price/product snapshots.
- `email_notifications`: one durable outbox record per order with delivery state and attempts.
- `agent_runs`: status, trajectory, counted steps, tokens, cost and timing.

Money uses Decimal and Numeric(14,3), matching TND millimes. SQLite foreign keys and WAL are enabled. BEGIN IMMEDIATE serializes approval/order writes; unique constraints prevent duplicate orders. The approved price must still equal the current offer price, and all requirements/budget are checked again before commit. Scrape refreshes cannot alter order snapshots.

Cross-retailer merging requires manufacturer identity and a complete matching configuration. When identity is uncertain, URLs keep records separate. This favors avoiding false merges over aggressive deduplication.

Budgets cover merchandise in the internal sandbox order. Shipping is not quoted or charged. General in-stock status does not establish an exact available quantity; the UI makes that limitation explicit.

## Configuration

See `.env.example`. Key options:

- OPENAI_API_KEY / OPENAI_MODEL: live extraction; no model fallback impersonation.
- LANGSMITH_API_KEY / LANGSMITH_TRACING / LANGSMITH_PROJECT: optional tracing. Disabled tracing does not affect execution.
- DATABASE_URL: SQLite only. Development defaults to `data/techstock.db`; tests/evaluation use `test.db`/`evaluation.db`. Checkpoint files are derived from each database path.
- OFFER_MAX_AGE_HOURS: default 48.
- MAX_AGENT_STEPS: 1-12; MAX_TOOL_RETRIES: 0-2. Every tool attempt, including retries, consumes a step.
- EMAIL_MODE: sandbox by default. SMTP_HOST/PORT default localhost:1025. Real mode additionally requires SMTP_ALLOWED_RECIPIENTS, explicit credentials and TLS.
- INPUT_COST_PER_MILLION / OUTPUT_COST_PER_MILLION: optional verified model rates. Missing rates produce unknown cost, never a fabricated estimate.

Trace payloads are hidden by default to avoid exporting email addresses or raw content. Local trajectories retain validated tool arguments and retry/error timing. Monitoring can retrieve LangSmith trace links. The MCP subprocess also emits tool execution traces and timing logs.

## Email semantics

The order and outbox commit together. Failure to connect to SMTP records `failed` and permits a safe retry from order history. A crash or ambiguous SMTP acknowledgement leaves `sending` or `delivery_unknown`; those are deliberately not auto-retried. SMTP cannot guarantee exactly-once delivery across a crash after acceptance. Reconcile such messages in Mailpit/the SMTP sink before manually repairing their status. Message-ID is stable. Real recipient changes cannot be supplied through the email tool.

## Evaluation and tests

```powershell
python -m pytest -q
python -m eval.trajectory_eval
python scripts/smoke_demo.py
```

The smoke script uses the running API and real catalog, creates one sandbox order, confirms it twice, and checks order history. It only sends to the configured local sandbox in the default launcher.

40 explicit cases: 12 normal, 8 budget/availability, 8 failures, 7 injections, 5 stopping cases. `eval/scenarios.json` defines requests, initial state, expected sequence/outcome, permitted writes, forbidden actions and stopping reasons. `eval/results.json` contains measured results. The offline runner uses real LangGraph, MCP transport and SQLite, a fixture parser, and an email transport stub. It measures control-flow behavior, **not live model quality**. Timing excludes MCP process startup and human deliberation. Model tokens/cost are zero only for this offline run.

Opt-in live model check:

```powershell
$env:RUN_LIVE_OPENAI='1'
python -m pytest tests/test_live.py -q
```

The delivery-time live check reached OpenAI but returned HTTP 429, no credits remaining. No successful live extraction or live token cost is claimed. LangSmith trace write/read and local SMTP delivery were verified separately. See `eval/live-status.json` and `verification.md`.

## Stopping proof

`consume` checks `steps < max_steps` before every counted action. A successful check increments steps exactly once; every retry calls the same function. Therefore by induction `0 <= steps <= max_steps <= 12`. At most two retries follow an initial tool attempt. Graph transitions are forward-only, except bounded retries. The human interrupt pauses with no polling loop; its replay does not increment a step before the interrupt. SDK network calls have timeouts; waiting for a human has no deadline but performs no autonomous work. Proposals expire after 30 minutes. Tests exercise bounds, rejection and forged resumes.

## Reset

Stop the application before resetting:

```powershell
python -m sandbox.reset --confirm
python -m sandbox.reset_mail --confirm
# Or preserve catalog while clearing orders, proposals, runs and checkpoints:
python -m sandbox.reset --confirm --orders-only
```

Database reset only accepts recognized database filenames directly under the project's `data` directory. It clears application tables, not unrelated databases. Local captured email reset only deletes `.eml` files under `data/mail`; Mailpit has its own UI. Tests initialize their own disposable database every case.

## Docker

```powershell
docker compose up --build
```

Includes backend (with MCP subprocess), Streamlit, and Mailpit. SQLite persists in the `catalog` volume. Mailpit UI: http://localhost:8025. All published ports bind localhost. The backend has a health check. Refresh in Docker: `docker compose exec backend python -m scraping.refresh_catalog --retailer spacenet --limit 34`.
Docker CLI is present in the delivery environment, but the engine was not running; image build and full Compose startup remain unverified.

## Known limits

Live OpenAI requires funded credits. Retailer access and selectors can change. Exact stock counts, shipping and missing technical details are not invented. Unknown/stale offers are excluded. CPU-equivalence and complex mixed-product baskets require further work. Browser-session identity is lost when Streamlit session state resets; persistent account login is outside this localhost demo. Offline evaluation cannot establish resistance of arbitrary future models or truthfulness of retailer prices. Browser visual automation was unavailable; page rendering and API behavior were tested with Streamlit AppTest and pytest.

## Contributions

Implementation, tests, data collection and documentation were generated with Codex in this workspace. Student names and actual team responsibilities were not provided and are not invented. Before submission, each team member should review the code and record their own contributions here.
