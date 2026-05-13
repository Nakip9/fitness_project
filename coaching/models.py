"""
Enhanced Coaching Management System Models
Builds upon the existing memberships app structure
"""
from datetime import datetime, timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from memberships.models import Membership, MembershipPlan


class Coach(models.Model):
    """
    Coach profile extending the User model
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='coach_profile'
    )
    specialization = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    max_daily_sessions = models.PositiveIntegerField(default=8)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['user__first_name', 'user__last_name']
    
    def __str__(self):
        return f"Coach {self.user.get_full_name() or self.user.username}"
    
    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username
    
    def get_availability_for_date(self, date):
        """Get coach availability for a specific date"""
        day_name = date.strftime('%A').lower()
        return self.availability_slots.filter(
            day_of_week=day_name,
            is_active=True
        )
    
    def is_available_at(self, start_time, end_time):
        """Check if coach is available during the specified time slot"""
        # Check availability slots
        day_name = start_time.strftime('%A').lower()
        availability = self.availability_slots.filter(
            day_of_week=day_name,
            is_active=True,
            start_time__lte=start_time.time(),
            end_time__gte=end_time.time()
        ).exists()
        
        if not availability:
            return False
        
        # Check for conflicting sessions
        conflicting_sessions = CoachingSession.objects.filter(
            coach=self,
            status__in=['scheduled', 'in_progress'],
            scheduled_start__lt=end_time,
            scheduled_end__gt=start_time
        ).exists()
        
        return not conflicting_sessions


class CoachAvailability(models.Model):
    """
    Coach availability schedule
    """
    DAYS_OF_WEEK = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    coach = models.ForeignKey(
        Coach, 
        on_delete=models.CASCADE,
        related_name='availability_slots'
    )
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['day_of_week', 'start_time']
        unique_together = ['coach', 'day_of_week', 'start_time', 'end_time']
    
    def __str__(self):
        return f"{self.coach} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"
    
    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time")


class CoachingSession(models.Model):
    """
    Individual coaching sessions
    """
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
    ]
    
    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name='coaching_sessions'
    )
    coach = models.ForeignKey(
        Coach,
        on_delete=models.PROTECT,
        related_name='sessions'
    )
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    actual_start = models.DateTimeField(blank=True, null=True)
    actual_end = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    session_notes = models.TextField(blank=True, help_text="Session plan and objectives")
    coach_feedback = models.TextField(blank=True, help_text="Post-session feedback from coach")
    trainee_feedback = models.TextField(blank=True, help_text="Feedback from trainee")
    rating = models.PositiveIntegerField(
        blank=True, 
        null=True,
        help_text="Session rating (1-5)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_start']
    
    def __str__(self):
        return f"Session: {self.membership.user.get_full_name()} with {self.coach} on {self.scheduled_start.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def duration_minutes(self):
        """Calculate session duration in minutes"""
        if self.actual_start and self.actual_end:
            return int((self.actual_end - self.actual_start).total_seconds() / 60)
        return int((self.scheduled_end - self.scheduled_start).total_seconds() / 60)
    
    @property
    def is_past_due(self):
        """Check if session is past its scheduled time"""
        return timezone.now() > self.scheduled_end
    
    def clean(self):
        """
        Validate session scheduling to prevent conflicts
        """
        if self.scheduled_start >= self.scheduled_end:
            raise ValidationError("Session start time must be before end time")
        
        # Check for coach availability
        if not self.coach.is_available_at(self.scheduled_start, self.scheduled_end):
            raise ValidationError(
                f"Coach {self.coach} is not available during the requested time slot"
            )
        
        # Check for overlapping sessions (excluding self on update)
        overlapping_sessions = CoachingSession.objects.filter(
            coach=self.coach,
            status__in=['scheduled', 'confirmed', 'in_progress'],
            scheduled_start__lt=self.scheduled_end,
            scheduled_end__gt=self.scheduled_start
        ).exclude(pk=self.pk)
        
        if overlapping_sessions.exists():
            conflicting_session = overlapping_sessions.first()
            raise ValidationError(
                f"Schedule conflict: Coach {self.coach} already has a session "
                f"from {conflicting_session.scheduled_start.strftime('%H:%M')} "
                f"to {conflicting_session.scheduled_end.strftime('%H:%M')} "
                f"with {conflicting_session.membership.user.get_full_name()}"
            )
    
    def check_in(self):
        """Mark session as started"""
        self.actual_start = timezone.now()
        self.status = 'in_progress'
        self.save(update_fields=['actual_start', 'status'])
    
    def check_out(self):
        """Mark session as completed"""
        self.actual_end = timezone.now()
        self.status = 'completed'
        self.save(update_fields=['actual_end', 'status'])
    
    def cancel(self, reason=""):
        """Cancel the session"""
        self.status = 'cancelled'
        if reason:
            self.session_notes = f"Cancelled: {reason}"
        self.save(update_fields=['status', 'session_notes'])
    
    def reschedule(self, new_start, new_end):
        """Reschedule the session to a new time"""
        # Validate new time slot
        temp_session = CoachingSession(
            coach=self.coach,
            scheduled_start=new_start,
            scheduled_end=new_end
        )
        temp_session.clean()  # This will raise ValidationError if conflicts exist
        
        # Update the session
        self.scheduled_start = new_start
        self.scheduled_end = new_end
        self.status = 'scheduled'
        self.save(update_fields=['scheduled_start', 'scheduled_end', 'status'])


class SessionAttendance(models.Model):
    """
    Track session attendance and check-in/out times
    """
    ATTENDANCE_STATUS = [
        ('present', 'Present'),
        ('late', 'Late'),
        ('absent', 'Absent'),
        ('excused', 'Excused'),
    ]
    
    session = models.OneToOneField(
        CoachingSession,
        on_delete=models.CASCADE,
        related_name='attendance'
    )
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS, default='present')
    check_in_time = models.DateTimeField(blank=True, null=True)
    check_out_time = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Attendance: {self.session} - {self.get_status_display()}"
    
    @property
    def was_late(self):
        """Check if trainee was late"""
        if self.check_in_time and self.session.scheduled_start:
            return self.check_in_time > self.session.scheduled_start
        return False
    
    @property
    def minutes_late(self):
        """Calculate how many minutes late the trainee was"""
        if self.was_late:
            return int((self.check_in_time - self.session.scheduled_start).total_seconds() / 60)
        return 0


class SessionFeedback(models.Model):
    """
    Bi-directional feedback system for sessions
    """
    session = models.ForeignKey(
        CoachingSession,
        on_delete=models.CASCADE,
        related_name='feedback_entries'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    content = models.TextField()
    rating = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Rating from 1-5"
    )
    is_coach_feedback = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        feedback_type = "Coach" if self.is_coach_feedback else "Trainee"
        return f"{feedback_type} feedback for {self.session}"


# Enhanced MembershipNote model (extends existing)
class EnhancedMembershipNote(models.Model):
    """
    Enhanced note system with threading and pinning capabilities
    """
    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name='enhanced_notes'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    content = models.TextField()
    is_pinned = models.BooleanField(default=False, help_text="Pinned notes appear at the top")
    parent_note = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='replies'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
    
    def __str__(self):
        note_type = "Pinned Note" if self.is_pinned else "Note"
        if self.parent_note:
            note_type = "Reply"
        return f"{note_type} by {self.author} on {self.membership}"
    
    @property
    def is_coach_note(self):
        """Check if note was written by a coach"""
        return self.author.is_staff or hasattr(self.author, 'coach_profile')
    
    def pin(self):
        """Pin this note"""
        self.is_pinned = True
        self.save(update_fields=['is_pinned'])
    
    def unpin(self):
        """Unpin this note"""
        self.is_pinned = False
        self.save(update_fields=['is_pinned'])


class NotificationLog(models.Model):
    """
    Track all notifications sent to users
    """
    NOTIFICATION_TYPES = [
        ('payment_success', 'Payment Success'),
        ('session_scheduled', 'Session Scheduled'),
        ('session_reminder', 'Session Reminder'),
        ('session_cancelled', 'Session Cancelled'),
        ('session_rescheduled', 'Session Rescheduled'),
        ('membership_expiring', 'Membership Expiring'),
        ('feedback_request', 'Feedback Request'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    email_sent = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.user}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])