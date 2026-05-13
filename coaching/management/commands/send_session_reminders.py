"""
Management command to send session reminders
Run this command hourly via cron job
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from coaching.models import CoachingSession, NotificationLog
from coaching.payment_automation import SessionNotificationService


class Command(BaseCommand):
    help = 'Send session reminders to trainees'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--hours-before',
            type=int,
            default=1,
            help='Hours before session to send reminder (default: 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending'
        )
    
    def handle(self, *args, **options):
        hours_before = options['hours_before']
        dry_run = options['dry_run']
        
        # Calculate the time window for reminders
        now = timezone.now()
        reminder_time_start = now + timedelta(hours=hours_before - 0.1)  # 6 minutes before
        reminder_time_end = now + timedelta(hours=hours_before + 0.1)    # 6 minutes after
        
        # Find sessions that need reminders
        sessions_needing_reminders = CoachingSession.objects.filter(
            status='scheduled',
            scheduled_start__gte=reminder_time_start,
            scheduled_start__lte=reminder_time_end
        ).select_related('membership__user', 'coach__user')
        
        # Filter out sessions that already have reminders sent
        sessions_to_remind = []
        for session in sessions_needing_reminders:
            existing_reminder = NotificationLog.objects.filter(
                user=session.membership.user,
                notification_type='session_reminder',
                created_at__gte=now - timedelta(hours=2),  # Check last 2 hours
                message__icontains=f'session {session.id}'
            ).exists()
            
            if not existing_reminder:
                sessions_to_remind.append(session)
        
        self.stdout.write(
            f"Found {len(sessions_to_remind)} sessions needing reminders "
            f"({hours_before} hour(s) before start time)"
        )
        
        if dry_run:
            for session in sessions_to_remind:
                self.stdout.write(
                    f"Would send reminder for: {session.membership.user.get_full_name()} "
                    f"- {session.scheduled_start.strftime('%Y-%m-%d %H:%M')}"
                )
            return
        
        # Send reminders
        sent_count = 0
        error_count = 0
        
        for session in sessions_to_remind:
            try:
                SessionNotificationService.send_session_reminder(session)
                sent_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Sent reminder for session {session.id} to {session.membership.user.email}"
                    )
                )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to send reminder for session {session.id}: {str(e)}"
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Completed: {sent_count} reminders sent, {error_count} errors"
            )
        )