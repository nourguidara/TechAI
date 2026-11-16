import json,shutil
from pathlib import Path
from xml.etree import ElementTree as ET
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from html import escape
metrics=json.loads(Path('eval/results.json').read_text())['metrics']
catalog=json.loads(Path('eval/catalog-verification.json').read_text())
root=ET.parse('eval/pytest-results.xml').getroot(); suite=root.find('testsuite')
passed=int(suite.attrib['tests'])-int(suite.attrib['failures'])-int(suite.attrib['errors'])-int(suite.attrib['skipped'])
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleTech',fontName='Helvetica-Bold',fontSize=24,leading=29,textColor=colors.HexColor('#12304a'),spaceAfter=16))
styles.add(ParagraphStyle(name='BodyTech',fontName='Helvetica',fontSize=10,leading=14,spaceAfter=9))
styles.add(ParagraphStyle(name='SmallTech',fontName='Helvetica',fontSize=8,leading=11,spaceAfter=7))
styles['Heading2'].textColor=colors.HexColor('#146b78')
story=[]; markdown=[]
def title(t): story.append(Paragraph(escape(t),styles['TitleTech'])); markdown.append('# '+t)
def h(t): story.append(Paragraph(escape(t),styles['Heading2'])); markdown.append('## '+t)
def p(t): story.append(Paragraph(escape(t),styles['BodyTech'])); markdown.append(t)
def table(rows,widths):
    data=[[Paragraph(escape(str(c)),styles['SmallTech']) for c in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7f1f4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#146b78')),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6)]));story.append(t)
    markdown.extend(' | '.join(map(str,row)) for row in rows)
def page(): story.append(PageBreak())

title('TechStock AI')
p('CS496 - Project 3: The Operator | Mediterranean Institute of Technology | 16 November 2026')
h('1. Task, tools and architecture')
p('The application helps users procure laptops, desktops and tablets from a local catalog of Tunisian retailer offers. Streamlit calls FastAPI; a stateful LangGraph workflow invokes six official MCP SDK tools over stdio. SQLAlchemy persists SQLite sandbox orders. Scrapling is the sole website fetching and parsing framework. No retailer transaction or payment is implemented.')
table([['MCP tool','Role'],['search_products / compare_offers','Filter hard requirements and rank stored offers'],['check_budget / get_offer_details','Exact totals and auditable source details'],['create_purchase_order','Transactional, idempotent write after approval'],['send_confirmation_email','Durable notification to approved recipient']], [200,285])
h('2. Loop and proof of stopping')
p('The workflow parses and validates requirements, searches, compares, checks budget, builds an immutable proposal, interrupts for a human, then creates an order and sends confirmation. Missing requirements, no feasible offer, rejection and errors terminate explicitly. OpenAI extraction is integrated; ranking and explanations are deterministic. Manual structured input is explicitly labeled.')
p('Before every counted action, consume checks steps < limit and increments once. Every retry consumes another step. By induction, steps never exceed limit <= 12. Each recoverable tool has at most two retries. Forward-only graph edges prevent unbounded autonomous loops. Human waiting performs no polling work; replay does not increment before interrupt. MCP/model calls have 30-second timeouts. Tests exercise low limits, retry exhaustion, rejection and forged resumes.')
page()
title('Safety and measured behavior')
h('3. Human checkpoint and sandbox')
p('The user reviews the exact item, supplier, quantity, unit price, total, budget and recipient. Approval is recorded by a session-scoped backend endpoint and bound to the canonical proposal hash. A model-provided flag or graph resume alone cannot authorize a write. Proposals expire after 30 minutes. Order creation rechecks approval, payload integrity, price, availability, freshness and budget inside BEGIN IMMEDIATE.')
p('Unique proposal/idempotency constraints prevent repeated and concurrent confirmation from duplicating an order. Item snapshots preserve approved pricing across scraper refreshes. The order and email outbox commit together. Development, test and evaluation databases are separated; reset commands are scoped to recognized project paths. Sandbox SMTP is local only; no external messages were sent.')
h('4. Trajectory evaluation results')
p('Forty reproducible cases cover 12 normal requests, 8 budget/availability cases, 8 failures, 7 injections and 5 stopping cases. The runner uses real LangGraph, MCP transport and SQLite with a fixture parser and stubbed email transport. These results measure deterministic control paths, not live language-model quality. Expected arguments, sequence, writes, outcomes and stop reasons are checked.')
table([['Metric','Measured result'],['Task success / step accuracy',f"{metrics['passed']}/{metrics['cases']} / {metrics['step_accuracy']:.1%}"],['Tool-call precision / wasted steps',f"{metrics['tool_call_precision']:.1%} / {metrics['wasted_steps']}"],['Recovery / injection / stop compliance',f"{metrics['recovery_after_failure_rate']:.1%} / {metrics['prompt_injection_resistance']:.1%} / {metrics['stop_rule_compliance']:.1%}"],['Mean / p50 / p95 latency',f"{metrics['average_latency']:.3f}s / {metrics['p50_latency']:.3f}s / {metrics['p95_latency']:.3f}s"],['Automated pytest suite',f"{passed} passed; {suite.attrib['skipped']} opt-in live test skipped"]],[240,245])
p('Timing excludes MCP process startup and human deliberation. Additional tests exercise real local SMTP, API session isolation, concurrent idempotency, rollback, price changes, saved HTML parsing and all Streamlit pages. A real-catalog API smoke test completed an eight-step sandbox order, captured its email locally, and confirmed that a second click returned the same order.')
page()
title('Errors, attacks and evidence')
h('5. Error taxonomy and recovery')
table([['Failure class','Response'],['Invalid/missing/unsupported requirements','Reject or ask clarification before searching'],['Unknown stock, stale data, insufficient budget','No feasible offer; no write'],['Transport timeout/connection failure','At most two retries within global step limit'],['Changed price/payload, expired proposal','Reject; require a fresh proposal and approval'],['Database failure','Transaction rollback; no partial order/outbox'],['SMTP failure before delivery','Order survives; failed notification may be retried'],['Ambiguous SMTP acknowledgement','No automatic resend; manual reconciliation'],['Scraper block or robots failure','Fail closed; no access-control bypass']],[220,265])
h('6. Injection threat model')
p('Untrusted entry points include retailer descriptions, names, URLs and user requests. Attackers may try budget overrides, fake system authority, unauthorized writes, recipient redirection, unsafe links, infinite loops, or forged price/stock statements. Seven explicit injected-content scenarios passed. Backend constraints, typed tool schemas, HTTPS domain checks, immutable approval records and bounded execution contain these attacks.')
p('Raw descriptions are retained for audit and are not sent to the model. Therefore the seven tests demonstrate the implemented data/permission boundary, not a general claim about model robustness. A retailer can still publish plausible false structured data; provenance and human review do not prove real-world truth. Local database/process compromise is outside this localhost demo threat model. SMTP exactly-once delivery across a crash is not claimed.')
h('Observed development problems')
p('Real integration tests exposed MCP v2 API changes, Scrapling optional dependencies, Windows icon encoding and Streamlit test path changes. Retailer blocks and terms required changing the live source. LangSmith read-after-write needed indexing time. These incidents and fixes are recorded in postmortem.md, rather than presenting development as failure-free.')
page()
title('Collection, cost and limitations')
h('7. Verified data and integrations')
p(f"The delivery catalog contains {catalog['real_offers']} real offers and {catalog['demo_offers']} demo offers. Supplier counts: {catalog['by_supplier']}. Category counts: {catalog['by_category']}. Validation checked positive prices, allowed source URLs, timestamps, stock enums, quantities and uniqueness. Nullable specifications and quantities remain unknown when not published.")
p('Spacenet normal HTTP collection and pagination are verified with a ten-second minimum delay. Mytek returned 403; no bypass was attempted. Tunisianet bulk collection is disabled because its terms prohibit catalog reproduction. The initial laptop run stopped on a robots DNS timeout; a retry collected 33 laptop offers, with one product request timing out. A subsequent one-off refresh updated its existing record without inserting a duplicate. Exact collection reports accompany the repository.')
p('MCP transport, LangGraph interrupt/resume, local SMTP and LangSmith synthetic trace write/read were verified. The configured OpenAI API returned HTTP 429: no credits remaining. Thus live natural-language extraction and live model token cost remain unverified. Manual structured mode demonstrates the remaining workflow. Docker Compose is supplied, but its engine was not running. Browser automation was unavailable; Streamlit rendering was tested with AppTest.')
h('8. Cost analysis and reproducibility')
p('The offline suite used zero model tokens and zero model API cost. Its 100x replay model cost is also zero; this does not estimate a live workload. For a live task, cost = (input_tokens x input_rate + output_tokens x output_rate) / 1,000,000. For 100 times a measured workload, multiply the observed total by 100. Rates are configurable and left unknown unless verified. No live cost figure is fabricated.')
p('Run: python -m pytest -q; python -m eval.trajectory_eval; python -m scraping.refresh_catalog --retailer spacenet --limit 34. Setup and launch commands, environment configuration, reset instructions and integration limits are in README.md. Full measured trajectories are in eval/results.json; test results are in eval/pytest-results.xml.')
p('Team contribution names were not supplied. Code, tests and documentation were generated with Codex; students must review, explain and record their actual contributions before submission.')

def footer(canvas,doc):
    canvas.setStrokeColor(colors.HexColor('#d6e1e8'));canvas.line(42,39,553,39)
    canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#536a7a'));canvas.drawString(42,27,'TechStock AI | Sandbox procurement | CS496');canvas.drawRightString(553,27,str(doc.page))
Path('output/pdf').mkdir(parents=True,exist_ok=True)
out=Path('output/pdf/report.pdf')
SimpleDocTemplate(str(out),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=40,bottomMargin=52).build(story,onFirstPage=footer,onLaterPages=footer)
shutil.copyfile(out,'report.pdf')
Path('report.md').write_text('\n\n'.join(markdown),encoding='utf-8')
from pypdf import PdfReader
pages=len(PdfReader('report.pdf').pages)
assert pages<=4,f'Report exceeds four pages: {pages}'
print('Generated report.pdf:',pages,'pages')
