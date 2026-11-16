# TechStock AI

CS496 - Project 3: The Operator | Mediterranean Institute of Technology | 16 November 2026

## 1. Task, tools and architecture

The application helps users procure laptops, desktops and tablets from a local catalog of Tunisian retailer offers. Streamlit calls FastAPI; a stateful LangGraph workflow invokes six official MCP SDK tools over stdio. SQLAlchemy persists SQLite sandbox orders. Scrapling is the sole website fetching and parsing framework. No retailer transaction or payment is implemented.

MCP tool | Role

search_products / compare_offers | Filter hard requirements and rank stored offers

check_budget / get_offer_details | Exact totals and auditable source details

create_purchase_order | Transactional, idempotent write after approval

send_confirmation_email | Durable notification to approved recipient

## 2. Loop and proof of stopping

The workflow parses and validates requirements, searches, ranks and persists authorized recommendations, interrupts for customer product/quantity selection, revalidates budget, builds an immutable proposal, interrupts again for explicit purchase approval, then creates an order and sends confirmation. The normal path counts 10 actions. Missing requirements, no feasible offer, rejection and errors terminate explicitly. OpenAI extraction is integrated; ranking and explanations are deterministic. Manual structured input is explicitly labeled.

Before every counted action, consume checks steps < limit and increments once. Every retry consumes another step. By induction, steps never exceed limit <= 12. Each recoverable tool has at most two retries. Forward-only graph edges prevent unbounded autonomous loops. Human waiting performs no polling work; replay does not increment before interrupt. MCP/model calls have 30-second timeouts. Tests exercise low limits, retry exhaustion, rejection and forged resumes.

# Safety and measured behavior

## 3. Two human checkpoints and sandbox

An owner-bound, hashed recommendation snapshot permits only its listed offer IDs and expires after 30 minutes. Selection rechecks price, stock, freshness, quantity and budget; it never authorizes an order. The user then reviews the exact item, supplier, quantity, unit price, total, budget and recipient. Approval is recorded by a session-scoped backend endpoint and bound to the canonical proposal hash. A model-provided flag or graph resume alone cannot authorize a write. Proposals expire after 30 minutes. Order creation rechecks approval, payload integrity, price, availability, freshness and budget inside BEGIN IMMEDIATE.

Unique proposal/idempotency constraints prevent repeated and concurrent confirmation from duplicating an order. Item snapshots preserve approved pricing across scraper refreshes. The order and email outbox commit together. Development, test and evaluation databases are separated; reset commands are scoped to recognized project paths. Verification used local SMTP only. Gmail host/port, credential and allowlist presence were checked without logging secrets; TLS/auth and allowlist enforcement passed mocked tests.

## 4. Trajectory evaluation results

The original 40 scenarios remain, adapted for selection, plus 22 new workflow cases. Nine separate synthetic ranking-policy expectations also passed; this is not recommendation accuracy. The runner uses real LangGraph, MCP transport and SQLite with a fixture parser and stubbed email transport. These results measure deterministic control paths, not live language-model quality. Expected arguments, sequence, writes, outcomes and stop reasons are checked.

Metric | Measured result

Task success / step accuracy | 62/62 / 100.0%

Tool-call precision / wasted steps | 100.0% / 0

Recovery / injection / stop compliance | 100.0% / 100.0% / 100.0%

Mean / p50 / p95 latency | 0.093s / 0.104s / 0.171s

Automated pytest suite | 71 passed; 1 opt-in live test skipped

Timing excludes MCP process startup and human deliberation. Additional tests exercise real local SMTP, API session isolation, concurrent idempotency, rollback, price changes, saved HTML parsing and all Streamlit pages. The new isolated synthetic API smoke completed a ten-step order after selecting an alternative with quantity two, captured one email locally, and confirmed idempotency. Both checkpoints survive restart in a regression test.

# Errors, attacks and evidence

## 5. Error taxonomy and recovery

Failure class | Response

Invalid/missing/unsupported requirements | Reject or ask clarification before searching

Unknown stock, stale data, insufficient budget | No feasible offer; no write

Transport timeout/connection failure | At most two retries within global step limit

Changed price/payload, expired proposal | Reject; require a fresh proposal and approval

Database failure | Transaction rollback; no partial order/outbox

SMTP failure before delivery | Order survives; failed notification may be retried

Ambiguous SMTP acknowledgement | No automatic resend; manual reconciliation

Scraper block or robots failure | Fail closed; no access-control bypass

## 6. Injection threat model

Untrusted entry points include retailer descriptions, names, URLs and user requests. Attackers may try budget overrides, fake system authority, unauthorized writes, recipient redirection, unsafe links, infinite loops, or forged price/stock statements. Seven explicit injected-content scenarios passed. Backend constraints, typed tool schemas, HTTPS domain checks, immutable approval records and bounded execution contain these attacks.

Raw descriptions are retained for audit and are not sent to the model. Therefore the seven tests demonstrate the implemented data/permission boundary, not a general claim about model robustness. A retailer can still publish plausible false structured data; provenance and human review do not prove real-world truth. Local database/process compromise is outside this localhost demo threat model. SMTP exactly-once delivery across a crash is not claimed.

## Recommendation policy and limits

Hard filtering precedes normalized weighted RAM, storage, SSD, processor-information, completeness, value and budget-headroom scoring. Programming favors RAM; study favors headroom/value. RAM/storage credits cap at 32/1024 GB, not hard requirements. Unknowns earn no credit. GPU performance, weight, battery and stylus support are unverified. Alternatives explain factual tradeoffs. Quantity defaults to one; missing budget asks clarification. Budget revisions require a new request.

# Collection, cost and limitations

## 7. Verified data and integrations

The delivery catalog contains 101 real offers and 0 demo offers. Supplier counts: {'spacenet': 101}. Category counts: {'desktop': 34, 'tablet': 34, 'laptop': 33}. Validation checked positive prices, allowed source URLs, timestamps, stock enums, quantities and uniqueness. Nullable specifications and quantities remain unknown when not published.

Spacenet normal HTTP collection and pagination are verified with a ten-second minimum delay. Mytek returned 403; no bypass was attempted. Tunisianet bulk collection is disabled because its terms prohibit catalog reproduction. The initial laptop run stopped on a robots DNS timeout; a retry collected 33 laptop offers, with one product request timing out. A subsequent one-off refresh updated its existing record without inserting a duplicate. Exact collection reports accompany the repository.

MCP transport, LangGraph interrupt/resume, local SMTP and LangSmith synthetic trace write/read were verified. The configured OpenAI API returned HTTP 429: no credits remaining. Thus live natural-language extraction and live model token cost remain unverified. Manual structured mode demonstrates the remaining workflow. Docker Compose is supplied, but its engine was not running. Browser automation was unavailable; Streamlit rendering was tested with AppTest.

## 8. Cost analysis and reproducibility

The offline suite used zero model tokens and zero model API cost. Its 100x replay model cost is also zero; this does not estimate a live workload. For a live task, cost = (input_tokens x input_rate + output_tokens x output_rate) / 1,000,000. For 100 times a measured workload, multiply the observed total by 100. Rates are configurable and left unknown unless verified. No live cost figure is fabricated.

Run: python -m pytest -q; python -m eval.trajectory_eval; python -m eval.ranking_eval; python -m scraping.refresh_catalog --retailer spacenet --limit 34. Setup and launch commands, environment configuration, reset instructions and integration limits are in README.md. Full measured trajectories are in eval/results.json; test results are in eval/pytest-results.xml.

Team contribution names were not supplied. Code, tests and documentation were generated with Codex; students must review, explain and record their actual contributions before submission.