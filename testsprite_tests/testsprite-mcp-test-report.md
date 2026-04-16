# TestSprite AI Testing Report (MCP) — JobPilot Round 1

Combined backend + frontend Round 1 results for the TestSprite Hackathon Season 2 submission.

---

## 1️⃣ Document Metadata
- **Project Name:** jobpilot
- **Project Path:** /Users/meiguowashington/Desktop/jobpilot
- **Round:** 1
- **Date:** 2026-04-15
- **Prepared by:** TestSprite AI Team
- **Backend test plan:** [testsprite_backend_test_plan.json](./testsprite_backend_test_plan.json) (10 test cases, Flask on localhost:5001)
- **Frontend test plan:** [testsprite_frontend_test_plan.json](./testsprite_frontend_test_plan.json) (6 test cases, Next.js on localhost:3001)
- **PRD source:** [standard_prd.json](./standard_prd.json)

### Environment / run notes
- **Port 5000 was occupied by macOS AirPlay Receiver**, which returned HTTP 403 for every tunneled request in the first backend attempt. Flask was moved to `127.0.0.1:5001` (explicit host bind + `PORT` env var) and the full backend round was re-run against 5001.
- **Port 3000 was already running `newsplatfrom`** (a different Next.js project). The first frontend attempt tested the wrong application — every test observed "a global news dashboard, not a job board". JobPilot's frontend was brought up on port 3001 with `PORT=3001 npm run dev` and the full frontend round was re-run against 3001.
- Both failed early runs are preserved in `testsprite_tests/tmp/raw_report_backend_round1.md` (where applicable) for contrast; the numbers below reflect the corrected runs only.
- **TestSprite API key rotation** was required mid-round (the first API key had expired, surfacing as `AUTH_FAILED: CREATE_API_KEY`). A new key was generated on the TestSprite dashboard and written into `.claude.json > mcpServers > TestSprite > env.API_KEY`.

---

## 2️⃣ Requirement Validation Summary

### Requirement R1 — Service Health & Introspection
**Scope:** Liveness probe and database introspection — the two endpoints Railway and ops depend on.

#### TC001 (backend) — GET /api/health returns service status
- **Status:** ✅ Passed
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/2e35899f-51a9-4799-92e4-6775f1860571/005b8ab7-4428-4e70-abdf-deb8b3e0cf14
- **Analysis:** Health endpoint returned 200 with the expected schema. This is the baseline confirming the tunnel reached Flask on 5001 (vs. the initial AirPlay 403 misroute). No regression.

#### TC002 (backend) — GET /api/debug/tables returns database tables and row counts
- **Status:** ❌ Failed
- **Error:** `AssertionError: 'tables' is not an object/dict`
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/2e35899f-51a9-4799-92e4-6775f1860571/0f381450-0034-4fea-8de5-d4f221265155
- **Analysis:** Response schema mismatch. The test expected `{"tables": {<name>: <count>, ...}}` per the code-summary contract, but the handler in `backend/app.py:84` returns `tables` as a non-dict value (likely a list). Low severity but still a real contract bug — ops scripts consume this endpoint.

---

### Requirement R2 — User Authentication & Profile
**Scope:** Google OAuth sync from the Next.js NextAuth callback into Postgres, plus the current-user profile endpoint. Every authenticated path in JobPilot depends on R2.

#### TC003 (backend) — POST /api/sync-user upserts user record from Google OAuth payload
- **Status:** ❌ Failed
- **Error:** `AssertionError: Expected 200, got 400` (backend body: `{"error":"google_id required"}`)
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/2e35899f-51a9-4799-92e4-6775f1860571/0591c0b2-ba54-40d5-adf7-2f7b0237a1e7
- **Analysis:** **Highest-impact finding of Round 1.** `/api/sync-user` requires a `google_id` field that is not documented in the code-summary contract and not in the payload the test generator builds from a standard OAuth user shape. A single endpoint failure cascades into TC004, TC005, TC008, TC010 — every authenticated backend test. Also an immediate production risk: if the Vercel NextAuth callback does not send `google_id`, real Google sign-ins are silently rejected. Recommended fix: make `google_id` optional server-side and upsert by email.

#### TC004 (backend) — GET /api/me returns authenticated user profile
- **Status:** ❌ Failed (cascade from TC003)
- **Error:** `AssertionError: Sync user failed with status 400`
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/2e35899f-51a9-4799-92e4-6775f1860571/5a443efc-8e9f-4c84-8b5e-22c9d01eee0b
- **Analysis:** Pure cascade. `/api/me` was never actually exercised; the test could not obtain a session.

---

### Requirement R3 — Resume Parsing
**Scope:** PDF/DOCX upload → Claude-extracted skills, degree, direction, experience.

#### TC005 (backend) — POST /api/parse parses uploaded resume and returns structured fields
- **Status:** ❌ Failed (cascade from TC003)
- **Error:** `RuntimeError: Failed to sync user for auth token simulation`
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/2e35899f-51a9-4799-92e4-6775f1860571/d224baf7-ff44-49c1-bf41-b62fe2d65e92
- **Analysis:** Cascade. The resume-parsing pipeline (`parser.py` → Claude) was never reached.

---

### Requirement R4 — Job Search (Core Promise Gate)
**Scope:** The P0 endpoint. Queries the verified job cache and applies the 4-condition Core Promise gate (open, location, direction, identity/degree/visa).

#### TC006 (backend) — POST /api/search returns jobs filtered by Core Promise
- **Status:** ❌ Failed (timeout)
- **Error:** `ReadTimeoutError: HTTPConnectionPool(host='tun.testsprite.com', port=8080): Read timed out. (read timeout=30)`
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/2e35899f-51a9-4799-92e4-6775f1860571/c9fb21ca-3fe6-4a6c-a989-eb08638e5e35
- **Analysis:** Real performance signal. `/api/search` exceeded 30 s. `CLAUDE.md` explicitly warns that Cloudflare cuts single requests at 30 s on Railway. Probable root cause: the handler in `backend/app.py:279` is doing live Greenhouse/Lever verification inside the request path, which it should not — all verification must live in the daily GitHub Actions cron. Fix options: cache-only reads; or stream partial results via SSE. The Core Promise gate's correctness cannot be validated until this test can read a response.

---

### Requirement R5 — Cover Letter Generation
**Scope:** Claude-authored cover letter per matched job. Blocking and SSE variants.

#### TC007 (backend) — POST /api/generate-cls generates cover letter for job
- **Status:** ❌ Failed (timeout)
- **Error:** `ReadTimeoutError: read timeout=30`
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/2e35899f-51a9-4799-92e4-6775f1860571/06f16308-f155-4322-a926-41d414dec378
- **Analysis:** Same class as TC006. The synchronous Claude completion in `backend/app.py:454` takes longer than 30 s for realistic resumes. The streaming endpoint `/api/generate-cls/stream` already exists for exactly this reason — the frontend should route all cover-letter generation through streaming and the blocking variant should be deprecated.

#### TC008 (backend) — GET /api/generate-cls/stream streams cover letter generation tokens
- **Status:** ❌ Failed (cascade from TC003)
- **Error:** `AssertionError: Sync user failed: {"error":"google_id required"}`
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/2e35899f-51a9-4799-92e4-6775f1860571/16bda557-9504-495c-a7d5-41a4878a6adf
- **Analysis:** Cascade. Confirms the exact error string `google_id required` a second time, which pins the R2 root cause. The SSE stream was not opened.

---

### Requirement R6 — Demo / Public Verification (Backend + Frontend)
**Scope:** The public "Verify Job URL" widget on the landing page — the piece of JobPilot a visitor can try without signing in. Exercised at both layers.

#### TC009 (backend) — GET /api/demo-verify verifies job URL open status
- **Status:** ❌ Failed
- **Error:** `AssertionError: 'verified_open' key missing in response`
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/2e35899f-51a9-4799-92e4-6775f1860571/f0747575-3ef0-495d-8eba-0f2e57fb0f93
- **Analysis:** Real contract bug. `backend/app.py:110` (handler) or `backend/verifier.py` (implementation) has a code path that returns a response shape missing the promised `verified_open: bool` field. Probably the unreachable-URL / parser-short-circuit branch. No auth dependency — this is an independent fix.

#### TC004 (frontend) — Submit a valid job URL in the demo verifier
- **Status:** ✅ Passed
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/3091907b-8a62-4b6a-bbdd-bff6ce501730/88ffe0fe-3453-4f6b-8179-587032adc8cf
- **Analysis:** End-to-end happy path works: the landing page widget accepts a valid Greenhouse/Lever URL, submits to `/api/demo-verify`, and renders a result. This is the only public surface a visitor can test without credentials — and it works.

#### TC006 (frontend) — Reject malformed URLs in the demo verifier
- **Status:** ✅ Passed
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/3091907b-8a62-4b6a-bbdd-bff6ce501730/f7627652-dc04-42f9-841c-f4a21c7468a8
- **Analysis:** Frontend correctly rejects / surfaces an error for malformed URL input. Input validation on the landing page is intact.

> **Cross-layer finding:** frontend TC004 passes (valid URL) but backend TC009 fails (`verified_open` missing). This strongly suggests `verified_open` is only populated on the happy path. When the tested URL is reachable and parseable (frontend Round 1 used a real greenhouse URL), the response looks correct; when the backend test generator used a stubbed or unreachable URL, the error branch dropped `verified_open`. **Fix:** guarantee the field is set on every branch, including errors, then both tests pass.

---

### Requirement R7 — Stripe Payments
**Scope:** Stripe Checkout session creation and webhook upgrade flow.

#### TC010 (backend) — POST /api/stripe/create-checkout creates Stripe Checkout session
- **Status:** ❌ Failed (cascade from TC003)
- **Error:** `AssertionError: Failed to sync user, status code 400`
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/2e35899f-51a9-4799-92e4-6775f1860571/0987238c-09a4-43d6-a8a2-902d0f5806c4
- **Analysis:** Cascade. Stripe wiring and price-id lookup were not exercised.

---

### Requirement R8 — Authenticated Frontend Flows (Onboarding / Dashboard)
**Scope:** Everything behind the Google sign-in wall — onboarding, resume upload UI, job list, filter controls, cover letter UI.

#### TC001 (frontend) — Complete onboarding with profile criteria and a PDF/DOCX resume
- **Status:** 🚫 BLOCKED (environmental, not a bug)
- **Error:** `TEST BLOCKED — /login returns 404; no form fields`
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/3091907b-8a62-4b6a-bbdd-bff6ce501730/b37eaa29-5ab0-4dd9-8491-80a8673e0b85
- **Analysis:** TestSprite's test generator assumed a conventional `/login` route, but JobPilot uses NextAuth's default sign-in path (`/api/auth/signin`) which redirects straight to Google OAuth. The automation cannot complete a real Google OAuth flow without stored credentials. **Not a bug** — a limitation of automated testing against OAuth-gated flows. Round 2 will ship either a test-mode session bypass or a seeded JWT that mints a session without going through Google.

#### TC002 (frontend) — Apply region and degree filters to refine Core Promise job results
- **Status:** 🚫 BLOCKED (same environmental cause as TC001)
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/3091907b-8a62-4b6a-bbdd-bff6ce501730/adb6a063-fc87-4c56-8f81-89355da47ddb
- **Analysis:** Same block. The dashboard is behind OAuth.

#### TC003 (frontend) — Update direction or degree criteria and refresh results
- **Status:** 🚫 BLOCKED (same environmental cause as TC001)
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/3091907b-8a62-4b6a-bbdd-bff6ce501730/73a36ebd-58de-4437-93c5-375b37be3120
- **Analysis:** Same block.

#### TC005 (frontend) — Reject non-PDF/DOCX resume uploads during onboarding
- **Status:** 🚫 BLOCKED (hit Google OAuth, no credentials)
- **Error:** `Clicking 'Try free — no card needed' redirected to the Google Accounts sign-in page`
- **Visualization:** https://www.testsprite.com/dashboard/mcp/tests/3091907b-8a62-4b6a-bbdd-bff6ce501730/a52bc121-b56c-4af4-a307-f8499628f711
- **Analysis:** Interesting asymmetry — this test figured out that the CTA leads to Google OAuth rather than a local `/login`. Confirms the blocker is OAuth itself, not a misrouted path.

---

## 3️⃣ Coverage & Matching Metrics

### Combined
- **Total tests:** 16 (10 backend + 6 frontend)
- **Passed:** 3 (TC001 backend, TC004 & TC006 frontend)
- **Real-bug failures:** 3 (TC002 backend shape, TC003 backend `google_id`, TC009 backend `verified_open`)
- **Performance failures:** 2 (TC006 search, TC007 cover letter — both 30 s tunnel timeout)
- **Cascade failures (blocked by TC003 backend):** 4 (TC004, TC005, TC008, TC010 backend)
- **Environmental blocks (Google OAuth):** 4 (TC001, TC002, TC003, TC005 frontend)

### By requirement
| Requirement | Total | ✅ Passed | ❌ Failed | 🚫 Blocked | Notes |
|---|---|---|---|---|---|
| R1 — Service Health & Introspection | 2 | 1 | 1 | 0 | TC002 response shape mismatch |
| R2 — User Auth & Profile (backend) | 2 | 0 | 2 | 0 | **Root cause: unblocks 4 more tests** |
| R3 — Resume Parsing | 1 | 0 | 1 | 0 | Cascade from R2 |
| R4 — Job Search (Core Promise) | 1 | 0 | 1 | 0 | 30 s tunnel timeout (perf, not correctness) |
| R5 — Cover Letter Generation | 2 | 0 | 2 | 0 | TC007 timeout, TC008 cascade |
| R6 — Demo / Public Verification | 3 | 2 | 1 | 0 | Cross-layer: frontend happy path works, backend error branch drops `verified_open` |
| R7 — Stripe Payments | 1 | 0 | 1 | 0 | Cascade from R2 |
| R8 — Authenticated Frontend Flows | 4 | 0 | 0 | 4 | Environmental (Google OAuth) |
| **Total** | **16** | **3** | **9** | **4** | |

Raw pass rate: **3 / 16 = 18.8 %**.
Effective pass rate (excluding environmental blocks): **3 / 12 = 25 %**.

---

## 4️⃣ Key Gaps / Risks

### P0 — Ship-blockers, fix before Round 2
1. **`/api/sync-user` requires undocumented `google_id` field.** Single highest-leverage fix of Round 1 — unblocks 4 cascaded backend tests AND fixes a silent production failure mode. Decision: make `google_id` optional server-side and upsert by email. File: `backend/app.py:180`.
2. **`/api/demo-verify` response drops `verified_open` on the error / unreachable-URL branch.** Independent contract bug on a public endpoint; frontend happy-path test already passes, so the fix is guaranteeing the field on every branch. Files: `backend/app.py:110`, `backend/verifier.py`.

### P1 — Architecture / Cloudflare 30 s ceiling
3. **`/api/search` exceeds 30 s.** Matches the documented Cloudflare cutoff. Must be cache-only at request time; all live verification belongs in the daily GitHub Actions cron.
4. **`/api/generate-cls` blocking variant is unusable for realistic resumes.** Deprecate in favor of the existing `/api/generate-cls/stream`.

### P2 — Contract & hygiene
5. **`/api/debug/tables` response shape mismatch** (non-dict `tables`). Trivial fix.
6. **`/api/sync-user` trusts the request-body email without server-side OAuth verification.** Pre-existing, surfaced by static analysis — server should verify the Google JWT before upsert. Not exercised by Round 1 tests; flagged for Round 2.
7. **`/api/demo-verify` accepts arbitrary URLs with no allowlist** — SSRF surface on a public endpoint. Add a host allowlist (greenhouse.io, lever.co, known ATS domains) alongside the P0 fix.

### P3 — Test-harness gaps (to unblock Round 2 coverage)
8. **R8 (authenticated frontend flows) is unreachable by automated testing as long as the only sign-in path is Google OAuth.** Two options: (a) ship a test-mode env flag that mints a NextAuth JWT from a seed email without redirecting to Google; (b) provide TestSprite with a dedicated Google test account. (a) is cleaner and hackathon-safe. Without this, TC001/002/003/005 frontend cannot be re-run meaningfully.
9. **Test generator assumed `/login`.** After (8) is in place, update `code_summary.yaml` to declare the exact sign-in URL so the generator stops guessing.

### Infra / process notes (do not repeat in Round 2)
- **macOS port 5000 collision with AirPlay Receiver** broke the first backend attempt. Flask now binds `127.0.0.1` explicitly and reads `PORT` env (default 5001). Do not return to port 5000 on developer macOS.
- **Port 3000 was already occupied by a different project** (`newsplatfrom`). Always verify what is actually serving the bootstrapped port before kicking off TestSprite — the first frontend round was wasted measuring the wrong app. Going forward, run JobPilot frontend on 3001 or a pinned-high port.
- **TestSprite API keys need rotation** when the `AUTH_FAILED: CREATE_API_KEY` error surfaces mid-round. Key lives in `~/.claude.json > mcpServers > TestSprite > env.API_KEY`; restart Claude Code after rotation so the MCP server picks up the new env.

---
