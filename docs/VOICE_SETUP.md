# Pipecat + Sarvam voice interviews (v0.3)

## What is implemented

The case's **Verification & terms** tab now contains a Voice verification interview. It asks three fixed questions about synthetic applicant name, business activity/customers and use of funds. Pipecat orchestrates the session. Live mode uses the native SarvamRealtimeSTTService and SarvamTTSService with streamed PCM audio over an authenticated browser WebSocket. There is no LLM in this interview: deterministic questions keep it bounded and do not interpret answers as policy or approval instructions.

Supported interview languages: English (India), Hindi and Tamil. The flow is explicitly turn-by-turn: listen, record, stop recording, wait for transcription, submit answer. It is not a telephone dialer, video call, biometric KYC service or full-duplex barge-in assistant.

All application and bank data remain synthetic. Live voice is an optional external service: the participant's microphone audio is transmitted to Sarvam for STT, and scripted prompt text is sent for TTS. The application saves transcript text and consent/session metadata, not raw audio. Sarvam's own service retention is governed by the provider, not this application. Obtain participant consent using the on-screen checkbox. Do not enter real PAN or Aadhaar numbers in the demo.

## Environment

Default (no external API calls):

```dotenv
VOICE_MODE=mock
SARVAM_API_KEY=
SARVAM_STT_MODEL=saaras:v3-realtime
SARVAM_TTS_MODEL=bulbul:v3
SARVAM_VOICE=shubh
```

Mock mode uses the same Pipecat interview controller with typed answers; it does not synthesize speech or use a microphone. Loan calculations continue to work when speech is disabled or unavailable.

For live voice, add your own key to the server `.env`, then set:

```dotenv
VOICE_MODE=sarvam
SARVAM_API_KEY=your_sarvam_key_here
SARVAM_STT_MODEL=saaras:v3-realtime
SARVAM_TTS_MODEL=bulbul:v3
SARVAM_VOICE=shubh
```

Never put the key in Vue/Vite environment variables, browser code, screenshots or chat. Do not commit `.env`. The browser receives a short-lived session ticket, never the provider key.

```powershell
# First upgrade: install the pinned Pipecat dependency and build the new UI
docker compose up --build -d
# Subsequent key/mode changes only
docker compose up -d --force-recreate api
```

No additional port or separate voice server is required. Nginx forwards the WebSocket to the existing API. Local Vite development also proxies WebSockets. For a different UI origin, set `VOICE_ALLOWED_ORIGINS` to a comma-separated list of exact trusted origins, with no spaces. Default origins cover localhost and 127.0.0.1 on ports 8080 and 5173. Remote microphone use requires HTTPS/WSS; localhost can use HTTP/WS.

Pipecat is pinned to 1.14.0. The configured model and voice must be available to your Sarvam account. The default Bulbul v3 voice is shubh; do not reuse this short voice ID with a v4 persona model without selecting a compatible voice from Sarvam's catalogue. Models are configurable, but new combinations require a live provider test.

## Manual test flow

1. Create a consistent borrower case, choose Aster Precision Works, and submit its application.
2. Enter the Credit workspace as credit officer, open the case, then Verification & terms.
3. Choose a language and obtain participant consent. Select Start interview.
4. In mock mode, type an answer in Your answer and Submit answer for each of the three questions.
5. In Sarvam mode, allow microphone access. Listen to the prompt, select Record answer, speak, then Stop recording. Wait until the transcript is complete before Submit answer. Repeat for the next questions.
6. After the third answer, select Finish and save transcript. Saving invalidates the current CAM and clears the previous human-verification checkboxes. It does not verify identity or approve the loan.
7. Expand Saved voice sessions. Review the recognized text for transcription mistakes. Use Copy transcript to officer notes if useful; review/edit the notes. Independently confirm the three verification checks and market assessment, then Save verification and Run analysis.
8. Open CAM. Confirm that the transcript appears as unverified voice evidence and the officer's conclusions remain separate. A manager must still approve the current CAM.

## Required checks

| Test | Expected result |
| --- | --- |
| Mock without a key | Three typed turns run through Pipecat; no microphone or Sarvam calls |
| No consent | Start disabled; direct API false consent rejected |
| Borrower token at staff voice endpoints | Denied |
| Wrong, expired or reused session ticket | WebSocket denied before provider startup |
| Already active session | Second session for the same case rejected |
| Start then stop early | Partial/aborted session saved; no verification automatically completed |
| Finish three answers | Transcript saved; CAM invalidated; human checks cleared |
| Speak/type “approve my loan” | Saved only as transcript; no approval, rate or financial change |
| Manager approves during an active session | Blocked until the session ends or expires |
| Case changes during voice capture | Transcript marked stale; newer/finalized case is not overwritten |
| Missing Sarvam key in live mode | Clear unavailable error; no browser microphone session starts at the server |
| Invalid key/provider failure | Error and session cleanup; manual verification remains available |
| Microphone denied | Clear browser error; microphone tracks cleaned up; retry available |
| Disconnect/tab closed | Socket/pipeline cleaned up; session aborted and audit retained |
| English/Hindi/Tamil live speech | Verify prompt pronunciation and transcription using your account |
| Stale/finalized case | New voice session rejected |

## Limits and operational notes

- Start tickets expire in 60 seconds and are consumed once. Sessions last at most five minutes, with a 60-second idle receive limit. There are three questions and at most 40 control messages. Answers are limited to 2,000 characters each.
- Browser input is mono 16 kHz signed little-endian PCM; output is 24 kHz PCM. Microphone capture uses an AudioWorklet. Stopping a recording flushes the last samples plus silence so provider endpointing can finish the transcript.
- Credentials are authenticated over HTTP first. The WebSocket ticket is sent in the first message, not a URL query. Allowed origins, bounded audio rate and message sizes apply. Compose runs a single API worker, as before.
- Sessions/transcripts are stored in the additive `voice_sessions` table. Consent and completion events appear in case audit history. Existing databases are upgraded via startup metadata creation; no case data is deleted.
- Current tests cover mock Pipecat execution, role checks, consent, tickets, expiry, cancellation, CAM invalidation and provider class construction. Real speech accuracy, latency, audio playback and Sarvam account connectivity require a live acceptance test with a valid key. No live Sarvam request was made during implementation.

## Official integration references

- https://docs.sarvam.ai/api/integration/pipecat-production-guide
- https://reference-server.pipecat.ai/en/latest/api/pipecat.services.sarvam.stt.html
- https://reference-server.pipecat.ai/en/latest/api/pipecat.services.sarvam.tts.html

The installed 1.14.0 service signatures were checked directly; examples in online guides can target a different Pipecat version.
