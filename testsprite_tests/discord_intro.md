## Discord Intro Post — TestSprite Hackathon Season 2

Hey everyone 👋 — excited to be in TestSprite Hackathon Season 2.

I'm submitting **JobPilot** — an AI-powered job search platform built for F-1 international students in the US. If you've ever lost an afternoon manually checking whether a company sponsors visas, you know the pain.

**What it does**
- Parses your resume with Claude (skills, degree, direction, experience)
- Pulls live postings from 6 regional Greenhouse + Lever endpoints (US, UK, CA, AU, HK, CN)
- Runs every listing through a 4-condition "Core Promise" gate before it ever reaches a user: **open · location match · direction match · identity match (degree + visa)**
- Generates a tailored cover letter per job via the Claude API, one click

It's a live SaaS with Stripe payments and real paying users — not a hackathon prototype.

**Stack**
Next.js on Vercel · Flask on Railway · PostgreSQL · Stripe · Claude API · Scrapling + BS4 fallback for web discovery · GitHub Actions cron for daily refresh.

**Why I'm excited about TestSprite**
The backend has 19 endpoints and the promise gate has a lot of edge cases around degree hierarchy (PhD→MS→BS) and visa language detection. I've been maintaining pytest suites by hand — curious to see what TestSprite finds at the service boundaries (Greenhouse/Lever failures, Stripe webhooks, SSE streaming, multipart resume upload) that I've been skipping.

Round 1 kicked off today. Will post results + any real bugs TestSprite surfaces in a couple days.

Live app: https://jobpilot-plum.vercel.app
Repo: https://github.com/CherishChenCherish/jobpilot
