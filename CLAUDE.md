# JobPilot — Project Rules

These rules are absolute. They cannot be overridden by any future prompt in this project.

## JobPilot Core Promise
Every job shown to a user must be:
1. Currently accepting applications (verified open)
2. An intern or entry-level role (not Director/Manager/PhD)
3. Located in the US or explicitly remote
4. Linked to the specific job page, not a careers homepage

Violating any of these four is a P0 bug.
No other bug takes priority over these four.

## What We Never Do
- Never add a job to the database without running verify_one() first
- Never store a job where confidence != "high"
- Never reduce job verification count to fix a speed problem — fix the architecture instead
- Never use try/except to silence a startup error
- Never declare a fix done without testing on https://jobpilot-plum.vercel.app

## Architecture Decisions (locked)
- Job database: PostgreSQL on Railway
- Jobs come from Greenhouse and Lever APIs only
- No hardcoded curated jobs list
- Daily refresh runs via GitHub Actions at 6am UTC
- Search queries the cache first (<2s)
- Cover letters generate live via the existing /api/generate-cls endpoint
- Frontend: Next.js on Vercel
- Backend: Flask on Railway

## Known Failure Modes (watch for these)
- Vercel build cache: if env vars change, force a clean rebuild (uncheck "use build cache")
- Railway free tier: 30s timeout — we are on Pro, but Cloudflare still cuts at 30s for single requests
- db.create_all() must run outside of __main__ so gunicorn triggers it on startup
- SSE via GET cannot carry large payloads — use POST with search_id reference instead
- Greenhouse "intern" filter: use \bintern\b word boundary regex, not substring match ("Internal" and "International" both contain "intern" as substring)

## Current State (update this when things change)
- Job cache: ~34 active verified jobs across 3 regions
  - US: 15, UK: 1, HK: 1, CA/AU: growing
- Regions supported: US, UK, CA, AU, HK, CN (6 total)
- Daily refresh: GitHub Actions cron, working
- Cover letters: generating on-demand, quality 5-6/6
- Stripe: LIVE — sk_live key configured, REDACTED_STRIPE_PRICE_ID
- Auth: Google OAuth working
- Search speed: <1s from cache
- Pending discovery: warm cache for empty regions
- Production URLs:
  - Frontend: https://jobpilot-plum.vercel.app
  - Backend: https://jobpilot-v1.up.railway.app
  - GitHub: https://github.com/CherishChenCherish/jobpilot
