# Lost & Found Management System

A full-featured, secure, and production-ready web application built with **Django 6** and **Bootstrap 5** for managing lost and found item lifecycles across school campuses, universities, and organizations.

## Next.js frontend (local development)

The frontend lives in `frontend/` and uses Next.js, React, and Tailwind CSS. The backend lives in `backend/` and uses Django for authentication, permissions, database access, and application logic. Run each service from its own folder.

Install Node.js and Python, then open two terminals from the project directory:

```bash
# Terminal 1 — Django backend
cd backend
py -3.14 -m pip install -r requirements.txt
$env:DJANGO_DEBUG = "True"
py -3.14 manage.py migrate
py -3.14 manage.py seed_demo_accounts
py -3.14 manage.py seed_categories
py -3.14 manage.py seed_demo_data
py -3.14 manage.py runserver 8000

# Terminal 2 — Next.js frontend
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Set `DJANGO_URL` if the Django server runs somewhere other than `http://127.0.0.1:8000`.

For local development, explicitly enable Django debug mode before starting the backend (`$env:DJANGO_DEBUG = "True"` in PowerShell). Production starts with debug disabled and requires a unique `DJANGO_SECRET_KEY`.

`seed_demo_accounts` creates `comlab_demo_user` and `comlab_demo_admin` with random passwords and prints them once. Save the output; rerunning the command will not reset or reveal existing passwords. It refuses to run in production. The user account can browse and report items; the admin account can access the ComLab admin dashboard.

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
- **Report Lost and Found Items:** Record the existing location plus optional building, room/lab, workstation/landmark, and approximate time details; attach a photo with decoded file-type and file-size validation.
- **Item Discovery:** Keyword search, multi-attribute filtering (category, type, status, date range, location), and pagination.
- **Item Lifecycle:** Items transition from `ACTIVE` to `ARCHIVED` upon claim resolution or owner recovery.

### Claims & Verification Workflow
- **Submit Claims:** Users can submit ownership claims against found items, providing proof of ownership and identifying descriptions.
- **Admin Verification:** Administrators review claim details, inspect submitted proof, enter internal notes, and approve or reject claims.
- **Anti-Fraud Protections:** Users cannot claim their own reported items or submit duplicate claims.

### Intelligent Lost & Found Matching
- **Automated Match Detection:** Background scoring algorithm evaluates keyword similarity, category alignment, and location proximity between lost and found items.
- **Match Scores:** Rule-based similarity scores from 0–100 with component breakdowns; they are not probabilities.
- **User Verification:** Reporters can confirm or dismiss suggested matches directly from their dashboard.

### Notifications Center
- **Event-Driven Alerts:** Automated alerts triggered on claim status changes, match discoveries, and administrative updates.
- **Interactive UI:** Unread counter in the navigation bar, mark as read / mark all as read, and direct deep links to relevant items.

### Administrator Management Suite
- **Interactive Admin Dashboard:** Live metrics, recent activity feed, quick action shortcuts, and status summaries.
- **Entity Management:** Full administrative CRUD for users, items, categories, claims, and matches.
- **API Test Console:** Authorized administrators can discover API routes, probe seven HTTP methods, review responses, and inspect run history in local development.

### Reports, Analytics & Exports
- **Executive Reporting Dashboard (`/reports/`):** Real-time aggregates for lost vs. found ratio, resolution rates, category distributions, and top incident locations.
- **CSV Data Exports:** One-click streaming downloads for Items, Claims, Users Directory (with credentials safely stripped), Categories, and Matches.
- **Print-Friendly Styling:** Native CSS `@media print` rules generating clean, official print and PDF layouts with headers, timestamps, and hidden navigation controls.

### Health Check & Operations
- **Health and Readiness (`/health/`, `/ready/`):** `/health/` confirms the web process responds; `/ready/` checks database connectivity without returning internal error details.

---

## 3. Technology Stack

- **Backend:** Python 3.14, Django 6.1.1
- **WSGI / Production Server:** Gunicorn 26.2.0
- **Static Asset Serving:** WhiteNoise 6.12.0
- **Database:**
  - *Local Development:* SQLite 3
  - *Production:* PostgreSQL via `psycopg[binary]` 3.3.6 and `DATABASE_URL`
- **Frontend:** Next.js, React, Tailwind CSS, TypeScript
- **Deployment Platform:** Railway / Docker / Nixpacks

---

## 4. Project Structure

```text
Project-LostAndFound/
├── backend/                  # Django APIs, authentication, and business logic
│   ├── accounts/
│   ├── claims/
│   ├── config/
│   ├── items/
│   ├── matches/
│   ├── notifications/
│   ├── reports/
│   ├── templates/              # Legacy screens pending React migration
│   ├── manage.py
│   └── requirements.txt
├── frontend/                 # Next.js, React, and Tailwind interface
│   ├── src/app/
│   ├── src/components/
│   └── package.json
├── Procfile
├── DEPLOYMENT.md
└── README.md
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
   pip install -r backend/requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp backend/.env.example backend/.env
   ```
   Django does not load `.env` automatically in this project. Export the values in your shell or configure them in the hosting service. For PowerShell local development, set `$env:DJANGO_DEBUG = "True"` before starting Django.

5. **Apply database migrations:**
   ```bash
   python backend/manage.py migrate
   ```

6. **Collect static assets:**
   ```bash
   python backend/manage.py collectstatic --noinput
   ```

7. **Create a superuser account:**
   ```bash
   python backend/manage.py createsuperuser
   ```

8. **Start the development server:**
   ```bash
   python backend/manage.py runserver
   ```
   Open [http://localhost:3000](http://localhost:3000) for the Next.js frontend. Django runs at [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## 6. Environment Variables

Configure application settings by modifying `.env`:

| Key | Description | Development Default | Production Recommendation |
| :--- | :--- | :---: | :--- |
| `DJANGO_ENV` | Deployment environment marker | `development` | `production` |
| `DJANGO_SECRET_KEY` | Application cryptographic secret | Development fallback only with debug enabled | Unique generated secret, 60+ random characters |
| `DJANGO_DEBUG` | Django debug mode | Explicitly set `True` locally | `False` (default and enforced in recognized production environments) |
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
python backend/manage.py test
```

To run tests with detailed verbosity:
```bash
python backend/manage.py test -v 2
```

To run a specific app's tests:
```bash
python backend/manage.py test reports
python backend/manage.py test accounts
python backend/manage.py test items
python backend/manage.py test claims
python backend/manage.py test matches
python backend/manage.py test notifications
```

### API test console

Start Django with `DJANGO_DEBUG=True`, apply migrations, and sign in as an administrator. Open **API tests** in the admin dashboard to inspect discovered routes, run one endpoint/method, or run the full API suite. The console runs Django's test runner against its disposable SQLite test database; API probe writes are rolled back and outbound socket connections are blocked. It is available only with debug enabled, outside production, and on SQLite, so it cannot run against the production PostgreSQL database. Test-console control routes are intentionally excluded from endpoint probes to prevent recursive runs.

Run the same dedicated suite from a terminal with:

```bash
python backend/manage.py test api_testing.tests -v 2
```

---

## 8. Static Files

In development, Django serves static files directly. In production, **WhiteNoise** provides fast, compressed, and cached static file delivery directly from Gunicorn:

```bash
python backend/manage.py collectstatic --noinput
```

Assets are collected into the `staticfiles/` directory specified by `STATIC_ROOT`.

---

## 9. Production Deployment

For complete, detailed instructions on deploying to Railway or any standard container/Linux platform, see [DEPLOYMENT.md](DEPLOYMENT.md).

### Quick Production Start:
```bash
cd backend && gunicorn config.wsgi:application --bind 0.0.0.0:8000
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
