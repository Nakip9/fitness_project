from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class MembershipPlan(models.Model):
    BILLING_CYCLE_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("yearly", "Yearly"),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.PositiveIntegerField(default=30)
    billing_cycle = models.CharField(
        max_length=20, choices=BILLING_CYCLE_CHOICES, default="monthly"
    )
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["price"]

    def __str__(self) -> str:
        return self.name

    @property
    def duration(self) -> timedelta:
        return timedelta(days=self.duration_days)


class MembershipBenefit(models.Model):
    plan = models.ForeignKey(
        MembershipPlan, related_name="benefits", on_delete=models.CASCADE
    )
    text = models.CharField(max_length=255)
    highlight = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.text} ({self.plan})"


class Membership(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("expired", "Expired"),
        ("canceled", "Canceled"),
        ("postponed", "Postponed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    auto_renew = models.BooleanField(default=True)

    # Scheduling fields
    scheduled_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="The daily session start time (date portion is ignored; only time matters).",
    )
    duration_minutes = models.PositiveIntegerField(
        default=60,
        help_text="Session length in minutes.",
    )
    coach_notes = models.TextField(
        blank=True,
        help_text="Permanent instructions from the coach — always visible to the trainee.",
    )

    # Postpone support: stores remaining days at the moment of postponement
    postponed_remaining_days = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Days remaining when the membership was postponed. Used to restore the countdown on re-activation.",
    )

    class Meta:
        ordering = ["-start_date"]
        unique_together = ("user", "plan", "start_date")

    def __str__(self) -> str:
        return f"{self.user} — {self.plan} [{self.get_status_display()}]"

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def scheduled_end_time(self):
        """Return the session end datetime (start + duration_minutes)."""
        if self.scheduled_time:
            return self.scheduled_time + timedelta(minutes=self.duration_minutes)
        return None

    @property
    def time_slot(self) -> str:
        """Human-readable session window, e.g. '03:00 PM – 04:00 PM'."""
        if self.scheduled_time:
            end = self.scheduled_end_time
            return (
                f"{self.scheduled_time.strftime('%I:%M %p')} – "
                f"{end.strftime('%I:%M %p')}"
            )
        return "Not Scheduled"

    @property
    def is_active(self) -> bool:
        if self.status != "active":
            return False
        return self.end_date is not None and self.end_date >= timezone.now()

    @property
    def days_left(self) -> int:
        """
        Live days remaining.
        - Active: calculated from end_date.
        - Postponed: returns the frozen value stored at postponement time.
        - Anything else: 0.
        """
        if self.status == "postponed" and self.postponed_remaining_days is not None:
            return self.postponed_remaining_days
        if self.status == "active" and self.end_date:
            delta = self.end_date - timezone.now()
            return max(0, delta.days)
        return 0

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def cancel(self):
        """
        Cancel the membership.  Freezes the countdown by clearing end_date
        so no further time elapses against the subscription.
        """
        self.status = "canceled"
        # Preserve end_date for audit purposes but mark as canceled.
        # The is_active property already gates on status, so the countdown
        # is effectively stopped.
        self.save(update_fields=["status"])

    def postpone(self):
        """
        Postpone the membership.
        - Freezes the remaining days counter.
        - Clears scheduled_time so the session window is hidden from the client
          until the coach assigns a new time.
        """
        if self.status not in ("active", "pending"):
            raise ValidationError("Only active or pending memberships can be postponed.")
        self.postponed_remaining_days = self.days_left
        self.scheduled_time = None  # Hide session window until re-scheduled
        self.status = "postponed"
        self.save(update_fields=["status", "postponed_remaining_days", "scheduled_time"])

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        """
        Hard conflict prevention: no two *active* memberships may share an
        overlapping session window.

        The check is intentionally limited to Active memberships so that
        Pending / Postponed / Canceled records do not block scheduling.
        """
        if not self.scheduled_time:
            return  # Nothing to validate without a scheduled time

        my_start = self.scheduled_time
        my_end = self.scheduled_end_time  # always set when scheduled_time is set

        # Only check against Active memberships (excluding self on edit)
        conflicting_qs = Membership.objects.filter(
            status="active",
            scheduled_time__isnull=False,
        ).exclude(pk=self.pk)

        for other in conflicting_qs:
            other_start = other.scheduled_time
            other_end = other.scheduled_end_time

            if other_end is None:
                continue

            # Overlap condition: two intervals [A,B) and [C,D) overlap when A < D and C < B
            if my_start < other_end and other_start < my_end:
                raise ValidationError(
                    f"Schedule conflict: This time slot ({my_start.strftime('%I:%M %p')} – "
                    f"{my_end.strftime('%I:%M %p')}) overlaps with "
                    f"trainee '{other.user.get_full_name() or other.user.username}' "
                    f"(#{other.pk}) whose session runs "
                    f"{other_start.strftime('%I:%M %p')} – {other_end.strftime('%I:%M %p')}."
                )

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self, *args, **kwargs):
        # Auto-calculate end_date on first save
        if not self.end_date and self.plan_id:
            self.end_date = self.start_date + self.plan.duration
        super().save(*args, **kwargs)


class MembershipNote(models.Model):
    membership = models.ForeignKey(
        Membership, on_delete=models.CASCADE, related_name="notes"
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Note by {self.author} on {self.membership}"
