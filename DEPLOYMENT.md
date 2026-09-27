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

Configure these environment variables in your deployment dashboard (e.g., Railway Service Variables):

| Variable Name | Required | Default (Dev) | Description | Production Example |
| :--- | :---: | :---: | :--- | :--- |
| `DJANGO_SECRET_KEY` | **Yes** | Insecure dev key | Cryptographic salt for sessions, CSRF, and passwords. Generate with `python -c "import secrets; print(secrets.token_urlsafe(60))"` | `s8A_f9...K2q!` (60+ characters) |
| `DJANGO_DEBUG` | **Yes** | `True` | Set to `False` in production to prevent stack trace disclosure | `False` |
| `DJANGO_ALLOWED_HOSTS` | **Yes** | `127.0.0.1,localhost` | Comma-separated list of allowed hostnames/domains | `lostandfound.up.railway.app,yourdomain.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | **Yes** | *(Empty)* | Comma-separated list of trusted HTTPS origins for CSRF validation | `https://lostandfound.up.railway.app,https://yourdomain.com` |
| `DATABASE_URL` | **Yes** | *(Uses SQLite)* | PostgreSQL connection URL. Automatically provided by Railway PostgreSQL plugin | `postgres://user:password@host:port/dbname` |
| `DJANGO_SECURE_SSL_REDIRECT` | Optional | `False` | Enforce HTTPS redirection for all non-HTTPS requests | `True` |
| `DJANGO_SESSION_COOKIE_SECURE` | Optional | `False` | Transmit session cookies only over HTTPS | `True` |
| `DJANGO_CSRF_COOKIE_SECURE` | Optional | `False` | Transmit CSRF cookies only over HTTPS | `True` |
| `DJANGO_SECURE_HSTS_SECONDS` | Optional | `0` | HTTP Strict Transport Security duration (e.g., 31536000 for 1 year) | `31536000` |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | Optional | `False` | Apply HSTS policy to all subdomains | `True` |
| `DJANGO_SECURE_HSTS_PRELOAD` | Optional | `False` | Submit domain to browser HSTS preload list | `True` |
| `DJANGO_EMAIL_BACKEND` | Optional | `console.EmailBackend` | Django email backend (`django.core.mail.backends.smtp.EmailBackend` for SMTP) | `django.core.mail.backends.smtp.EmailBackend` |
| `DJANGO_EMAIL_HOST` | Optional | *(Empty)* | Outbound SMTP host | `smtp.sendgrid.net` |
| `DJANGO_EMAIL_PORT` | Optional | `587` | SMTP port | `587` |
| `DJANGO_EMAIL_USE_TLS` | Optional | `True` | Use TLS for email transmission | `True` |
| `DJANGO_EMAIL_HOST_USER` | Optional | *(Empty)* | SMTP account username | `apikey` |
| `DJANGO_EMAIL_HOST_PASSWORD` | Optional | *(Empty)* | SMTP account password/token | *(API Secret)* |
| `DJANGO_DEFAULT_FROM_EMAIL` | Optional | `noreply@lostandfound.local` | Default sender address for system notifications | `notifications@yourdomain.com` |
| `MATCH_THRESHOLD` | Optional | `50` | Minimum score (0-100) for automatic Lost/Found matching | `50` |

---

## 3. Step-by-Step Railway Deployment

### Step 1: Push Code to GitHub
Ensure all Sprint 1–8 code, `Procfile`, `railway.json`, `runtime.txt`, and `requirements.txt` are committed:
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

### Step 4: Configure Environment Variables
In the Railway Web Service settings under **Variables**, set:
- `DJANGO_SECRET_KEY` = `[Generate using python -c "import secrets; print(secrets.token_urlsafe(60))"]`
- `DJANGO_DEBUG` = `False`
- `DJANGO_ALLOWED_HOSTS` = `${{RAILWAY_PUBLIC_DOMAIN}}`
- `DJANGO_CSRF_TRUSTED_ORIGINS` = `https://${{RAILWAY_PUBLIC_DOMAIN}}`
- `DJANGO_SECURE_SSL_REDIRECT` = `True`
- `DJANGO_SESSION_COOKIE_SECURE` = `True`
- `DJANGO_CSRF_COOKIE_SECURE` = `True`

### Step 5: Configure Build & Deploy Commands
Railway reads `railway.json` and `Procfile` automatically:
- **Build Command:**
  ```bash
  python manage.py collectstatic --noinput
  ```
- **Pre-Deploy Migration Command:**
  ```bash
  python manage.py migrate
  ```
- **Start Command:**
  ```bash
  gunicorn config.wsgi:application
  ```

### Step 6: Create an Admin Superuser on Railway
Open the Railway service terminal (or use Railway CLI `railway run`):
```bash
python manage.py createsuperuser
```
Follow prompts to set up your production administrator account.

---

## 4. Post-Deployment Verification & Health Check

### Health Check Endpoint
Verify server responsiveness without exposing internal data:
```bash
curl -I https://<your-app>.up.railway.app/health/
```
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
Railway provides automated point-in-time PostgreSQL backups in the Database service tab. Manual dumps can be made via:
```bash
pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d).sql
```

### Static Files Updates
When making frontend modifications, re-run:
```bash
python manage.py collectstatic --noinput
```
WhiteNoise will generate hashed filenames ensuring seamless cache busting.
