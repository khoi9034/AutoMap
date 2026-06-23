# Vercel Frontend Deployment

The deployed frontend is:

```text
https://auto-map-cyan.vercel.app
```

Vercel project:

```text
Project name: auto-map
Project ID: prj_OoA139zaivCLzq9iRFF0Ny0WQtlD
Root Directory: frontend
Framework Preset: Next.js
Install Command: npm install
Build Command: npm run build
Output Directory: default / blank
```

## Backend API URL

Production browser requests use a same-origin Vercel route handler at `/api/automap/*`.
The route handler forwards requests to the Render backend. Set this server-only
Vercel environment variable:

```text
AUTOMAP_API_SERVER_URL=https://automap-api.onrender.com
```

This value is not a secret, but it must not be a `NEXT_PUBLIC_*` variable. The browser
should call `/api/automap/composer/generate`, not Render directly.

Keep this public variable if you want the UI to display the deployed backend host:

```text
NEXT_PUBLIC_AUTOMAP_API_BASE_URL=https://automap-api.onrender.com
```

Then redeploy the Vercel frontend.

Do not set production API values to `localhost` or `127.0.0.1`. Local values only belong in `frontend/.env.local`.

## Secrets Boundary

Do not put these in Vercel frontend env:

- Supabase database password
- Supabase service role key
- ArcGIS password
- backend-only secrets

The frontend should only receive public browser-safe values.

## Recruiter-Safe Public Demo

The Vercel frontend is the stable public portfolio layer. It now renders a professional landing page at `/` and keeps `/map-composer` usable even when the Render backend is cold-starting, slow, or temporarily unavailable.

Production behavior:

- `/` explains the project and shows live readiness without depending on a fast backend response.
- `/api/automap/*` proxies backend requests through Vercel so the browser does not depend on direct Render CORS.
- Health checks show friendly "backend waking up" copy for free-tier cold starts.
- Map Composer offers a static demo fallback for the known 793 Bartram Ave nearest-fire-station prompt if live generation is slow or unavailable.
- Live address and parcel workflows are explicitly labeled as Cabarrus County, NC only. Out-of-county addresses are not
  supported in this prototype, so recruiter users should test Cabarrus County addresses, parcels/PINs, or planning
  prompts.
- Real ArcGIS publish remains disabled and no backend secrets are exposed to the browser.

For recruiter/resume traffic, consider upgrading Render or adding uptime monitoring so the backend stays warm before interviews or application reviews.

Run the safe production smoke check from repo root:

```bash
python scripts/production_smoke_check.py
```
