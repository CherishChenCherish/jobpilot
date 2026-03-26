# JobPilot

**Find jobs that are actually still open.** Upload your resume. We verify every posting is open, then write your cover letters.

## Architecture

```
jobpilot/
├── backend/         Flask API (Python)
│   ├── app.py       Main API with all routes
│   ├── parser.py    Resume parsing (PyMuPDF + Claude)
│   ├── searcher.py  Job search (Greenhouse/Lever APIs)
│   ├── verifier.py  Job verification (HTML + API checks)
│   ├── generator.py Cover letter generation (Claude)
│   ├── exporter.py  Excel export (4-sheet styled output)
│   └── models.py    SQLAlchemy models
└── frontend/        Next.js 14 (TypeScript + Tailwind)
    ├── app/page.tsx         Landing page
    ├── app/dashboard/       3-state dashboard
    ├── app/pricing/         Pricing + FAQ
    └── lib/auth.ts          Google OAuth (NextAuth)
```

## 1. Local Development

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Fill in your keys
python migrate.py       # Create DB tables
python app.py           # Starts on :5000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # Fill in your keys
npm run dev                         # Starts on :3000
```

## 2. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project > APIs & Services > Credentials
3. Create OAuth 2.0 Client ID (Web application)
4. Authorized redirect URIs: `http://localhost:3000/api/auth/callback/google`
5. Copy Client ID and Secret to both `.env` files

## 3. Stripe Setup

1. Create account at [stripe.com](https://stripe.com)
2. Products > Create product: "JobPilot Pro" $12/month recurring
3. Copy the Price ID (starts with `price_`)
4. Developers > Webhooks > Add endpoint:
   - URL: `https://your-backend.railway.app/api/stripe/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.deleted`, `invoice.payment_failed`
5. Copy signing secret (starts with `whsec_`)

## 4. Deploy Backend (Railway)

```bash
cd backend
railway login
railway init
railway up
# Set environment variables in Railway dashboard
```

## 5. Deploy Frontend (Vercel)

```bash
cd frontend
vercel login
vercel --prod
# Set environment variables in Vercel dashboard
```

## 6. Environment Variables

### Backend (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | Yes | Claude API key for parsing/generation |
| `FRONTEND_URL` | Yes | Frontend URL for CORS |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
| `STRIPE_SECRET_KEY` | Yes | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing secret |
| `STRIPE_PRICE_ID` | Yes | Stripe price ID for Pro plan |

### Frontend (.env.local)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXTAUTH_URL` | Yes | Frontend URL |
| `NEXTAUTH_SECRET` | Yes | Random 32+ char string |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret |
| `NEXT_PUBLIC_API_URL` | Yes | Backend API URL |

## 7. Cost per Search

| Component | Cost | Notes |
|-----------|------|-------|
| Claude API (parse) | ~$0.01 | Sonnet, ~3K tokens |
| Claude API (10 CLs) | ~$0.10 | Sonnet, ~1K tokens each |
| Greenhouse/Lever API | $0.00 | Free public APIs |
| Verification (HTTP) | $0.00 | Direct requests |
| **Total per search** | **~$0.11** | $12/mo breaks even at ~109 searches |

## License

MIT
