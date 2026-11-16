# GitHub publication audit - 16 November 2026

## Intended tracked content

- Application source: agent/, app/, backend/, mcp_server/, scraping/ and sandbox/.
- Reproduction: scripts/, requirements.txt, pytest.ini, .streamlit/config.toml, Dockerfile, docker-compose.yml, .dockerignore, .env.example, .gitignore and .gitattributes.
- Tests: tests/ including the minimal documented Spacenet HTML parser fixture; eval/ runners, scenarios and selected historical non-private measurement summaries.
- Documentation: README.md, CONTRIBUTING.md, verification.md, threat_model.md, errors.md, postmortem.md and this audit.
- Academic deliverables: root report.pdf/report.md and project3-operator.pdf (assignment brief). data/.gitkeep creates the runtime directory in a fresh checkout.

No application architecture changes or existing database/secret modifications were needed. Existing recommendation/selection changes are retained. The setup helper now runs from the repository root and stops on failed Python commands.

## Files kept locally but removed from publication tracking

| Paths | Purpose and reason |
| --- | --- |
| data/inspection/ | Raw discovery/robots/terms/product HTML captures, roughly 6 MB; not runtime or test dependencies. Minimal parser fixture remains under tests/fixtures/. |
| tmp/pdfs/ | Generated visual QA previews; not source or academic deliverables. |
| output/pdf/report.pdf | Generated duplicate of the canonical root report.pdf; report builder recreates it. |
| data/langsmith-verification.json, eval/langsmith-verification.json | Duplicate private run/project IDs and trace links. Historical success remains documented without these identifiers. |
| data/smoke-demo.json | Generated synthetic run snapshot; scripts/smoke_demo.py regenerates it. |

These files are not deleted from the local workspace. Ignore rules alone do not untrack files, so the publication cleanup removes only these exact paths from the Git index. Existing commits remain unchanged and still contain the original artifacts. No force-push or history rewrite is performed.

Other intentional exclusions: .env and secret variants, private key formats, .streamlit/secrets.toml, environments/caches, SQLite/checkpoint files and journals, captured SMTP emails, scraper outputs, logs, IDE files, build outputs and current generated evaluation results. .env.example, academic reports, test fixtures and scenario definitions remain included.

## Security and size review

The one existing reachable commit and prospective publication files were scanned for known API/private-key token patterns and exact configured secret values without printing those values. Prospective files were additionally compared with configured SMTP identities; PDF text was inspected by extraction. No configured credential matches were found, and .env/databases were never tracked in the inspected history. No credential rotation is indicated by this audit. This heuristic scan is not a proof that every possible secret format is absent.

Private LangSmith trace identifiers were found in history, not API credentials; they are excluded from the next tree, but remain in the original commit. Access to traces depends on LangSmith project permissions. Public retailer addresses in archived HTML are third-party content. Security fixtures deliberately include attacker@example.org and an evil.test URL user-info attack; these are synthetic, not personal contact details.

No intended retained file exceeds 1 MB. The academic assignment brief and root report are intentional PDFs; .gitattributes marks PDFs binary to prevent newline conversion. No generated previews or raw inspection HTML are required to clone and run.

## Verification and limits

Clean-copy verification uses only prospective tracked files plus .env.example, with new databases in a temporary directory and the existing installed Python 3.11 virtual environment. It checks imports, FastAPI routes, database initialization, seeding, pytest (including Streamlit AppTest), both evaluations and the isolated actual local-SMTP demo. Results are recorded in docs/publication-checks.json. No real Gmail email or live OpenAI request is made in this audit.

The installed pinned environment passes pip check. A new network download/install into a second virtual environment was not repeated; package-index access is needed on teammates' machines. Historical measurements are preserved; this audit records a separate run. Offline policy/control-flow pass rates are not recommendation accuracy. Live OpenAI remains blocked by the previously observed credit limit; Docker engine startup and full browser visual interaction remain unverified.

## Publish safely

Origin is already https://github.com/nourguidara/TechAI.git and the local branch is main. No commit or push is performed by preparation. Review cleanup deletions as removals from tracking only; local files remain.

```powershell
git status --short
git diff --check
git diff --cached --stat
# Confirm ignored local secrets/databases are absent from git ls-files.
git add .gitignore .gitattributes .dockerignore .env.example README.md CONTRIBUTING.md docs verification.md
# Include the reviewed application upgrade, tests and canonical report:
git add agent app backend sandbox tests eval/scenarios.json eval/trajectory_eval.py eval/ranking_eval.py eval/ranking_scenarios.json scripts report.md report.pdf
git diff --cached --stat
git diff --cached -- .env.example
git commit -m "Prepare TechStock AI recommendations and team onboarding"
git fetch origin
```

If origin/main exists, reconcile its history before pushing:

```powershell
git merge origin/main
# Resolve conflicts deliberately and rerun checks if code changed.
git push -u origin main
```

If the new remote has no main branch, skip the merge and run `git push -u origin main`. If Git reports unrelated histories (for example a separately created GitHub README), inspect both histories and use `git merge --allow-unrelated-histories origin/main`, resolve conflicts, commit and rerun relevant checks. Do not force-push, reset away remote commits or overwrite teammates' work. The ordinary push will reject an unexpected non-fast-forward update.
