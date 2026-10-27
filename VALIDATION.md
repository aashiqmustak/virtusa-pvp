# Validation record

Verified in this workspace:

- Backend: 22 pytest tests passed, using isolated SQLite databases.
- Frontend: Vue/TypeScript production build passed; 2 Vitest tests passed.
- Live HTTP smoke test: created and uploaded a consistent synthetic case, ran all analysis nodes, retrieved persisted dashboard counts and a current CAM. DSCR was 4.0607 for the supplied consistent fixture.
- OpenAPI JSON and Vite HTML returned HTTP 200.
- Docker Compose YAML parsed successfully.
- Chromium browser flow passed: token login, persisted dashboard, case analysis, CAM print-to-PDF, reviewer approval and mock-ledger display. Mobile viewport had no page-level horizontal overflow; no browser page errors were observed.
- Desktop/mobile screenshots and the first printed CAM page were visually inspected. The sample CAM printed to 5 pages with its evidence appendix.
- The actual Agno/Ollama adapter was instantiated against an unavailable endpoint; graceful fallback passed.

Covered backend behavior: EMI/amortization and zero-interest handling, unknown/zero DSCR denominators, period/tolerance rules, all six adverse financial/document scenarios, authorized atomic approval, unauthorized review (403), duplicate approval prevention (409), additional evidence and stale-CAM invalidation, checkpoint retry, crash recovery, append-only audit protection, document prompt injection isolation, missing debt, rejected file input, strict dates/amounts, template-PDF source extraction, unrecognized PDF rejection, failed document approval blocking, reviewer request resolution, and unavailable LLM fallback.

Not verified here: a Docker image build or PostgreSQL runtime (Docker unavailable), successful inference on an installed Ollama model (no model/hardware supplied), and real-world document accuracy. General document formats intentionally require manual mapping. OCR support is implemented but scanned-page extraction quality has not been evaluated.

To run PostgreSQL integration tests in the target Compose environment, use a separate test database (never production data):

```powershell
docker compose exec db createdb -U msme msme_test
docker compose exec -e TEST_DATABASE_URL=postgresql+psycopg://msme:local-db-change-me@db:5432/msme_test api python -m pytest -q
```

Substitute your configured database password, URL-encoded if necessary. Tests append synthetic records to that dedicated database.

All thresholds are demo configuration. No measured extraction accuracy, predictive credit performance, token savings, latency or cost claims are made.

## Synthetic journey v0.2 validation

- 32 backend tests passed across the full regression run and targeted additions on isolated SQLite, including ten new journey tests covering OTP expiry/replay/attempts, consent, borrower isolation, manager-only rates/final approval, deterministic rate recalculation, missing GST resolution, property gates and duplicate ledger prevention.
- Frontend TypeScript/Vite production build passed; two existing Vitest tests passed.
- Chromium browser flow passed: displayed OTP -> borrower session -> KYC OTP -> five consents -> fetch -> credit officer verification -> officer approval disabled -> manager approval -> borrower approved/ledger status. No browser page errors; 390px mobile viewport had no horizontal overflow. Desktop and mobile screenshots visually inspected internally.
- PostgreSQL/Docker rebuild must be checked on the target machine; this revision was exercised using SQLite/Uvicorn/Vite locally. New schema uses additive tables only.
- External services are not called. No real SMS, MCP transport/server, bank API, video agent, biometric identity check or funds movement is implemented. Mock CBS is the existing transactional local ledger. Human verification records are simulated officer inputs. MSME classification is synthetic profile metadata, not statutory validation. Orchestration remains sequential with checkpoint reuse; no autonomous planning or cross-case learned memory is claimed.
- Framework deprecation warnings remain (Litestar inferred parameter declarations); they do not fail tests on pinned dependencies.

## Pipecat + Sarvam v0.3 validation

- Full backend suite: 36 passed on SQLite with Pipecat 1.14.0 installed; dependency compatibility check passed. New voice tests exercise the real mock Pipecat worker, role/consent restrictions, active-session approval block, ticket expiry/replay, abort, transcript persistence, manual-verification reset, CAM inclusion, and native Sarvam service construction without network calls.
- Frontend production build and two Vitest tests passed. Chromium completed the guided mock interview, transcript save, note import and entire borrower/officer/manager approval journey with no page errors; mobile overflow check passed.
- No valid Sarvam key was supplied and no live Sarvam request was made. Live audio quality, provider latency, microphone permissions and provider account access require the acceptance checks in docs/VOICE_SETUP.md. This revision does not implement telephone dialing, video calling, biometric verification or full-duplex interruption handling.
- The older tester PDF remains the borrower-journey guide. docs/VOICE_SETUP.md is the v0.3 voice addendum. Docker/PostgreSQL rebuild remains a target-machine check.
