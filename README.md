# Gymfit Django + Bootstrap Starter

This project integrates the [Gymfit Bootstrap template](https://github.com/themefisher/gymfit-bootstrap) with a Django backend. It delivers membership management, class scheduling, and Stripe-ready payments in a production-friendly structure.

## Features

- Django 4 project with modular apps for accounts, memberships, schedules, and payments.
- Authentication with registration and login screens styled to match the Gymfit theme.
- Membership plans with benefits, subscription workflow, and member dashboard.
- Class scheduling with category filtering, booking, and waitlist handling.
- Stripe Checkout integration (with graceful fallback when API keys are not configured).
- Responsive UI built on the Gymfit aesthetic, including hero sections, pricing cards, and schedule previews.

## Getting Started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment variables**

   Copy `.env.example` to `.env` (create the file if it does not exist) and supply the following values:

   ```env
   DJANGO_SECRET_KEY=change-me
   DJANGO_DEBUG=True
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
   STRIPE_SECRET_KEY=sk_test_your_key
   STRIPE_PUBLISHABLE_KEY=pk_test_your_key
   SITE_NAME=JafriFit
   SITE_TAGLINE=Fuel Your Energy. Elevate Your Strength.
   ```

   When Stripe keys are not provided the app activates memberships automatically, making local testing straightforward.

3. **Run migrations and start the dev server**

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

   Visit `http://127.0.0.1:8000/` to see the Gymfit home page.

4. **Create a superuser (optional)**

   ```bash
   python manage.py createsuperuser
   ```

## Payments

- `/payments/<slug:plan>/create/` starts a Stripe Checkout session for the specified membership plan.
- Success and cancel callbacks update the local `Payment` and `Membership` records.
- Configure webhook endpoints separately if you require server-to-server confirmations.

## Deployment Notes

- Set `DJANGO_DEBUG=False` and define `DJANGO_ALLOWED_HOSTS` for your production domain.
- Collect static assets with `python manage.py collectstatic` and ensure the `staticfiles/` directory is served by your platform (e.g., WhiteNoise on Heroku or S3/CloudFront on AWS).
- Supply production Stripe keys through environment variables.
- For Heroku deployment, add the `python-3.11` runtime, set config vars, and use a production-ready database such as Heroku Postgres.

## Project Structure

```
full_dj_bs/
├── accounts/              # Authentication views and forms
├── core/                  # Marketing pages and context processors
├── memberships/           # Membership plans, benefits, and subscriptions
├── payments/              # Stripe integration and payment records
├── schedules/             # Class scheduling and booking
├── templates/             # Gymfit-inspired HTML templates
├── static/                # CSS and JS assets adapted from Gymfit
├── gymfit_project/        # Django project configuration
└── manage.py
```

## Testing

Run the Django test suite:

```bash
python manage.py test
```

The included tests cover core flows such as registration, membership subscription, booking, and payment fallbacks.
