# Architecture and trust boundaries

The browser calls Litestar with a local role token. Litestar schemas validate input and delegate business operations to case/document/workflow services. SQLAlchemy persists PostgreSQL records; generated upload paths live on a separate private volume. No uploaded content is served as HTML or imported as Python. ORM and typed checkpoint schemas provide a stable application boundary.

## Persistent graph

`documents → reconciliation → cashflow → fraud → risk → policy → structure → cam`

This single explicitly defined orchestrator is sequential to fit limited hardware. Fraud uses normalized transactions, not cash-flow numeric conclusions. Node results are checkpointed per case/revision/node and committed separately. Node failures do not erase completed predecessors. A failed CAM can resume without rerunning deterministic tools. Explicit evidence replacement advances the revision, retains all old records, reuses already parsed unchanged documents, and invalidates the dependent graph. Reviewer text requests/resolutions invalidate only CAM. Policy changes rerun financial outputs whose rate/DSCR parameters may differ.

The long-running HTTP request is dispatched to a worker thread. Read-only status endpoints remain usable for polling. The single-process asyncio lock bounds analysis, uploads and review mutations. PostgreSQL locks provide a transactional review/evidence boundary, but multiple API replicas are unsupported: there is no distributed workflow lease. Use one worker.

## Data records

Applications own documents, source fields, transactions, agent checkpoints, reconciliation findings, financial metrics, risk flags, policy evaluations, evidence requests, CAM versions, reviewer decisions, audit events and mock-ledger entries. Demo users identify trusted reviewer principals. Policy rules are independently versioned. Every checkpoint and memo carries a case revision; policy evaluations carry a policy version. Only active document evidence feeds current extraction; superseded evidence is retained.

Reviewer decisions and audit events are append-only by database trigger. Loan ledger entries are unique per case and decision. Approval checks the review revision, current analysis/CAM, current policy version, all policy outcomes and unresolved reviewer requests in the same transaction that creates the decision/ledger entry. Rejection freezes the case. Additional analysis cannot overwrite approval state.

## Financial source boundary

Structured facts are claims derived from synthetic source documents. Each retains document ID/name, page, source text and evidence ID. Numeric metrics carry formulas, units, input values, assumptions and source references. Reporting periods must align for turnover comparisons. Missing debt/data is unknown; raw credits are never silently promoted to turnover. Model output has a separate unverified-explanation label.

## Untrusted content and model boundary

PDF parsing occurs in a subprocess with page, raster, text, time and Linux memory/CPU boundaries. OCR itself uses a bounded process without a shell. JSON is validated through Pydantic and treated as data. The Agno/Ollama agent receives only bounded verified policy outputs/evidence IDs, no raw source text, no filesystem/API tools and no credentials. Its output cannot reach review or ledger functions. Citation allow-list validation catches unsupported IDs but does not prove narrative factual correctness; deterministic CAM facts are the review basis.

## Resource model and deployment

Compose: PostgreSQL ≤1 GiB, API ≤3 GiB, Nginx ≤256 MiB; Ollama is optional on the host. These are configuration caps, not measured operating footprints. One document parser/model call is active at a time. Quantized model selection is intentionally left to inspection of real hardware. No benchmarks, token savings or extraction-accuracy claims are made.

The initial migration is idempotent on a fresh schema and includes audit triggers. It does not replace Alembic or a production migration history. Existing installations changing columns need a new explicit migration. Tests default to SQLite; Compose PostgreSQL needs its own integration pass in the target Docker environment.

## Synthetic borrower journey v0.2

New additive tables store synthetic provider profiles, single-use OTP challenges and hashed expiring borrower sessions. `/api/borrower/*` enforces ownership separately from the staff-token API; a borrower token never grants staff access. Demo OTPs are intentionally displayed, not sent. Consent IDs, source identifiers and retrieval timestamps are recorded with the case. Profiles are generated from the consistent fixture with deterministic scenario variations (100 by default, up to 500).

Integrations are local Python adapters invoked by typed HTTP endpoints. `services/integrations/synthetic.py` documents a schema registry, but does not expose an actual MCP transport/server. Provider retries preserve active uploaded evidence. Case identity comes from the matched synthetic KYC profile, preventing the earlier applicant-name prefix mismatch in the new wizard.

Credit officers record simulated interview and property results and propose terms; managers approve rate exceptions and final sanction. New CAM-only checks enforce consent, business verification, bureau threshold, interview, rate exception and property gates. Approval repeats those gates inside the database transaction. Rate changes invalidate cashflow and all downstream nodes. Human verification and rate decisions invalidate CAM. The current terms are the ones used for deterministic EMI/DSCR and ledger posting. The non-overridable demo rate bounds are base minus 1 through base plus 5 percentage points.

Legacy officer-created cases retain their original flow and controls. Existing records are not retrospectively treated as borrower-submitted cases. All three portals use the same existing shared case file and immutable audit/decision history.

## Voice integration v0.3

Staff starts consented, revision-bound voice sessions. Short-lived, single-use tickets authenticate the WebSocket before Pipecat/Sarvam is instantiated. The pipeline is Sarvam realtime STT -> bounded interview frame processor -> Sarvam TTS -> browser audio output. Mock mode bypasses providers but retains Pipecat orchestration. Guided turn submission is explicit and never invokes an LLM or loan tools. Three fixed prompts collect unverified answers only. Completing a current interview clears human verification and invalidates CAM; stale sessions preserve the transcript without mutating a newer/final case. Active voice sessions block final approval. Transcripts and session metadata persist separately; no raw microphone audio is stored by this app.
