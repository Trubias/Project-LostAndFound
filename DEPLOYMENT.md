# Production Deployment Guide

## Lost & Found Management System

This document outlines the step-by-step procedure to deploy the Lost & Found Management System to production using **Railway**, **PostgreSQL**, **Gunicorn**, and **WhiteNoise**.

---

## 1. System Architecture

```text
[ Client / Browser ]
        │  HTTPS (Port 443)
        ▼
[ Railway Edge / Reverse Proxy (SSL Termination) ]
        │  HTTP
        ▼
[ Gunicorn WSGI Server ]
        ├── WhiteNoise (Serves static assets with cache headers & gzip/brotli)
        └── Django Application (config.wsgi:application)
                ├── Local SQLite (Development) / PostgreSQL (Production)
                └── Media Storage (Uploaded item photos & profiles)
```

- **Runtime:** Python 3.14
- **Framework:** Django 6.1.1
- **WSGI Application:** `config.wsgi:application`
- **Application Server:** Gunicorn 26.2.0
- **Static Assets:** WhiteNoise 6.12.0
- **Database Driver:** `psycopg[binary]` 3.3.6
- **Database:** PostgreSQL (Production) / SQLite (Development)
- **Container / Builder:** Nixpacks (Railway standard)

---

## 2. Environment Variables Reference

For local use, copy `backend/.env.example` to `backend/.env`; Django loads it without replacing variables already set by the shell. For production, configure these values in your deployment dashboard (e.g., Railway Service Variables):

| Variable Name | Required | Default (Dev) | Description | Production Example |
| :--- | :---: | :---: | :--- | :--- |
| `DJANGO_ENV` | Recommended | *(Empty)* | Set to `production` so safety checks can reject unsafe production settings | `production` |
| `DJANGO_SECRET_KEY` | **Yes** | Required outside explicit local debug/test | Cryptographic salt for sessions, CSRF, and passwords. Generate with `python -c "import secrets; print(secrets.token_urlsafe(60))"` | *(unique generated value)* |
| `DJANGO_DEBUG` | **Yes** | `False` | Debug defaults off; recognized production environments reject `True` | `False` |
| `DJANGO_ALLOWED_HOSTS` | **Yes** | `127.0.0.1,localhost` | Comma-separated list of allowed hostnames/domains | `lostandfound.up.railway.app,yourdomain.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | **Yes** | *(Empty)* | Comma-separated list of trusted HTTPS origins for CSRF validation | `https://lostandfound.up.railway.app,https://yourdomain.com` |
| `DATABASE_URL` | **Yes in production** | SQLite for local development | PostgreSQL connection URL. Required in production; startup fails rather than silently using SQLite. | `postgres://user:password@host:port/dbname` |
| `DJANGO_DB_CONN_MAX_AGE` | Optional | `0` local / `60` production | Seconds to reuse healthy database connections | `60` |
| `DJANGO_TIME_ZONE` | Optional | `Asia/Manila` | IANA timezone used for local date and time display | `Asia/Manila` |
| `DJANGO_MEDIA_ROOT` | **Yes in production** | `backend/media` | Directory used for uploaded item and profile images. Required in production and must be on a persistent volume or object storage mount. | `/data/media` |
| `DJANGO_SECURE_SSL_REDIRECT` | Optional | `False` | Enforce HTTPS redirection for all non-HTTPS requests | `True` |
| `DJANGO_SESSION_COOKIE_SECURE` | Optional | `False` | Transmit session cookies only over HTTPS | `True` |
| `DJANGO_CSRF_COOKIE_SECURE` | Optional | `False` | Transmit CSRF cookies only over HTTPS | `True` |
| `DJANGO_SECURE_HSTS_SECONDS` | Optional | `3600` in production / `0` local | Initial production HSTS duration (increase after HTTPS is confirmed across the deployed host) | `31536000` |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | Optional | `False` | Apply HSTS policy to all subdomains | `True` |
| `DJANGO_SECURE_HSTS_PRELOAD` | Optional | `False` | Submit domain to browser HSTS preload list | `True` |
| `DJANGO_EMAIL_BACKEND` | **Yes in production** | `console.EmailBackend` | Production startup requires SMTP so password recovery is not silently dropped. | `django.core.mail.backends.smtp.EmailBackend` |
| `DJANGO_EMAIL_HOST` | **Yes in production** | `smtp.example.com` | Outbound SMTP host | `smtp.sendgrid.net` |
| `DJANGO_EMAIL_PORT` | **Yes in production** | `587` | SMTP port | `587` |
| `DJANGO_EMAIL_USE_TLS` | **Yes in production** | `True` | Use TLS for email transmission | `True` |
| `DJANGO_EMAIL_HOST_USER` | **Yes in production** | *(Empty)* | SMTP account username | `apikey` |
| `DJANGO_EMAIL_HOST_PASSWORD` | **Yes in production** | *(Empty)* | SMTP account password/token | *(API Secret)* |
| `DJANGO_DEFAULT_FROM_EMAIL` | **Yes in production** | `noreply@lostandfound.local` | Verified sender address for system email | `notifications@yourdomain.com` |
| `MATCH_THRESHOLD` | Optional | `50` | Minimum score (0-100) for automatic Lost/Found matching | `50` |

---

## 3. Step-by-Step Railway Deployment

### Step 1: Push Code to GitHub
Ensure the intended code, root `Procfile`, backend dependencies, and frontend package lock are present:
```bash
git add .
git commit -m "Sprint 8: Production deployment configuration and documentation"
git push origin main
```

### Step 2: Create a New Project on Railway
1. Navigate to [Railway Dashboard](https://railway.app/).
2. Click **New Project** &rarr; **Deploy from GitHub repo**.
3. Select your repository: `Trubias/Project-LostAndFound`.

### Step 3: Add a PostgreSQL Database
1. In your Railway project canvas, click **+ New** &rarr; **Database** &rarr; **Add PostgreSQL**.
2. Railway will automatically create a managed PostgreSQL service and generate a `DATABASE_URL` variable.
3. In your web service settings, reference `DATABASE_URL` as a variable linking directly to the PostgreSQL database.
4. Add a persistent volume to the web service, mount it at `/data`, and set `DJANGO_MEDIA_ROOT=/data/media`. Without persistent media storage, uploaded images can be lost during redeploys.

### Step 4: Configure Environment Variables
In the Railway Web Service settings under **Variables**, set:
- `DJANGO_ENV` = `production`
- `DJANGO_SECRET_KEY` = `[Generate using python -c "import secrets; print(secrets.token_urlsafe(60))"]`
- `DJANGO_DEBUG` = `False`
- `DJANGO_ALLOWED_HOSTS` = backend public hostname, backend private hostname, and frontend public hostname (comma-separated)
- `DJANGO_CSRF_TRUSTED_ORIGINS` = `https://${{RAILWAY_PUBLIC_DOMAIN}}`
- `DJANGO_SECURE_SSL_REDIRECT` = `True`
- `DJANGO_SESSION_COOKIE_SECURE` = `True`
- `DJANGO_CSRF_COOKIE_SECURE` = `True`
- `DJANGO_SECURE_HSTS_SECONDS` = `3600` initially; after confirming HTTPS works on all deployed hosts, raise it to `31536000`
- `DJANGO_MEDIA_ROOT` = `/data/media` (with the persistent volume mounted at `/data`)
- `DJANGO_EMAIL_BACKEND` = `django.core.mail.backends.smtp.EmailBackend`
- Configure `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_USE_TLS`, `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`, and a verified `DJANGO_DEFAULT_FROM_EMAIL`. Production startup now refuses the console backend or missing SMTP settings.

### Step 5: Configure the Django Backend Service

Keep the repository root as the service root so its commands can address both project folders. Configure:

- **Build Command:** `pip install -r backend/requirements.txt && cd backend && python manage.py collectstatic --noinput`
- **Pre-Deploy Command:** `cd backend && python manage.py migrate --noinput`
- **Start Command:** `cd backend && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
- **Health Check Path:** `/ready/`
- Attach the persistent volume at `/data`; set `DJANGO_MEDIA_ROOT=/data/media`.

The root `Procfile` uses Railway's `PORT` as well. Django trusts `X-Forwarded-Proto` only in recognized production environments, so HTTPS redirects work behind Railway's TLS proxy. The production startup checks require a PostgreSQL URL, explicit host and CSRF origin lists, persistent media root, SMTP, and HTTPS secure cookies.

### Step 6: Configure the Next.js Frontend Service

Create a second service from the same repository and set its **Root Directory** to `/frontend`. Configure `npm ci` as the install/build setup and `npm run build` as the build command; use `npm start` as the start command. Add the frontend's public Railway domain to Django's `DJANGO_CSRF_TRUSTED_ORIGINS` and `DJANGO_ALLOWED_HOSTS` (password-reset URLs use the public frontend host). Add the backend service's `.railway.internal` private hostname to `DJANGO_ALLOWED_HOSTS` because Next.js uses it for server-to-server API requests.

Set `DJANGO_URL` on the frontend service to the backend service's private Railway URL, including its runtime port, for example `http://<backend-private-domain>:<backend-port>`. Set this before building because Next.js uses it for the `/media/*` rewrite. Keep the backend volume attached only to the backend service. The frontend and backend need public domains if users access them directly; backend media requests are proxied through the frontend.

### Step 7: Create an Admin Superuser on Railway
Open the Railway service terminal (or use Railway CLI `railway run`):
```bash
cd backend && python manage.py createsuperuser
```
Follow prompts to set up your production administrator account.

---

## 4. Post-Deployment Verification & Health Check

### Health Check Endpoint
Verify server responsiveness without exposing internal data:
```bash
curl -I https://<your-app>.up.railway.app/health/
```

`/health/` checks that the web process responds. Use `/ready/` for a database connectivity check; it returns `503` with a generic response when the database is unavailable.
Expected response:
```http
HTTP/2 200
content-type: application/json

{"status": "ok"}
```

### Smoke Test Checklist
- [ ] `/health/` returns `200 OK`
- [ ] `/login/` renders styled with static assets served via WhiteNoise
- [ ] User registration and authentication work
- [ ] Admin dashboard and `/reports/` accessible to admin accounts
- [ ] Item creation with image upload functions properly
- [ ] CSV export endpoints return valid CSV files with attachment headers
- [ ] Print preview on `/reports/` hides navigation and displays clean tables
- [ ] 403 / 404 custom error pages render when unauthorized paths are requested

---

## 5. Security & Maintenance Operations

### Periodic Database Backups
Railway's PostgreSQL point-in-time recovery protects the database, not uploaded images. Keep database dumps and media backups encrypted in storage outside the running service and its volume. Use one timestamp for both parts of a backup:
```bash
backup_stamp=$(date -u +%Y%m%dT%H%M%SZ)
pg_dump --format=custom --no-owner "$DATABASE_URL" --file="findly-db-${backup_stamp}.dump"
tar -C /data -czf "findly-media-${backup_stamp}.tar.gz" media
sha256sum "findly-db-${backup_stamp}.dump" "findly-media-${backup_stamp}.tar.gz" > "findly-${backup_stamp}.sha256"
```

Copy all three artifacts to encrypted off-site storage and define retention with the school. Perform a restore drill into a separate PostgreSQL database and media directory before relying on a backup. To restore, stop writes, restore the database with `pg_restore --no-owner --dbname="$RESTORE_DATABASE_URL" findly-db-<timestamp>.dump`, and extract media with `tar -C "$RESTORE_ROOT" -xzf findly-media-<timestamp>.tar.gz`. Do not point `RESTORE_DATABASE_URL` at production during a drill.

### Static Files Updates
When making frontend modifications, re-run:
```bash
cd backend && python manage.py collectstatic --noinput
```
WhiteNoise will generate hashed filenames ensuring seamless cache busting.
