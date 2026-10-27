# MSME Capital: current screen walkthrough

This guide follows the v0.4 business interface. Developer configuration, fixture identifiers and operational limitations are documented in README.md and VOICE_SETUP.md. Screen names in the older tester PDF predate this release.

## Upgrade an existing installation

1. Back up your project and database. Run `docker compose down` from the existing project folder.
2. Replace source files with this release. Keep your existing `.env`, database password, staff tokens and Docker volumes.
3. Run `docker compose up --build -d`, then `docker compose ps`.
4. Open http://localhost:8080 and hard-refresh the browser. Do not run `docker compose down -v` during an upgrade.

## Borrower journey

1. Select **Aster Precision Works** in Business account. Select **Continue to verification**.
2. Copy the displayed one-time access code into **Enter verification code**, then **Verify & continue**.
3. In Your identity, review the applicant details. Select **Get verification code**, enter the displayed identity code, then **Verify identity & continue**.
4. Review Your business and each consent. Continue to loan configuration.
5. Select the loan type, amount and tenure. Describe the intended use of funds. Select **Submit application** once.
6. Review connected records, application status and What happens next. Open **View application** to resume later.
7. If the status is **Action needed**, read the individual policy/evidence gaps. Supply the requested document type and reporting period. If replacing a document, choose the actual existing document to replace. An upload alone does not prove that all gaps are resolved.
8. Respond to any officer clarification with the relevant explanation or evidence. Refresh and check the subsequent assessment; do not assume submission means approval.

## Credit officer review and interview

1. Select **Credit workspace**, enter the analyst token from `.env`, then **Enter underwriting desk**.
2. Search by displayed business/applicant name or case reference. Queue filters apply to the loaded applications; the current register loads up to 100 recent cases.
3. Open the business. Review Documents, Evidence and Analysis. Use evidence references to inspect the original underlying facts.
4. Open **Verification & terms**. Select each evidence graph node to inspect source status, then **Explore evidence** for detail.
5. Choose an interview language and obtain the participant's consent. Select **Start interview**.
6. For a written interview, enter each answer in **Your answer**, then **Submit answer**. For voice, allow microphone access, listen to the prompt, select **Record answer**, speak, then **Stop recording**. Wait for the transcript before submitting.
7. Complete the three questions: applicant name, business activity/customers, and use of funds. Select **Finish and save transcript**.
8. Expand **Saved voice sessions**. Review the transcript. **Copy transcript to officer notes** is optional; correct and assess the notes before saving. Transcript completion does not verify the applicant.
9. Independently confirm identity, business nature and use of funds. Complete the local-market/viability assessment and **Save verification**.
10. Review the proposed amount, tenure and interest. Save changes with a rationale. Any rate deviation requires manager approval. Complete property and survey requirements where applicable.
11. Select **Run analysis**. Review the newly generated CAM and remaining gaps. A saved interview, new evidence or changed terms can invalidate the previous memo.

## Voice configuration and acceptance

Set `VOICE_MODE=sarvam` and `SARVAM_API_KEY` on the server using the existing `.env.example` variable names. Recreate the API container after changing environment values. Keep the key out of frontend code. Consult VOICE_SETUP.md for model, voice and origin settings. Remote microphone access requires HTTPS; localhost supports local testing.

Verify English, Hindi and Tamil speech using your account. Check audible prompts, recognized numbers/names, correction through officer notes, interruption/disconnect behavior, microphone denial, missing/invalid credentials and session cancellation. Inspect `docker compose logs --tail=100 api` for failures without sharing credentials. Provider connectivity, speech accuracy and latency require a live account test.

## Manager approval and tracking

1. As credit officer, confirm **Record approve** remains unavailable.
2. Sign out of the staff session. Sign in using the reviewer/manager token.
3. Open the case, review the current evidence and CAM, and approve any authorized rate exception with a reason. Rerun analysis when required.
4. In **Human review**, enter reviewer comments and record the decision. Open evidence requests, stale analysis, incomplete verification or an active interview must block approval.
5. For an approved application, confirm a single entry in **Sanction register**. Repeating the approval must not create another entry.
6. Return to **Borrower portal**, open **View application**, and confirm the current status and sanctioned terms. Approval messaging must not claim that money has been transferred.

## Visual and regression checks

- Check laptop and narrow mobile layouts, keyboard focus, readable status labels, loading and error states.
- Check login, identity, consent, tracking, queue, verification, voice history, documents, evidence, analysis, CAM, review and audit views for consistent business language.
- Compare displayed amounts, terms, ratios, policy outcomes and evidence references against the underlying case. Presentation changes must not change financial outcomes or permissions.
- Exercise a missing-record case and a low-capacity case; the interface must show actionable gaps and retain approval gates.
- Record each result with case reference, role, steps, expected result, actual result and relevant screenshot. Never include access tokens or API keys in a defect report.
