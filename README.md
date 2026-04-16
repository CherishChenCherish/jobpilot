# JobPilot

**AI-powered job search for international students.** Upload your resume, get verified open positions, and auto-generated cover letters — built for F-1 students who need visa sponsorship.

**Live:** [jobpilot-plum.vercel.app](https://jobpilot-plum.vercel.app)

---

## The Problem

International students waste hours applying to jobs that are already closed or don't sponsor visas. Job boards don't verify posting status, and "sponsorship available" is rarely stated explicitly.

## What JobPilot Does

1. **Parse** — Upload your resume. AI extracts skills, experience, and degree level
2. **Search** — Queries Greenhouse + Lever APIs across 6 regions (US, UK, CA, AU, HK, CN)
3. **Verify** — Every job is checked via API calls to confirm it's still open (not just scraped HTML)
4. **Filter** — Core Promise gate ensures every result matches your location, field, degree, and visa status
5. **Generate** — One-click cover letters tailored to each job via Claude AI
6. **Export** — Download a styled 4-sheet Excel with jobs, cover letters, and match analysis

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | Flask (Python), SQLAlchemy, PostgreSQL |
| AI | Claude API (resume parsing + cover letter generation) |
| Web Discovery | Scrapling (preferred) with requests+BS4 fallback |
| Auth | Google OAuth via NextAuth.js |
| Payments | Stripe (subscription billing) |
| Deploy | Vercel (frontend) + Railway (backend) |
| CI | GitHub Actions (daily job refresh at 6am UTC) |

## Architecture

```
User uploads resume
       |
   [parser.py] — Claude AI extracts structured profile
       |
   [searcher.py] — Queries Greenhouse + Lever APIs
       |
   [verifier.py] — API-level verification (not HTML scraping)
       |
   [promise.py] — Core Promise gate (open + location + field + identity)
       |
   [generator.py] — Claude AI writes tailored cover letters
       |
   Dashboard — verified jobs with one-click apply + CL download
```

## Key Design Decisions

- **API verification over HTML scraping** — Greenhouse and Lever have public APIs. We check job status at the API level for high-confidence results instead of parsing fragile HTML
- **Scrapling for web discovery** — DuckDuckGo-based job discovery prefers Scrapling for anti-bot fingerprinting and faster parsing, with automatic fallback to requests+BeautifulSoup if Scrapling is unavailable
- **Core Promise as a hard gate** — Every job must pass 4 checks (open, location, direction, identity) in `promise.py` before reaching any user. This is enforced as the final filter, not a soft ranking signal
- **Visa policy: permissive by default** — Most top companies sponsor F-1 OPT/CPT but don't state it. We only block jobs with explicit "no sponsorship" language. Unspecified = show
- **Degree hierarchy** — PhD users see all jobs. MS users see MS+BS. BS users see BS only. Enforced at both storage and search time

## Testing

### Unit Tests

```bash
cd backend
python -m pytest -v       # 56 tests across 5 modules
```

```
backend/test_parser.py     # Resume parsing edge cases
backend/test_searcher.py   # Search API + deduplication
backend/test_verifier.py   # Job verification (mocked + live)
backend/test_promise.py    # Core Promise gate (37 scenarios)
backend/test_generator.py  # Cover letter quality checks
```

### TestSprite Automated Testing (Hackathon Season 2)

TestSprite auto-generated **16 tests** (10 backend API + 6 frontend UI) with zero manual test authoring, testing across the multi-service architecture (Vercel frontend → Railway backend → Greenhouse/Lever APIs).

**3-round progression:**

| Round | Pass Rate | What Happened |
|-------|-----------|---------------|
| Round 1 | 1/10 backend, 2/6 frontend | **5 real bugs found** — including a security vulnerability where `/api/me` returned user data without authentication |
| Round 2 | 5/10 backend | Fixed 3 critical bugs, **400% pass rate improvement** |
| Round 3 | 5/10 backend | Security vulnerability closed; remaining failures are test-environment data gaps |

**Most impactful findings:**
- **Security:** `/api/me` leaked full user data to unauthenticated requests — in production, with real user emails
- **Cross-layer contract gap:** Frontend demo-verify test passed (happy path), while backend test for the same endpoint failed (error branch dropped `verified_open` field). Same feature, two layers, contradictory behavior
- **Silent OAuth rejection:** `/api/sync-user` required an undocumented `google_id` field, silently rejecting email-only payloads
- **Performance:** Search and cover letter endpoints exceeded Cloudflare's 30-second timeout ceiling

```
testsprite_tests/                          # All auto-generated test artifacts
├── TC001-TC010_*.py                       # Backend API test cases
├── TC001-TC006_*.py                       # Frontend UI test cases
├── testsprite_backend_test_plan.json      # Generated test plan
├── testsprite_frontend_test_plan.json
├── testsprite-mcp-test-report.md          # Full test report
├── ROUND1_FIX_PRIORITY.md                # Bug fix priority list
└── tmp/raw_report.md                      # Raw TestSprite output
```

## Local Development

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Fill in your keys
python migrate.py       # Create DB tables
python app.py           # Starts on :5001
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # Fill in your keys
npm run dev                         # Starts on :3000
```

## Environment Variables

### Backend (.env)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | Claude API key |
| `FRONTEND_URL` | Frontend URL for CORS |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `STRIPE_PRICE_ID` | Stripe price ID for Pro plan |
| `ADMIN_SECRET` | Secret for admin endpoints |

### Frontend (.env.local)

| Variable | Description |
|----------|-------------|
| `NEXTAUTH_URL` | Frontend URL |
| `NEXTAUTH_SECRET` | Random 32+ char string |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `NEXT_PUBLIC_API_URL` | Backend API URL |

## License

MIT
