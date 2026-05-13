# Coach Jafri PT — Personal Training Platform

A full-stack Django web application for a personal training coaching business. Clients can browse coaching programs, enroll, and manage their memberships. Coaches manage trainees, assign session times, add notes, and track progress — all from a clean admin dashboard.

## Features

- **Personal Coaching Programs** — Three tiers (Starter, Elite 1-on-1, 90-Day Transformation) with benefits, pricing, and descriptions managed from the admin.
- **Enrollment Workflow** — Clients select a program, submit their phone number, and the coach contacts them within 2 hours to finalise setup.
- **Trainee Dashboard** — View active programs, session time slots, days remaining, coach notes, and a threaded chat with the coach.
- **Membership Lifecycle** — Pending → Active → Postponed / Canceled / Expired, with frozen-day support for postponements.
- **Session Scheduling** — Coach assigns daily session windows; the system prevents double-booking across active memberships.
- **Coach Notes & Chat** — Sticky permanent instructions plus a threaded message thread per membership.
- **Payment Requests** — Manual callback flow (no Stripe keys required for local dev). Stripe Checkout integration available when keys are configured.
- **EmailJS Notifications** — Welcome emails and request confirmations sent via EmailJS when keys are configured.
- **Admin Dashboard** — Branded "Coach Jafri PT" admin with colour-coded status badges, session-window display, and status-transition guards.
- **Responsive UI** — Bootstrap 5 + custom CSS with gradient design, sticky nav, and mobile-first layouts.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` (or create it) and set:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
STRIPE_SECRET_KEY=sk_test_...        # optional — app works without it
STRIPE_PUBLISHABLE_KEY=pk_test_...   # optional
SITE_NAME=Coach Jafri PT
SITE_TAGLINE=Personalized Training. Proven Results. Your Journey Starts Here.
# EmailJS (optional)
EMAILJS_SERVICE_ID=
EMAILJS_TEMPLATE_ID=
EMAILJS_PUBLIC_KEY=
EMAILJS_PRIVATE_KEY=
```

```bash
python manage.py migrate
python manage.py seed_plans        # creates 3 default coaching plans
python manage.py createsuperuser   # optional
python manage.py collectstatic
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` to see the home page.

## Project Structure

```
fitness_project/
├── accounts/          # Registration, login, logout
├── core/              # Home, About, Contact pages + context processors
├── memberships/       # Coaching plans, subscriptions, scheduling, notes
│   └── management/commands/seed_plans.py
├── payments/          # PaymentRequest tracking + Stripe integration
├── templates/         # All HTML templates
├── static/            # CSS, JS, images
├── gymfit_project/    # Django project settings & URL config
└── manage.py
```

## Key URLs

| URL | Description |
|-----|-------------|
| `/` | Home page with featured plans |
| `/memberships/` | All coaching programs |
| `/memberships/<slug>/` | Program detail |
| `/memberships/<slug>/subscribe/` | Enrollment form |
| `/memberships/my/` | Trainee dashboard |
| `/memberships/my/<id>/` | Membership detail + chat |
| `/payments/history/` | Enrollment request history |
| `/accounts/login/` | Login |
| `/accounts/register/` | Register |
| `/admin/` | Coach/admin dashboard |

## Running Tests

```bash
python manage.py test
```

All 8 tests cover registration, home page, plan listing, subscription flow, and payment request tracking.

## Deployment

- Set `DJANGO_DEBUG=False` and configure `DJANGO_ALLOWED_HOSTS`.
- Run `python manage.py collectstatic` — WhiteNoise serves static files automatically.
- Use `DATABASE_URL` env var for PostgreSQL (Heroku, Railway, etc.).
- `Procfile` is included for Heroku: `web: gunicorn gymfit_project.wsgi`.
