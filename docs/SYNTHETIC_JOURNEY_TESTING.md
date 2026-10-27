# Synthetic journey v0.2 — manual tester guide

## Before testing

Ask the owner for the UI URL and the credit officer / branch manager tokens. The default UI is http://localhost:8080. Use only synthetic identities. Record application ID, profile ID, role, revision, expected result, actual result and evidence for each test. The previous upload-first manual guide describes legacy cases, not the default borrower journey.

## First successful application

1. Choose SYN-0001 on the borrower landing page. Get demo OTP, enter the displayed code and verify.
2. The wizard displays the profile name, PAN, DOB and mobile. Request a separate KYC OTP and verify it.
3. Review business, Udyam, GST and sector. Select all five consent checkboxes.
4. Choose Term loan, INR 1,000,000, 36 months, and enter a synthetic equipment purpose.
5. Submit & fetch synthetic data. Wait for analysis. Expect awaiting_review; human verification is still incomplete. Awaiting review is not approved.
6. Credit team portal -> officer token -> search DEMOPAN0001 -> open matching case -> Verification & terms.
7. Tick identity, business and purpose verification. Enter interview notes and local market/viability assessment. Save, then Run analysis.
8. Open Analysis. At default 14% rate expect monthly operating cash INR 220,000, existing monthly debt INR 20,000, EMI INR 34,177.63 (UI may round), DSCR about 4.06. Inspect each policy result and citations.
9. Open CAM; verify current revision, sources, human inputs and terms. Print/save PDF if needed.
10. Sign out of staff and enter manager token. Open the case -> Human review -> approve with comments.
11. Mock ledger should contain exactly one row for this application. Borrower portal -> Track application -> Refresh status should show approved and mock ledger posted.

## Repeatable test cases

| ID | Action | Expected result |
| --- | --- | --- |
| J01 | Wrong login OTP | Error; no borrower session |
| J02 | Reuse consumed OTP | Rejected |
| J03 | Wait over 5 minutes before OTP verification | Expired OTP rejected; resend needed |
| J04 | Five wrong attempts, then correct OTP | Challenge remains blocked |
| J05 | Request more than five OTPs for one mobile in one minute | Rate limited; retry after one minute |
| J06 | Change PAN/DOB from selected profile before submission | Submission rejected, no identity mismatch case created |
| J07 | Leave one consent unchecked | Cannot continue; direct API submission also rejected |
| J08 | Complete the successful flow above | One approved case and one mock ledger row |
| J09 | Officer attempts final approve/reject | Disabled UI and server 403 |
| J10 | Manager attempts approval before interview | Blocked by HUMAN_VERIFICATION |
| J11 | Change amount or tenure | Revision increases; old CAM cannot approve; financials must rerun |
| J12 | Change rate 14 to 13.5 | Pending manager rate exception; recalculated EMI lower; approval blocked |
| J13 | Officer attempts rate exception approval | Server 403 |
| J14 | Manager approves rate exception | Rate approved, CAM invalidated; rerun then inspect before final approval |
| J15 | Manager rejects exception | RATE_EXCEPTION remains blocking; officer must revise terms |
| J16 | Rate below 13 or above 19 with default base 14 | Rejected by demo hard bounds |
| J17 | Change terms after approved exception | New rate decision required for a non-base rate |
| J18 | Choose LAP/construction; omit survey/title/margin | PROPERTY gate blocks final approval |
| J19 | LAP with value 2,000,000, margin 25%, loan 1,000,000; add surveyor/report/title | PROPERTY passes after verification and analysis |
| J20 | LAP amount exceeds value minus margin | PROPERTY remains blocked |
| J21 | SYN-0002 | Bureau 650, BUREAU check blocks approval; no automatic rejection |
| J22 | SYN-0003 | GST requires_action; needs_evidence with specific missing GST request |
| J23 | Upload legacy 01_consistent/gst.json as missing GST for SYN-0003 | GST gap resolves after automatic rerun; human verification still required |
| J24 | SYN-0004 | Insufficient repayment capacity; DSCR fails |
| J25 | SYN-0005 | GST reconciliation conflict; final approval blocked |
| J26 | SYN-0006 | Balance-drop observation cites source transactions; investigation required |
| J27 | Officer requests exact missing evidence | Borrower sees request; current CAM invalidated |
| J28 | Borrower submits clarification text | Audit records response; request does not silently resolve |
| J29 | Staff reviews evidence, resolves request and reruns | Request resolved; new CAM includes resolution |
| J30 | Retry provider fetch on editable case | Existing active evidence not duplicated or overwritten |
| J31 | Upload identical file again | Duplicate rejected |
| J32 | Replace document explicitly | Old version retained; prior CAM stale; new analysis uses replacement |
| J33 | Log in as another borrower | Only own cases appear; cross-case API requests return 404 |
| J34 | Repeat final approval | Rejected; ledger remains one row |
| J35 | Edit/fetch/upload after approval or rejection | Blocked; final case frozen |
| J36 | Reload or restart containers | Profiles/cases/approvals retained; valid session can be reused |
| J37 | Borrower sign out; reuse old session token | Session rejected |
| J38 | Invalid staff token | Staff login denied |
| J39 | Narrow mobile viewport | Forms and buttons usable; no page-wide horizontal overflow |
| J40 | Print current CAM | Financials, source references, human inputs and current terms readable |

## When a case still needs evidence

Read the exact case Overview request, then Documents validation and Analysis. A file existing does not mean it is readable, complete, matched to the borrower or correct for the reporting period. Use explicit replacement for corrections. For new profiles, never upload the legacy Asha KYC to a different synthetic owner. A credit officer's request stays open until staff review and resolve it. Verification, rate or property gates can block approval even after the document gap clears.

## Limits and defect reporting

Calls, OTP delivery, Aadhaar/DigiLocker, bureau and bank fetches are simulations. The evidence graph shows recorded sources and gates, not an AI confidence score. MSME category is fixture metadata, not a statutory classification engine. No deployed bank MCP server, external API, learned credit model, speech/video agent or real disbursement is included. The underlying orchestrator remains bounded and sequential with persisted checkpoints; an evidence replacement reruns extraction and downstream nodes. Loan-term changes rerun cash flow and downstream; human review changes regenerate CAM.

Report: test ID, build/version, browser, role (no token), profile, application ID, revision, steps, expected/actual, screenshot, API error and timestamp. Redact all tokens. Pass only when expected results match; blocked setup is Blocked, not Pass. Critical failures include cross-borrower data access, officer approval, approval with unresolved gates, stale CAM sanction, or duplicate ledger postings.
