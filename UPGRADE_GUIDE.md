# MSME Capital — India experience update

## Install into the existing Docker project

Copy this package's source into your existing project. Preserve your `.env`, database volumes and uploaded files. Do not run `docker compose down -v`.

```powershell
docker compose up --build -d
docker compose ps
```

Open http://localhost:8080 and press Ctrl+F5. The landing page is now the entry point. Select Sign in for the borrower portal; Credit team sign in is at the bottom of the landing page.

## Bank-holding removal

Removed bank-account entry, IFSC and last-four-digit validation, account cards, statement-to-account linking and ownership-review controls/API. Bank statements, cash-flow charts and repayment analysis remain. Existing stored records and audit history are preserved; no database reset is required.

## What changed

- Ink (#151c28), violet (#5f2cff) and bright green (#02f576) visual palette inspired by Virtusa's current website. No Virtusa affiliation or logo is implied.
- Landing page, visual journey, explanatory cards, and separate borrower/staff entry points.
- Indian applicant names, business names and locations for new profiles; legacy generated profile names migrate at startup. Historical application evidence remains unchanged.
- Raw JSON panels replaced with labelled details. Monthly receipts and expenses use a bar chart with an exact-value table. Customer upload controls accept PDFs; internal fixture/API formats remain unchanged.
- Borrower interview includes a speaking visual assistant, microphone recording and optional camera preview. Staff review saved transcripts and independently verify the case.
- Camera preview remains local: no video is transmitted or recorded. This is not video KYC or a human video call. The interview remains guided and turn-based, not a continuous interruptible conversational agent.

## Voice test

Keep your existing Sarvam key in `.env` and use `VOICE_MODE=sarvam`. Rebuild/recreate the API after configuration changes. The previous min_buffer_size fix (30) is retained.

1. Sign in as a borrower, create an application.
2. Submit and open View application.
3. Find Meet your application assistant. Select English (India), Hindi or Tamil.
4. Consent, then Start interview. Listen to each prompt, Record answer, Stop recording, review the transcription and Submit answer.
5. Optionally turn the camera on/off. A denied camera permission must not prevent an audio interview.
6. After three answers choose Finish and save transcript. Camera/microphone tracks close when the session ends or the component is unmounted.
7. As credit officer, open Verification & terms. Review the transcript, copy notes if useful, complete independent checks and save verification. Run analysis before manager approval.

Live audio requires localhost or HTTPS, browser permission and valid Sarvam configuration. Written interview mode is retained when VOICE_MODE=mock. Bank statement retrieval and analysis remain unchanged.

## Validation and limits

Frontend production build and two frontend unit tests passed. The backend journey and voice tests validate applications without bank-holding details. Borrower ownership, consent, stale revisions, duplicate sessions are covered. The landing page was visually inspected in the browser. The preview environment could not connect its frontend proxy to the separate API process, so the full browser journey and live microphone/camera/Sarvam session were not validated here.

This update provides production-style UX, not a production banking deployment. OTP delivery, bank/tax/bureau retrieval and sanction posting retain their internal test integrations. Real identity verification, bank integrations, production authentication, deployment hardening and operational controls require separate implementation before live customer use. Arbitrary bank PDF layouts still need supported extraction/mapping; the UI update does not add universal OCR.
