# MSME Capital — Business Finance Workspace v0.4

Borrower-led synthetic lending demonstration: Vue 3 + TypeScript + Vite, Litestar + Pydantic, SQLAlchemy/PostgreSQL, deterministic financial tools and an evidence-backed CAM. All OTP, KYC, bank, tax, bureau, Udyam and CBS operations are synthetic. No SMS, real bank API, Aadhaar lookup or money movement occurs.

## Business experience refresh

The borrower portal and credit workspace use a warm cream, forest-green and sage visual system, responsive layouts, clear application steps, readable evidence summaries, business account names and a sanction register. Environment labels are excluded from customer-facing screens; internal fixture identifiers and source records remain unchanged. Display aliases are presentation-only, not verified identities. This is a presentation upgrade, not a production-readiness certification or activation of live banking services.

Use **docs/BUSINESS_UI_WALKTHROUGH.md** for current screen names and the end-to-end path. The older tester PDF uses earlier labels. Configuration and engineering documentation deliberately retain accurate environment descriptions.

## Voice interviews: Pipecat + Sarvam

The **Verification & terms** screen now includes a guided voice interview. `VOICE_MODE=mock` runs typed interviews through Pipecat with no external calls. Set `VOICE_MODE=sarvam` and your server-side `SARVAM_API_KEY` for browser microphone recognition and speech playback. English, Hindi and Tamil prompts are included. All loan data remain synthetic; live microphone audio is sent to Sarvam only after consent.

See **docs/VOICE_SETUP.md** for environment values, browser steps, troubleshooting and live acceptance tests. The included tester PDF covers the borrower journey; this voice guide supplements it. Voice transcripts are unverified evidence, cannot approve a loan and require fresh officer verification before a new CAM. This is a guided browser interview, not a phone dialer or biometric KYC service.

## Start or upgrade on Windows

For an existing install: back up your project and database, stop the containers with `docker compose down`, replace the source files from this ZIP, and keep your existing `.env`. Do not delete volumes. New profile, OTP and session tables are added automatically; existing cases remain available as legacy officer-created cases.

For a fresh install, copy `.env.example` to `.env` once. For an upgrade, do not overwrite your existing database password or staff tokens.

```powershell
# Fresh installation only:
Copy-Item .env.example .env
# Fresh installation or upgrade:
docker compose up --build -d
docker compose ps
```

Open http://localhost:8080. The borrower portal is now the default landing page. The first 100 synthetic profiles are inserted automatically; do not run the old scenario seed command to start the borrower flow.

### Complete the first case

1. Select `SYN-0001 / Synthetic Owner 001 / consistent`.
2. Get the demo OTP and enter the code shown on screen. No SMS is sent.
3. Complete a separate synthetic KYC OTP. Keep the provided PAN and DOB unchanged.
4. Accept all five demo consents, then request INR 1,000,000 for 36 months, Term loan.
5. Submit. The backend fetches matching synthetic bank/GST/ITR/financial/KYC evidence and mock bureau/Udyam details, then analyzes it.
6. Open **Credit team portal**. Sign in with `ANALYST_TOKEN` from your `.env` (credit officer).
7. Search `DEMOPAN0001` and open the application. In **Verification & terms**, tick all three interview checks, enter interview notes and market assessment, then save. Click **Run analysis**.
8. If you change amount, tenure or rate, save and rerun. Any rate different from the base rate needs manager approval. The default hard rate interval is base minus 1 through base plus 5 percentage points.
9. Sign out of staff view and sign in with `REVIEWER_TOKEN` (branch manager). Approve any pending rate exception, then rerun analysis. Inspect CAM and all policy checks. In **Human review**, enter a reason and approve.
10. Check **Mock ledger**. Return to **Borrower portal**, track the application and refresh status. No real disbursal occurs.

| Role | Credential | Permissions |
| --- | --- | --- |
| Borrower | On-screen synthetic OTP | Own applications, consented fetch, additional evidence, clarifications and tracking |
| Credit officer | `ANALYST_TOKEN` | Staff search, evidence analysis, verification, terms, evidence requests/resolution |
| Branch manager | `REVIEWER_TOKEN` | Staff access plus rate exceptions and final decisions |

Keep staff tokens distinct. Existing ANALYST_TOKEN and REVIEWER_TOKEN variable names remain compatible. Borrower sessions last eight hours; OTPs expire after five minutes, allow five attempts and are single-use. KYC proofs are bound to the same profile, valid for 30 minutes and single-use per application.

### Profiles and testing

```powershell
# Increase demo profiles, idempotently (100–500):
docker compose exec api python generate_profiles.py --count 500
# Run isolated backend tests (test credentials are set by the test suite):
docker compose exec api python -m pytest -q
# Inspect local logs:
docker compose logs --tail 100 api
```

Profile scenarios repeat every six IDs: consistent, low bureau, missing GST, low capacity, GST mismatch, balance drop. Profile 1, 7, 13, etc. are consistent. Profile 3 omits GST during fetching; upload `fixtures/synthetic_cases/01_consistent/gst.json` as additional GST evidence to resolve it. The profile's KYC is generated for its own name, so do not replace it with Asha Mehta's legacy KYC.

See `docs/SYNTHETIC_JOURNEY_TESTING.md` for the current manual test guide. Existing twelve fixture scenarios and `seed.py --scenario all` remain available for legacy regression testing only; running seed again creates more cases.

### Environment and endpoints

No bank or OTP provider keys are needed. Optional live voice requires a Sarvam API key; mock voice does not. Keep `LLM_MODE=mock` for fully local deterministic testing. Optional Ollama explanation mode is unchanged; it cannot approve a loan or alter calculations.

UI: http://localhost:8080; API schema: http://localhost:8000/schema; health: http://localhost:8000/api/health.

`docker compose down` retains database/upload volumes. Do not use `down -v` unless you intend to delete your demo data. HTTP ports bind to localhost. The staff token scheme and visible demo OTPs are for local synthetic demonstration only.

## Run without Docker

Python 3.12+, Node 22+, optional local PostgreSQL and Tesseract. In PowerShell:

```powershell
cd server
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# SQLite is used only when DATABASE_URL is absent, for a lightweight demo/test.
# To use PostgreSQL instead:
# $env:DATABASE_URL='postgresql+psycopg://user:password@localhost:5432/msme'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

In another terminal:

```powershell
cd client
npm ci
npm run dev
```

Open http://localhost:5173. In a third terminal, with the Python environment active:

```powershell
cd server
python seed.py --scenario 01_consistent
# Or --scenario all
python -m pytest -q
```

Frontend checks: `npm run build` and `npm test` from `client`.

Local Python processes do not automatically load `.env`; export the desired environment variables in your shell. Compose reads `.env` automatically. `server/migrations/001_initial.py` can apply the initial migration explicitly; startup also applies it idempotently. Future schema changes require additional migrations; `create_all` is not a general upgrade system.

## Walk through additional evidence

Use scenario `08_additional_evidence`. Initial KYC lacks fields. In Documents choose `kyc`, select the current KYC document in **Replacement**, and upload `fixtures/synthetic_cases/01_consistent/kyc.json`. Re-run analysis. The old extraction, memo and checkpoints remain in history; approval accepts only the current revision. For reviewer-requested clarifications, submit replacement evidence, then resolve the request under Human review with a source/rationale before re-running analysis. A note alone never overrides deterministic policy failures.

## Supported documents — explicit MVP boundary

This MVP does **not** claim general extraction accuracy for arbitrary bank, GST or ITR layouts. Upload either supplied synthetic JSON documents or the strict synthetic PDF template below. Unsupported layouts fail visibly and need manual mapping. Source text and normalized values are applicant-supplied evidence assertions, not independently authenticated facts. A `synthetic: true` assertion is required; it does not technically prove uploaded data is synthetic. Use no real personal data.

Each JSON file is one document. See `fixtures/synthetic_cases/01_consistent/*.json`. The complete Pydantic schema is `server/app/schemas/__init__.py`; uploads validate page references, dates, nonnegative declarations, positive transaction amounts and reporting periods. All amounts are INR. Do not upload the top-level scenario bundle as a document; use the individual files in its named folder.

Text PDF format:

```text
SYNTHETIC: true
DOCUMENT_KIND: bank
EXPECTED_PAGES: 1
PERIOD_START: 2025-04-01
PERIOD_END: 2026-03-31
TX|SYN-001|2025-04-05|500000|credit|operating|SYN-CUSTOMER|SYN-BUSINESS|1000000|INR
```

For a financial document, use:

```text
SYNTHETIC: true
DOCUMENT_KIND: financial
EXPECTED_PAGES: 1
PERIOD_START: 2025-04-01
PERIOD_END: 2026-03-31
FIELD|financial_turnover|6000000
FIELD|existing_monthly_debt|20000
```

Supported field names: `gst_turnover`, `itr_turnover`, `financial_turnover`, `existing_monthly_debt`, `legal_name`, `tax_id`. Bank transactions require stable account IDs, transaction reference, date, positive amount, direction, category and literal supporting text. Categories: `operating`, `transfer`, `loan`, `refund`, `debt`, `unknown`. Unknown classifications block cash-flow eligibility. Refunds/transfers/loans are excluded from operating revenue, with no inferred reclassification. Netting refunds against operating receipts needs manually corrected synthetic evidence.

PyMuPDF extracts text by page. Low-text pages use local Tesseract; a missing OCR executable or unreadable page fails visibly. PDF workers enforce 50 pages, a 15-megapixel/page raster limit, 200,000 text characters/page and a configurable 90-second document timeout. Linux workers additionally set CPU/address-space limits. Windows has the subprocess deadline and page/raster boundaries but no Linux `resource` limits. Maximum upload is 10 MiB. JSON text is structurally validated, not OCR-processed.

## Analysis and orchestration

`server/app/workflows/engine.py` is the single defined orchestrator. It uses a persistent sequential dependency graph rather than adding LangGraph beside an existing orchestrator:

1. Document Intelligence — parsing, page inventory, field provenance, KYC identity completeness.
2. Reconciliation — same-period bank/GST, GST/ITR and GST/financial turnover checks.
3. Cash-Flow Analysis — deterministic monthly summaries, cash flow, debt, EMI, DSCR, affordability and amortization.
4. Fraud Investigation — repeated stable transaction references, bounded directed fund cycles and negative balances.
5. Credit Risk — documented evidence completeness and observed cash-range summary; no predictive score.
6. Policy and Eligibility — versioned hard checks with inputs and evidence IDs.
7. Loan Structuring — proposed terms only when all checks pass.
8. CAM Generation — structured evidence-backed report, optional isolated Agno/Ollama narrative.
9. Human Review → atomic Mock Ledger entry.

Specialist outputs are validated through `schemas/agents.py`; agent identity/version, timestamps, model config and policy version are checkpointed. Agents call typed deterministic tools directly. No A2A or MCP service is added without an interoperability need. Deterministic specialists remain usable with Ollama offline; only the optional explanation uses Agno/LLM. This design is deliberately rules-led, not seven LLM calls simulating independent underwriting judgments.

Completed nodes commit checkpoints and are reused on retry. Failed nodes record errors and resume without recreating completed extraction or CAM rows. One analysis/document/review critical section runs per API process; **use one worker and one API replica**. Run initiation waits for completion, while the frontend polls the status endpoint; there is no production job queue.

Evidence changes invalidate parsing and its financial/fraud/risk/policy/CAM descendants; previously parsed unchanged documents are reused. Reviewer clarification changes invalidate CAM only and copy unchanged predecessor checkpoints. Policy-version changes invalidate financial and downstream outputs on the next run. This is dependency-based invalidation at document-analysis granularity, not arbitrary field-level incremental computation. Old results remain queryable as history. Approved/rejected cases are frozen.

## Financial conventions and configurable policy

All critical arithmetic uses Python `Decimal`; JSON/display amounts are rounded to paise. DSCR uses **annualized net operating cash flow / annual debt service including both existing obligations and the proposed EMI**. Existing debt is the maximum of the explicit declaration and observed average monthly debt payments. Missing debt is unknown, never zero. A zero or missing DSCR denominator returns unknown.

Only complete reporting months count. Bank/GST operating receipts must reconcile over identical declared coverage dates before cash flow is eligible. A declared month with no transactions is treated as no activity only within a complete declared page/period inventory; missing statements are not inferred complete. This is not a bank-authenticated completeness check. A six-month annualization may miss seasonality; assumptions are visible. Raw bank credits never become operating revenue by default. Bank operating classifications are source assertions; period/tolerance matching is only a consistency check.

EMI uses a nominal annual percentage rate divided by 12, monthly reducing balance, with no processing fees, tax, grace period or balloon payment. Zero interest uses principal/months. Affordability inverts EMI after reserving the configured minimum DSCR. Every financial report contains formulas, inputs, units, assumptions and evidence IDs.

`policy.demo.json` contains **demo thresholds**, not lending standards. Set `POLICY_FILE` for a local process; Compose includes this file in the API image. To change policy, increment `version`, edit values, rebuild/restart API and re-run affected cases. Existing version contents cannot be silently overwritten. Review rejects a memo prepared under a different current policy version. No UI/API allows uploaded documents or LLMs to change policy. Exceptions require resolved/corrected evidence and reanalysis; no hard-rule override is provided.

Fraud flags are investigation leads, not proof. Cycle search uses directed exact account/amount links of 2–4 transactions within 3 days, with a 20,000-edge exploration budget. A search-budget limit itself requires review. Duplicate references are counted once in metrics but still block approval pending evidence resolution. No external account verification, fuzzy entity resolution or network-wide AML coverage is claimed. Leverage is marked insufficient because this template does not map balance-sheet equity/liability schedules.

## Optional Ollama

The default `LLM_MODE=mock` is deterministic and clearly labeled. No model is automatically downloaded or selected for unknown hardware. On the target 16 GB RAM / up-to-8 GB VRAM machine, first inspect actual available RAM/VRAM and check a model's quantized memory requirements. Test one small compatible quantized model with Ollama, then set:

```text
LLM_MODE=ollama
OLLAMA_MODEL=<your-tested-local-model-tag>
LLM_TIMEOUT=45
LLM_RETRIES=1
```

Run Ollama on the Windows host; Compose connects through `host.docker.internal`. For local Python set `OLLAMA_HOST=http://localhost:11434`. Restart API after configuration changes. One model request is active at a time, with a 4096 context setting and 400 output-token cap. Only bounded deterministic policy summaries/evidence IDs reach the LLM, never full PDFs, credentials, tools or approval state. Model unavailability/invalid output is disclosed and does not break deterministic analysis. Model explanations are unverified, visibly labeled and never alter policy, amounts, approval or ledger data. Agno's installed provider modules require the `openai` Python SDK as an import dependency; no OpenAI key or remote API call is used.

## API overview

All endpoints except health and schema require `Authorization: Bearer <token>`. JSON input schemas appear in OpenAPI. Multipart uploads use field name `data` and a `kind` query parameter; `replaces=<document-id>` explicitly supersedes a same-kind document. There is no unauthenticated file-serving directory.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Database connectivity, synthetic and LLM mode |
| GET / POST | `/api/applications` | Persisted dashboard/list, create case |
| GET | `/api/applications/{id}` | Case, document inventory, checkpoints, versions and decisions |
| GET / POST | `/api/applications/{id}/documents` | List/upload/additional evidence or explicit replacement |
| GET / POST | `/api/applications/{id}/runs` | Status/checkpoints, start or resume analysis |
| GET | `/api/applications/{id}/evidence` | Paginated extracted fields and transactions |
| GET | `/api/applications/{id}/analysis/{section}` | `financial`, `reconciliation`, `risk`, `policy` |
| GET | `/api/applications/{id}/cams` | All structured memo versions; compare current revision |
| POST | `/api/applications/{id}/evidence-requests` | Reviewer clarification request |
| POST | `/api/applications/{id}/evidence-requests/{request_id}/resolve` | Reviewer resolution and rationale |
| POST | `/api/applications/{id}/review` | Approve, reject, request evidence; revision checked |
| GET | `/api/applications/{id}/audit` | Paginated append-only history |
| GET | `/api/ledger` | Paginated mock approved proposals |

List endpoints support bounded `offset`/`limit`. The UI shows newest 100 applications/ledger items, first 500 evidence/audit records; API provides further pages. CAM itself retains all financial evidence references. HTTP 401/403 identify missing authorization/role, 409 stale/busy/finalized/duplicate operations, 413 excessive upload, and 422 explicit input/file errors. Framework body-validation failures use its standard structured 400 validation response. Analysis returns 200 with an explicit failed node when a workflow fails; inspect run status. The backend does not stream progress by bytes after intake.

## Persistence and security

PostgreSQL is the Compose database. SQLite is a developer/test fallback. The model includes all 16 requested record types, foreign keys, case indexes, timestamps, revision checkpoints and uniqueness constraints. Semi-structured specialist outputs use JSON columns. Initial migration creates append-only database triggers for audit and reviewer decisions. PostgreSQL row locking plus compare-and-set status, unique case-ledger and decision constraints make approval/ledger insertion atomic and duplicate-safe. A repeated approval returns 409 rather than inserting a second row.

Private uploads use generated IDs outside static web directories, content hashes and non-public filesystem permissions. Source filenames are display metadata only. SQLAlchemy parameterizes queries. Document content cannot become executable instructions: deterministic mapping does not execute document code and the narrative agent has no tools or permission path. The frontend renders text interpolation, never document HTML. LLM-supplied evidence IDs are checked against the supplied set; narrative factual accuracy is not claimed.

Remaining production work includes real authentication/SSO, tenant and case authorization, TLS, encryption/key management, malware scanning, document authenticity checks, provider-specific extraction validation, job infrastructure and cross-process locks, comprehensive data retention, full migration tooling, operational monitoring/backups and domain/compliance review. Append-only triggers protect application-level SQL writes, not a privileged database administrator. Do not deploy this demo as a real underwriting service.

## Repository

```text
msme/
  client/src/{components,pages,api,stores,types}/
  server/app/{api,models,schemas,agents,workflows,tools,security}/
  server/app/services/{documents,reconciliation,financial,fraud,policy,cam}/
  server/app/config.py
  server/migrations/
  server/tests/
  fixtures/synthetic_cases/
  docker-compose.yml
  policy.demo.json
  .env.example
  README.md
```

`VALIDATION.md` records verified behavior and environment limits. `docs/ARCHITECTURE.md` describes persistence, trust boundaries and workflow dependencies.
