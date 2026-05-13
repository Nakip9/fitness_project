"""
Management command to process membership expirations and send notifications
Run this command daily via cron job
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from memberships.models import Membership
from coaching.models import NotificationLog


class Command(BaseCommand):
    help = 'Process membership expirations and send notifications'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--warning-days',
            type=int,
            default=7,
            help='Days before expiration to send warning (default: 7)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually processing'
        )
    
    def handle(self, *args, **options):
        warning_days = options['warning_days']
        dry_run = options['dry_run']
        
        now = timezone.now()
        warning_date = now + timedelta(days=warning_days)
        
        # Find memberships expiring soon
        expiring_memberships = Membership.objects.filter(
            status='active',
            end_date__lte=warning_date,
            end_date__gt=now
        ).select_related('user', 'plan')
        
        # Find memberships that have already expired
        expired_memberships = Membership.objects.filter(
            status='active',
            end_date__lte=now
        ).select_related('user', 'plan')
        
        self.stdout.write(
            f"Found {expiring_memberships.count()} memberships expiring within {warning_days} days"
        )
        self.stdout.write(
            f"Found {expired_memberships.count()} memberships that have expired"
        )
        
        if dry_run:
            for membership in expiring_memberships:
                days_left = (membership.end_date - now).days
                self.stdout.write(
                    f"Would send expiration warning: {membership.user.get_full_name()} "
                    f"- {membership.plan.name} (expires in {days_left} days)"
                )
            
            for membership in expired_memberships:
                self.stdout.write(
                    f"Would expire membership: {membership.user.get_full_name()} "
                    f"- {membership.plan.name} (expired {membership.end_date})"
                )
            return
        
        # Process expiring memberships
        warning_sent = 0
        for membership in expiring_memberships:
            # Check if warning already sent
            existing_warning = NotificationLog.objects.filter(
                user=membership.user,
                notification_type='membership_expiring',
                created_at__gte=now - timedelta(days=1)  # Check last 24 hours
            ).exists()
            
            if not existing_warning:
                try:
                    days_left = (membership.end_date - now).days
                    
                    # Create notification
                    NotificationLog.objects.create(
                        user=membership.user,
                        notification_type='membership_expiring',
                        title='Membership Expiring Soon',
                        message=f'Your {membership.plan.name} membership will expire in {days_left} days on {membership.end_date.strftime("%Y-%m-%d")}. Renew now to continue your training.',
                        email_sent=True
                    )
                    
                    # Send email
                    send_mail(
                        subject=f'Membership Expiring Soon - {membership.plan.name}',
                        message=f'Hello {membership.user.get_full_name()},\n\nYour {membership.plan.name} membership will expire in {days_left} days on {membership.end_date.strftime("%B %d, %Y")}.\n\nTo continue your training without interruption, please renew your membership before the expiration date.\n\nThank you,\n{getattr(settings, "SITE_NAME", "Coach Jafri PT")}',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[membership.user.email],
                        fail_silently=False
                    )
                    
                    warning_sent += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Sent expiration warning to {membership.user.email} "
                            f"for {membership.plan.name} (expires in {days_left} days)"
                        )
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Failed to send expiration warning for membership {membership.id}: {str(e)}"
                        )
                    )
        
        # Process expired memberships
        expired_count = 0
        for membership in expired_memberships:
            try:
                membership.status = 'expired'
                membership.save(update_fields=['status'])
                
                # Create notification
                NotificationLog.objects.create(
                    user=membership.user,
                    notification_type='membership_expired',
                    title='Membership Expired',
                    message=f'Your {membership.plan.name} membership has expired. Please renew to continue your training.',
                    email_sent=False  # Will be sent by separate process
                )
                
                expired_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Expired membership: {membership.user.get_full_name()} "
                        f"- {membership.plan.name}"
                    )
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to expire membership {membership.id}: {str(e)}"
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Completed: {warning_sent} warnings sent, {expired_count} memberships expired"
            )
        )