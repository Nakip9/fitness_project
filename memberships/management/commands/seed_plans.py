"""
Management command: python manage.py seed_plans

Creates three default personal-training coaching plans with benefits.
Safe to run multiple times — uses get_or_create so it won't duplicate.
"""
from django.core.management.base import BaseCommand
from memberships.models import MembershipBenefit, MembershipPlan


PLANS = [
    {
        "name": "Starter Coaching",
        "slug": "starter-coaching",
        "description": (
            "Perfect for beginners who want a structured entry into fitness. "
            "You'll receive a custom 4-week training plan, basic nutrition guidelines, "
            "and weekly check-ins to keep you on track."
        ),
        "price": "99.00",
        "duration_days": 30,
        "billing_cycle": "monthly",
        "is_active": True,
        "featured": False,
        "benefits": [
            ("Custom 4-week training plan", False),
            ("Basic nutrition & macro guide", False),
            ("Weekly progress check-in", False),
            ("Access to coaching app", False),
            ("Email support (48h response)", False),
        ],
    },
    {
        "name": "Elite 1-on-1 Coaching",
        "slug": "elite-coaching",
        "description": (
            "Our most popular program. Fully personalised training and nutrition, "
            "direct WhatsApp access to Coach Jafri, video form reviews, and bi-weekly "
            "strategy calls to maximise your results."
        ),
        "price": "249.00",
        "duration_days": 30,
        "billing_cycle": "monthly",
        "is_active": True,
        "featured": True,
        "benefits": [
            ("Fully custom training program", True),
            ("Personalised nutrition & meal plan", True),
            ("Direct WhatsApp coach access", True),
            ("Video form analysis & feedback", True),
            ("Bi-weekly strategy calls", False),
            ("Progress tracking dashboard", False),
            ("Priority 2-hour response time", False),
        ],
    },
    {
        "name": "90-Day Transformation",
        "slug": "90-day-transformation",
        "description": (
            "A complete 3-month body-transformation package. Includes periodised "
            "programming, full nutrition overhaul, supplement guidance, and monthly "
            "body-composition assessments to ensure you hit your goals."
        ),
        "price": "599.00",
        "duration_days": 90,
        "billing_cycle": "quarterly",
        "is_active": True,
        "featured": False,
        "benefits": [
            ("3-month periodised training plan", False),
            ("Full nutrition & supplement guide", False),
            ("Monthly body-composition review", False),
            ("Unlimited messaging support", False),
            ("Video form analysis (unlimited)", False),
            ("Monthly 1-on-1 strategy call", False),
            ("Transformation photo tracking", False),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the database with default personal-training coaching plans."

    def handle(self, *args, **options):
        created_count = 0
        for plan_data in PLANS:
            benefits = plan_data.pop("benefits")
            plan, created = MembershipPlan.objects.get_or_create(
                slug=plan_data["slug"],
                defaults=plan_data,
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ Created plan: {plan.name}"))
                for text, highlight in benefits:
                    MembershipBenefit.objects.create(
                        plan=plan, text=text, highlight=highlight
                    )
            else:
                self.stdout.write(f"  — Plan already exists: {plan.name}")
            # Re-add the benefits key so the dict is intact for future runs
            plan_data["benefits"] = benefits

        if created_count:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Done! {created_count} coaching plan(s) created."
                )
            )
        else:
            self.stdout.write("\nAll plans already exist — nothing to do.")
