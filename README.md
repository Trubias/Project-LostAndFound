# Lost & Found Management System

A full-featured, secure, and production-ready web application built with **Django 6** and **Bootstrap 5** for managing lost and found item lifecycles across school campuses, universities, and organizations.

---

## 1. Project Description

The **Lost & Found Management System** simplifies the tracking, claiming, and returning of misplaced personal property. It bridges communication between people who lost items and those who found them through an automated matching engine, direct claims management, real-time notifications, a granular role-based administration suite, and executive analytics reports with one-click CSV exports.

---

## 2. Key Features

### Authentication & Role-Based Access Control (RBAC)
- **User Roles:** Distinct privileges for regular users (`USER`) and administrators (`ADMIN`).
- **Registration & Profile Management:** Secure account registration, profile pictures, contact details, and password changes.
- **Session & CSRF Security:** Strong password validators, HTTPS cookie flags, CSRF tokens on all state-altering forms, and secure logout handlers.

### Item Management & Discovery
- **Report Lost Items:** Detail title, description, category, location, and date of occurrence.
- **Report Found Items:** Add custody location, description, category, and optional photo upload with file-type and file-size validation.
- **Item Discovery:** Keyword search, multi-attribute filtering (category, type, status, date range, location), and pagination.
- **Item Lifecycle:** Items transition from `ACTIVE` to `ARCHIVED` upon claim resolution or owner recovery.

### Claims & Verification Workflow
- **Submit Claims:** Users can submit ownership claims against found items, providing proof of ownership and identifying descriptions.
- **Admin Verification:** Administrators review claim details, inspect submitted proof, enter internal notes, and approve or reject claims.
- **Anti-Fraud Protections:** Users cannot claim their own reported items or submit duplicate claims.

### Intelligent Lost & Found Matching
- **Automated Match Detection:** Background scoring algorithm evaluates keyword similarity, category alignment, and location proximity between lost and found items.
- **Match Scores:** Calculated 0–100% confidence scores with component score breakdowns.
- **User Verification:** Reporters can confirm or dismiss suggested matches directly from their dashboard.

### Notifications Center
- **Event-Driven Alerts:** Automated alerts triggered on claim status changes, match discoveries, and administrative updates.
- **Interactive UI:** Unread counter in the navigation bar, mark as read / mark all as read, and direct deep links to relevant items.

### Administrator Management Suite
- **Interactive Admin Dashboard:** Live metrics, recent activity feed, quick action shortcuts, and status summaries.
- **Entity Management:** Full administrative CRUD for users, items, categories, claims, and matches.

### Reports, Analytics & Exports
- **Executive Reporting Dashboard (`/reports/`):** Real-time aggregates for lost vs. found ratio, resolution rates, category distributions, and top incident locations.
- **CSV Data Exports:** One-click streaming downloads for Items, Claims, Users Directory (with credentials safely stripped), Categories, and Matches.
- **Print-Friendly Styling:** Native CSS `@media print` rules generating clean, official print and PDF layouts with headers, timestamps, and hidden navigation controls.

### Health Check & Operations
- **Health Endpoint (`/health/`):** Lightweight JSON endpoint (`{"status": "ok"}`) for container orchestrators, uptime monitors, and Railway deployment healthchecks.

---

## 3. Technology Stack

- **Backend:** Python 3.14, Django 6.1.1
- **WSGI / Production Server:** Gunicorn 26.2.0
- **Static Asset Serving:** WhiteNoise 6.12.0
- **Database:**
  - *Local Development:* SQLite 3
  - *Production:* PostgreSQL via `psycopg[binary]` 3.3.6 and `DATABASE_URL`
- **Frontend:** Django Templates, Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Inter Font
- **Deployment Platform:** Railway / Docker / Nixpacks

---

## 4. Project Structure

```text
Project/
├── accounts/               # User authentication, profiles, and admin views
│   ├── admin_views.py     # Administrative dashboard & management handlers
│   ├── models.py          # User Profile model & post-save signals
│   └── views.py           # Login, registration, profile, RBAC decorators
├── claims/                 # Ownership claims and verification workflow
│   ├── models.py          # Claim model & status state machine
│   └── views.py           # Claim submission & review views
├── config/                 # Main Django project configuration
│   ├── settings.py        # Settings with WhiteNoise, PostgreSQL & security
│   ├── urls.py            # Global URL routing & /health/ endpoint
│   └── wsgi.py            # Production WSGI application callable
├── items/                  # Item catalog, reporting, and search
│   ├── forms.py           # ItemReportForm & CategoryForm with validation
│   ├── models.py          # Item & Category models
│   └── views.py           # Browse, search, filter, and detail views
├── matches/                # Automated Lost & Found matching engine
│   ├── engine.py          # Similarity scoring algorithm
│   └── models.py          # ItemMatch model
├── notifications/          # In-app notification system
│   ├── context_processors.py  # Unread badge notification counters
│   └── models.py          # Notification model
├── reports/                # Reporting dashboard & CSV exports
│   ├── urls.py            # Export & dashboard routes
│   └── views.py           # Aggregations, print views, & CSV generators
├── static/                 # Source CSS, JavaScript, and images
├── staticfiles/            # Collected production static assets (WhiteNoise)
├── templates/              # Semantic Bootstrap 5 Django templates
│   ├── admin_dashboard/   # Admin dashboard, management tables & sidebar
│   ├── items/             # Browse, report, detail templates
│   ├── reports/           # Reports & print analytics dashboard
│   └── base.html          # Global responsive navigation, badges, & footer
├── .env.example            # Environment variables template
├── DEPLOYMENT.md           # Production deployment checklist & guide
├── Procfile                # Gunicorn process definition
├── railway.json            # Railway deployment configuration
├── requirements.txt        # Production dependencies
└── manage.py               # Django management script
```

---

## 5. Local Installation & Setup

### Prerequisites
- Python 3.12+ (Python 3.14 tested)
- Git

### Quickstart

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Trubias/Project-LostAndFound.git
   cd Project-LostAndFound
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```

5. **Apply database migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Collect static assets:**
   ```bash
   python manage.py collectstatic --noinput
   ```

7. **Create a superuser account:**
   ```bash
   python manage.py createsuperuser
   ```

8. **Start the development server:**
   ```bash
   python manage.py runserver
   ```
   Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your web browser.

---

## 6. Environment Variables

Configure application settings by modifying `.env`:

| Key | Description | Development Default | Production Recommendation |
| :--- | :--- | :---: | :--- |
| `DJANGO_SECRET_KEY` | Application cryptographic secret | *(development fallback)* | 60+ random characters |
| `DJANGO_DEBUG` | Django debug mode | `True` | `False` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hostnames | `127.0.0.1,localhost` | Your domain or Railway public domain |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Trusted origins for CSRF validation | *(Empty)* | `https://your-domain.com` |
| `DATABASE_URL` | PostgreSQL database connection string | *(Empty, uses SQLite)* | `postgres://user:pass@host:port/db` |
| `DJANGO_SECURE_SSL_REDIRECT` | Redirect HTTP to HTTPS | `False` | `True` |
| `DJANGO_SESSION_COOKIE_SECURE`| Cookie HTTPS only flag | `False` | `True` |
| `DJANGO_CSRF_COOKIE_SECURE` | CSRF cookie HTTPS only flag | `False` | `True` |

---

## 7. Running Tests

Run the full automated test suite (covering authentication, models, views, RBAC, matching, claims, security, reports, and CSV exports):

```bash
python manage.py test
```

To run tests with detailed verbosity:
```bash
python manage.py test -v 2
```

To run a specific app's tests:
```bash
python manage.py test reports
python manage.py test accounts
python manage.py test items
python manage.py test claims
python manage.py test matches
python manage.py test notifications
```

---

## 8. Static Files

In development, Django serves static files directly. In production, **WhiteNoise** provides fast, compressed, and cached static file delivery directly from Gunicorn:

```bash
python manage.py collectstatic --noinput
```

Assets are collected into the `staticfiles/` directory specified by `STATIC_ROOT`.

---

## 9. Production Deployment

For complete, detailed instructions on deploying to Railway or any standard container/Linux platform, see [DEPLOYMENT.md](DEPLOYMENT.md).

### Quick Production Start:
```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

---

## 10. Sprint Development Roadmap

| Sprint | Milestone | Status | Key Deliverables |
| :---: | :--- | :---: | :--- |
| **Sprint 1** | Authentication & User/Admin Roles | ✅ Completed | Custom profile, RBAC decorators, login, register, profile editing |
| **Sprint 2** | Lost & Found Item Management | ✅ Completed | Report lost/found forms, category foreign keys, image upload validation |
| **Sprint 3** | Search, Filtering & Discovery | ✅ Completed | Full-text query, multi-attribute filtering, pagination, item detail |
| **Sprint 4** | Claims & Item Verification | ✅ Completed | Claim creation, proof submission, fraud prevention, admin approval |
| **Sprint 5** | Admin Management & Dashboard | ✅ Completed | Admin dashboard, entity management tables, status transitions |
| **Sprint 6** | Notifications & Matching Engine | ✅ Completed | Keyword/category/location match engine, in-app notifications |
| **Sprint 7** | Security, Testing & QA | ✅ Completed | CSRF checks, file upload security, automated test suite, 403/404 pages |
| **Sprint 8** | Final UI, Reports & Deployment | ✅ Completed | Executive reports dashboard, CSV exports, WhiteNoise, Gunicorn, PostgreSQL readiness, Railway config, DEPLOYMENT.md |

---

## License

This project is open-source software built for educational and organizational lost and found management.
