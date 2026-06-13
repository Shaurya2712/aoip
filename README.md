# AOIP — App Opportunity Intelligence Platform

## What this is

AOIP is a 24/7 autonomous research platform that discovers, scores, and ranks Android app opportunities for the Indian market. Developers seed the platform with keywords; AI expands them into related search queries, scrapers collect Google Trends, Play Store, and Reddit data, and Gemini scores and ranks every opportunity.

The dashboard displays ranked opportunities, competitor intelligence, community insights, product concepts, and live scheduler job status — all stored in Supabase and updated continuously by the backend scheduler.

## Prerequisites

- **Node.js 18+** — for the Next.js frontend
- **Python 3.11+** — for the FastAPI backend
- **Supabase account** — [supabase.com](https://supabase.com) (free tier works)
- **Gemini API key** — [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- **Reddit API credentials** (optional) — [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) (script-type app)

## Database setup

1. Create a new project at [supabase.com/dashboard](https://supabase.com/dashboard).

2. Open **SQL Editor** in the Supabase dashboard.

3. Run `supabase/schema.sql` — paste the full file contents and click **Run**.

4. Run `supabase/rls_policies.sql` — paste the full file contents and click **Run**.

5. Run `supabase/seed_niches.sql` — paste the full file contents and click **Run**.

6. Create a storage bucket for daily reports:
   - Go to **Storage** → **New bucket**
   - Name: `reports`
   - Public: **off** (private)
   - Click **Create bucket**

7. Create a dashboard user:
   - Go to **Authentication** → **Users** → **Add user**
   - Enter an email and password (this is the login for the frontend)

8. Copy your project credentials from **Project Settings** → **API**:
   - Project URL → `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL`
   - `anon` public key → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `service_role` secret key → `SUPABASE_SERVICE_KEY` (backend only — never expose in frontend)

## Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` and fill in all values:

| Variable | Where to get it |
|---|---|
| `SUPABASE_URL` | Supabase → Project Settings → API → Project URL |
| `SUPABASE_SERVICE_KEY` | Supabase → Project Settings → API → service_role key |
| `GEMINI_API_KEY` | Google AI Studio |
| `REDDIT_CLIENT_ID` | Reddit app preferences (optional) |
| `REDDIT_CLIENT_SECRET` | Reddit app preferences (optional) |
| `REDDIT_USER_AGENT` | Any descriptive string, e.g. `AOIP/1.0 by yourusername` |
| `BACKEND_SECRET` | Generate a random string |
| `ENV` | `development` locally, `production` when deployed |
| `FRONTEND_URL` | Optional — your Vercel URL for CORS (production only) |

Start the backend:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify it is running:

```bash
curl http://localhost:8000/health
```

Expected response: `{"status":"ok"}`

## Frontend setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
```

Edit `frontend/.env.local` and fill in all values:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Same Project URL as backend |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon public key |
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` locally, or your Render URL in production |

Start the frontend:

```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and log in with the Supabase user you created.

## Deployment

### 1. Push to GitHub

```bash
cd aoip
git init
git add .
git commit -m "Initial commit: AOIP platform"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/aoip.git
git push -u origin main
```

`.gitignore` excludes `.env`, `.venv`, `node_modules`, and `.next` — secrets stay local.

### 2. Backend — Render (Docker)

1. Connect your GitHub repo at [render.com](https://render.com).
2. Create a **Web Service** with these settings:

| Setting | Value |
|---------|-------|
| **Root Directory** | `backend` |
| **Environment** | **Docker** |
| **Dockerfile Path** | `./Dockerfile` |
| **Health Check Path** | `/health` |

Or use the included `render.yaml` blueprint at the repo root.

3. Add **Environment Variables** in the Render dashboard (same as `backend/.env`):

| Variable | Value |
|----------|-------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service_role key |
| `GEMINI_API_KEY` | Google AI Studio key |
| `REDDIT_CLIENT_ID` | Optional — skip if not using Reddit |
| `REDDIT_CLIENT_SECRET` | Optional |
| `REDDIT_USER_AGENT` | `AOIP/1.0 by yourusername` |
| `BACKEND_SECRET` | Random secret string |
| `ENV` | `production` |
| `FRONTEND_URL` | Your Vercel URL, e.g. `https://aoip.vercel.app` |

4. Deploy and note the service URL, e.g. `https://aoip-backend.onrender.com`.

**Keep Render awake (free tier):** Ping every 10 minutes at [cron-job.org](https://cron-job.org):

```
GET https://aoip-backend.onrender.com/health
```

### 3. Frontend — Vercel

1. Import the repo at [vercel.com](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Add **Environment Variables**:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_SUPABASE_URL` | Same Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon public key |
| `NEXT_PUBLIC_BACKEND_URL` | Your Render URL, e.g. `https://aoip-backend.onrender.com` |

4. Deploy. Vercel runs `npm run build` automatically.

### 4. Supabase Auth (production)

In Supabase → **Authentication** → **URL Configuration**:

| Setting | Value |
|---------|-------|
| **Site URL** | `https://your-app.vercel.app` |
| **Redirect URLs** | `https://your-app.vercel.app/**` |

### Where URLs need to change

**You do NOT edit URLs in source code for deployment.** Set them via environment variables:

| Where | Variable | Local value | Production value |
|-------|----------|-------------|------------------|
| **Vercel** | `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` | `https://aoip-backend.onrender.com` |
| **Vercel** | `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase URL | Same |
| **Vercel** | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Your anon key | Same |
| **Render** | `FRONTEND_URL` | (optional locally) | `https://your-app.vercel.app` |
| **Supabase Auth** | Site URL | `http://localhost:3000` | `https://your-app.vercel.app` |
| **cron-job.org** | Health ping URL | — | `https://aoip-backend.onrender.com/health` |

**Files that read these URLs (no manual edits needed):**

- `frontend/lib/utils.ts` → `NEXT_PUBLIC_BACKEND_URL`
- `frontend/lib/supabase.ts` → `NEXT_PUBLIC_SUPABASE_*`
- `frontend/app/(dashboard)/niches/page.tsx` → uses `BACKEND_URL`
- `frontend/components/SeedKeywordImporter.tsx` → uses `BACKEND_URL`
- `frontend/app/(dashboard)/reports/page.tsx` → uses `BACKEND_URL`
- `frontend/app/(dashboard)/competitors/page.tsx` → uses `BACKEND_URL`
- `backend/main.py` → CORS reads `FRONTEND_URL` / `CORS_ORIGINS` from env

**Never commit:** `backend/.env`, `frontend/.env`, `frontend/.env.local`

## First run checklist

After both backend and frontend are running (locally or deployed):

- [ ] Confirm 11 default niches appear on the **Niches** page (from `seed_niches.sql`)
- [ ] Add seed keywords to at least one niche via the dashboard
- [ ] Verify the backend health endpoint responds:
  ```bash
  curl https://your-app.onrender.com/health
  ```
- [ ] Open the **Scheduler** page and confirm the first job (`keyword_expansion`) appears in `job_log` within a few minutes of backend startup
- [ ] Wait for the scheduler cycle — opportunities, competitors, and scores will populate over the first 6–24 hours
