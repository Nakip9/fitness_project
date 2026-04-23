from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from memberships.models import MembershipPlan

from .models import PaymentRequest


class PaymentRequestModelTests(TestCase):
    def setUp(self):
        self.plan = MembershipPlan.objects.create(
            name="Momentum",
            slug="momentum",
            price=79.0,
            duration_days=30,
        )
        self.user = get_user_model().objects.create_user(
            username="callback",
            email="callback@example.com",
            password="pass12345",
        )

    def test_string_representation_includes_phone_and_plan(self):
        request = PaymentRequest.objects.create(
            user=self.user,
            plan=self.plan,
            phone_number="+1 555 0199",
        )
        self.assertIn(self.plan.name, str(request))
        self.assertIn("+1 555 0199", str(request))
        self.assertEqual(request.status, "pending")

    def test_status_can_be_updated_when_contacted(self):
        request = PaymentRequest.objects.create(
            plan=self.plan,
            phone_number="+1 555 0200",
        )
        request.status = "contacted"
        request.save(update_fields=["status"])
        refreshed = PaymentRequest.objects.get(pk=request.pk)
        self.assertEqual(refreshed.status, "contacted")

    def test_history_view_requires_login_and_lists_requests(self):
        response = self.client.get(reverse("payments:history"))
        self.assertEqual(response.status_code, 302)
        self.client.login(username="callback", password="pass12345")
        PaymentRequest.objects.create(
            user=self.user,
            plan=self.plan,
            phone_number="+1 555 0222",
            status="contacted",
        )
        response = self.client.get(reverse("payments:history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "+1 555 0222")
