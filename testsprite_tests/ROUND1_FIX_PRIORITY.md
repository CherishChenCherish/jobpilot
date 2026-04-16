# Round 1 → Round 2 Fix Priority

Generated from TestSprite Round 1 backend run (2026-04-14).

## Quick math
- 1/10 passed
- Fix **1 bug** (sync-user google_id) → unblock 5 tests
- Fix **3 bugs** (+ debug/tables shape + demo-verify missing field) → unblock 7 tests
- Fix **5 bugs** (+ search timeout + cover-letter timeout) → expect 10/10 in Round 2

## P0 — do first (unblocks everything else)

### Bug 1: /api/sync-user requires undocumented `google_id`
- **File:** backend/app.py:180
- **Symptom:** POST with `{email, name, image}` returns `400 {"error":"google_id required"}`
- **Blast radius:** TC003, TC004, TC005, TC008, TC010 (5 tests)
- **Production risk:** HIGH — if the NextAuth callback on Vercel does not include google_id, real Google sign-ins silently fail. Verify against production before fixing.
- **Fix options:**
  - (A) Accept sign-in when email is present; treat google_id as optional / upsert by email.
  - (B) Keep google_id required but update NextAuth callback on frontend/ to send `profile.sub` as `google_id`. Also update code_summary.yaml and rerun Round 1 test plan generation.
- **Recommendation:** (A) — email is already unique, google_id buys nothing we do not already get from the OAuth flow, and making it required has created a silent-failure surface.

### Bug 2: /api/demo-verify response missing `verified_open` key
- **File:** backend/app.py:110, backend/verifier.py
- **Symptom:** Response shape lacks the `verified_open: bool` field that the PRD and landing page both depend on.
- **Blast radius:** TC009 (1 test) + landing page demo widget in production.
- **Fix:** guarantee the handler returns `{verified_open: bool, confidence: str}` on every code path. Probably a missed branch in verifier.py where the URL is unreachable or the response parser returns early.

## P1 — performance / Cloudflare 30s ceiling

### Bug 3: /api/search timeouts past 30 seconds
- **File:** backend/app.py:279, backend/searcher.py
- **Symptom:** Tunnel read timeout at 30s. Matches the Cloudflare single-request cutoff that CLAUDE.md already warns about.
- **Root cause to verify:** is search doing live Greenhouse/Lever verification inside the request path? It should be cache-only.
- **Fix:** make /api/search strictly read from the jobs table; move ALL verification to the daily GitHub Actions cron. If some verification must be at request time, return partial results via SSE.
- **Blast radius:** TC006 in test, real users in production on cold regions.

### Bug 4: /api/generate-cls blocking call unusable for realistic inputs
- **File:** backend/app.py:454
- **Symptom:** Claude completion >30s on realistic resumes.
- **Fix:** deprecate the blocking endpoint, route frontend entirely through `/api/generate-cls/stream`. Or add a very short timeout on the blocking variant and return 503 with a hint to switch to streaming.

## P2 — contract & hygiene

### Bug 5: /api/debug/tables response shape mismatch
- **File:** backend/app.py:84
- **Symptom:** `tables` returned as non-dict (probably a list).
- **Fix:** return `{"tables": {name: row_count, ...}}` per the documented shape. Trivial edit.

### Pre-existing risks surfaced during static analysis (not yet tested)
- `/api/sync-user` trusts request-body email — server should verify Google JWT before upsert.
- `/api/demo-verify` accepts arbitrary URL — SSRF risk. Add host allowlist (greenhouse.io, lever.co, known ATS domains).
- `/api/admin/*` uses a shared bearer — acceptable for now since access is scoped to GitHub Actions, but worth documenting.
- `db.create_all()` must run on import for gunicorn — any refactor that moves it inside `if __name__ == "__main__"` silently breaks prod.

## Round 2 plan
1. Fix Bugs 1, 2, 5 (P0 + trivial contract fix) — ~30 min.
2. Fix Bug 3 — convert /api/search to cache-only — ~60 min, needs verification against prod.
3. Fix Bug 4 — route frontend through /api/generate-cls/stream only — ~30 min.
4. Rotate TestSprite API key. Rerun backend Round 2 — target 10/10.
5. Bootstrap frontend TestSprite (localPort 3000). Run Round 1 for frontend.
6. Update HACKATHON.md Round 1 notes and post progress in Discord.
