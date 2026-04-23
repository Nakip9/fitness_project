from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

class TrainingPlan(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price_cents = models.PositiveIntegerField(help_text="Price in cents (e.g., 5000 for $50.00)")
    duration_days = models.PositiveIntegerField()
    featured = models.BooleanField(default=False)

    @property
    def price_display(self):
        return f"{self.price_cents / 100:.2f}"

    def __str__(self):
        return self.name

class Membership(models.Model):
    class Status(models.TextChoices):
        REQUESTED = 'REQUESTED', 'Pending Review'
        APPROVED = 'APPROVED', 'Approved (Pending Payment)'
        ACTIVE = 'ACTIVE', 'Active Coaching'
        PAUSED = 'PAUSED', 'Paused'
        POSTPONED = 'POSTPONED', 'Postponed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        COMPLETED = 'COMPLETED', 'Completed'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'UNPAID', 'Unpaid'
        PAID = 'PAID', 'Paid'
        REFUNDED = 'REFUNDED', 'Refunded'

    trainee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='training_requests')
    coach = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='trainee_roster')
    plan = models.ForeignKey(TrainingPlan, on_delete=models.PROTECT)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    
    # Scheduling fields (Using discrete fields for compatibility while maintaining logic)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def days_remaining(self):
        """Requirement: Real-time countdown for the trainee."""
        if self.status != self.Status.ACTIVE or not self.scheduled_end:
            return 0
        
        now = timezone.now()
        if now > self.scheduled_end:
            return 0
            
        delta = self.scheduled_end - now
        # Add 1 to include today
        return delta.days + 1

    def __str__(self):
        return f"{self.trainee.username} - {self.plan.name} ({self.get_status_display()})"

    def clean(self):
        """Requirement 1: Conflict Prevention Logic."""
        if self.status in [self.Status.APPROVED, self.Status.ACTIVE] and self.coach and self.scheduled_start and self.scheduled_end:
            # Check for overlaps
            overlaps = Membership.objects.filter(
                coach=self.coach,
                status__in=[self.Status.APPROVED, self.Status.ACTIVE],
                scheduled_start__lt=self.scheduled_end,
                scheduled_end__gt=self.scheduled_start
            ).exclude(pk=self.pk)
            
            if overlaps.exists():
                other = overlaps.first()
                raise ValidationError(
                    f"Schedule Conflict: Coach {self.coach.get_full_name()} is already booked with {other.trainee.get_full_name()} "
                    f"from {other.scheduled_start.strftime('%H:%M')} to {other.scheduled_end.strftime('%H:%M')}."
                )

class MembershipNote(models.Model):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name='comms_hub')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    is_pinned = models.BooleanField(default=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_pinned', 'created_at']

class AuditLog(models.Model):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name='audit_trail')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    old_state = models.JSONField(null=True)
    new_state = models.JSONField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
