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

After the backend is deployed, set this Vercel environment variable:

```text
NEXT_PUBLIC_AUTOMAP_API_BASE_URL=https://YOUR_DEPLOYED_BACKEND_URL
```

Then redeploy the Vercel frontend.

Do not set the production value to `localhost` or `127.0.0.1`. Local values only belong in `frontend/.env.local`.

## Secrets Boundary

Do not put these in Vercel frontend env:

- Supabase database password
- Supabase service role key
- ArcGIS password
- backend-only secrets

The frontend should only receive public browser-safe values.
