# Lost & Found Management System

A web-based Lost and Found Management System built with **Django**.

## Tech Stack
- Python 3.14
- Django 6.1.1
- SQLite (development)
- Bootstrap 5

## Setup

```bash
# Clone the repo
git clone https://github.com/Trubias/Project-LostAndFound.git
cd Project-LostAndFound

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate     # Windows
source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

## Sprints

| Sprint | Status | Features |
|--------|--------|----------|
| Sprint 1 | ✅ Complete | Auth, Roles, Dashboards, Profiles |
| Sprint 2 | 🔜 Upcoming | Lost & Found item reports |
| Sprint 3 | 🔜 Upcoming | Item search & matching |
| Sprint 4 | 🔜 Upcoming | Claims & notifications |

## URLs

| URL | Description |
|-----|-------------|
| `/register/` | User registration |
| `/login/` | User login |
| `/logout/` | User logout |
| `/dashboard/` | User dashboard |
| `/admin-dashboard/` | Admin dashboard |
| `/profile/` | User profile |
| `/admin/` | Django admin panel |
