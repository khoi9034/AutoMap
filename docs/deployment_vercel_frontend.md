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
