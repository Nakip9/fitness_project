from django.conf import settings
from django.db import models
from memberships.models import Membership, TrainingPlan

class ManualPaymentLog(models.Model):
    """Requirement 5: Log manual payments tracked by admins."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="manual_payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Reference for bank transfer, cash receipt, etc.")

    def __str__(self):
        return f"Payment for {self.membership} - {self.amount}"
