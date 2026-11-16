# Contributing to TechStock AI

Use Python 3.11 and follow README setup with your own `.env`. Start with synthetic demo data and local SMTP. Do not require another teammate's database or credentials.

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/short-description
# Make and review your changes, then run:
python -m pytest -q
python -m eval.trajectory_eval
python -m eval.ranking_eval
python scripts/smoke_demo.py
git diff --check
git status --short
# Stage only reviewed source/docs/tests. Inspect git diff --cached before committing.
```

Run these checks sequentially: tests and evaluations use dedicated disposable databases. The smoke demo creates an isolated synthetic database and local SMTP listener, ignoring real Gmail settings. Do not enable RUN_LIVE_OPENAI during offline checks. It opts into network use and potentially paid inference.

Open a pull request describing the problem, behavior change and actual verification results. Keep changes focused. Preserve server-authorized selection, separate hashed proposal approval, the shared 12-step limit, order/email idempotency, SMTP allowlisting and sandbox purchasing. Record new evaluation definitions separately from generated results. Do not describe offline fixture pass rates as live model accuracy.

Before each commit inspect staged files for secrets or personal information. Use example.com/test addresses in fixtures. Never commit .env, passwords, tokens, captured emails, local databases or private trace URLs. If a secret is committed, stop publication, rotate it and coordinate remediation; ignoring it does not erase history. Do not force-push shared history.

The academic report belongs in root report.pdf/report.md. Its builder also writes an ignored output/pdf copy. Rebuilding requires fresh local pytest XML and eval/results.json; preserve historical evidence unless deliberately documenting a new measured run. Team members should record their actual contributions; names and responsibilities must not be fabricated.
