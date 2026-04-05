# TestSprite Hackathon Season 2 — Prep Kit

## Timeline

| Date | Action |
|------|--------|
| 4/11 | Hackathon opens. Post intro in Discord. Start TestSprite Round 1 |
| 4/12-14 | Fix bugs from Round 1. Run Round 2. Post progress update in Discord |
| 4/15-16 | Record demo video. Share on X. Discord engagement |
| 4/17 11:59 PM PST | Submit in #hackathon-s02-submission |
| 4/23 | Winners announced |

## TestSprite Workflow

### Round 1 (4/11)
```bash
# Start backend
cd backend && source venv/bin/activate && python app.py

# Start frontend (separate terminal)
cd frontend && npm run dev

# In Claude (from jobpilot dir):
# "Help me test this project with TestSprite"
# Or manually:
# 1. testsprite_bootstrap_tests (type: "backend", localPort: 5000, testScope: "codebase")
# 2. testsprite_generate_code_summary
# 3. testsprite_generate_standardized_prd
# 4. testsprite_generate_backend_test_plan
# 5. testsprite_generate_code_and_execute
# Then repeat for frontend (type: "frontend", localPort: 3000)
```

Commit: "Round 1: initial TestSprite test generation"

### Round 2 (4/12-14)
1. Review testsprite_tests/tmp/report_prompt.json for fix suggestions
2. Fix real bugs found
3. Run testsprite_rerun_tests or re-generate with testScope: "diff"
4. Commit: "Round 2: improved coverage after fixes"

## Discord Posts

### Intro (post 4/11)

Hey everyone! Excited to be part of TestSprite Hackathon Season 2.

I'm submitting **JobPilot** — an AI-powered job search platform built specifically for F-1 international students in the US. If you've ever spent hours manually checking whether a company sponsors visas, you know the pain.

JobPilot parses your resume, searches real job boards via Greenhouse and Lever APIs, **verifies every listing is still open with live API calls** (no stale postings), filters by visa sponsorship/degree/location, and generates tailored cover letters using Claude AI — all in one workflow.

**Tech stack:** Next.js frontend on Vercel, Flask backend on Railway, Stripe payments, Claude API for resume parsing + cover letter generation, PostgreSQL, and live API integration with 6 regional Greenhouse/Lever endpoints.

It's a live SaaS product with paying users, not a hackathon prototype. Looking forward to seeing what TestSprite finds under the hood!

### Progress Update (post after Round 1)

Just ran TestSprite Round 1 on JobPilot — it generated tests across the entire application without any manual configuration. It caught edge cases I hadn't considered: malformed resume uploads, empty API responses from Greenhouse, Stripe webhook signature failures, and some auth flow gaps around session expiration.

The fact that it understood the multi-service architecture (Vercel frontend → Railway backend → external APIs) and tested across those boundaries is genuinely impressive. Already fixing bugs it surfaced. Round 2 coming soon.

### Submission (post 4/17)

**JobPilot — Final Submission**

An AI-powered job search platform for F-1 international students, tested end-to-end with TestSprite.

**Key stats:**
- Auto-generated tests covering frontend, backend, and API integrations
- Live SaaS with Stripe payments and real users
- 6 regional Greenhouse/Lever endpoints with live verification
- Full AI pipeline: resume parsing → job matching → cover letter generation via Claude
- Real bugs found and fixed thanks to TestSprite

GitHub: https://github.com/CherishChenCherish/jobpilot
Live app: https://jobpilot-plum.vercel.app

TestSprite saved me hours of manual test writing and caught issues across service boundaries I wouldn't have tested myself.

## X (Twitter) Post

Ran @TestSprite on my live AI job search SaaS and it generated tests automatically — caught real bugs in my API error handling I'd missed for months. Actual value, not hype. [screenshot]

## Demo Video Script (~60 sec)

**[0:00-0:08] The Problem**
Screen: Google search "H1B sponsor jobs" → outdated results
VO: "If you're an international student, job searching is brutal. Most listings are expired, companies don't say if they sponsor visas."

**[0:08-0:18] Introduce JobPilot**
Screen: Land on homepage, show tagline, sign in
VO: "JobPilot fixes this. Upload your resume, AI does the rest."

**[0:18-0:28] Upload Resume**
Screen: Drag-drop PDF. Parsing spinner → extracted skills appear
VO: "Claude AI parses your resume — skills, degree, experience — no manual entry."

**[0:28-0:38] Job Results**
Screen: Click search. Results with "Verified Open" badges. Visa/location filters active
VO: "Every job is pulled live from Greenhouse and Lever APIs and verified open right now. Six regions, hundreds of companies."

**[0:38-0:48] Cover Letter**
Screen: Click "Generate Cover Letter". Claude-generated letter appears
VO: "One click generates a tailored cover letter matched to the job and your resume."

**[0:48-0:55] Tech & Testing**
Screen: Flash tech stack, then TestSprite results
VO: "Built with Next.js, Flask, Stripe, Claude. TestSprite generated automated tests and caught real bugs across the full stack."

**[0:55-1:00] Close**
Screen: App with logo
VO: "JobPilot. Stop searching. Start applying."
