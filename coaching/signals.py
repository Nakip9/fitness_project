"""
Django signals for the Coaching Management System
Handles automatic notifications and workflow triggers
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from payments.models import Payment
from .models import CoachingSession, NotificationLog
from .payment_automation import PaymentAutomationService, SessionNotificationService


@receiver(post_save, sender=Payment)
def handle_payment_success(sender, instance, created, **kwargs):
    """
    Handle successful payment and trigger automation workflows
    """
    if instance.status == 'succeeded' and not created:
        # Payment status changed to succeeded
        PaymentAutomationService.process_successful_payment(instance.id)


@receiver(post_save, sender=CoachingSession)
def handle_session_created(sender, instance, created, **kwargs):
    """
    Handle new session creation and send notifications
    """
    if created and instance.status == 'scheduled':
        # Send session scheduled notification
        SessionNotificationService.send_session_scheduled_notification(instance)


@receiver(pre_save, sender=CoachingSession)
def handle_session_status_change(sender, instance, **kwargs):
    """
    Handle session status changes and send appropriate notifications
    """
    if instance.pk:  # Only for existing sessions
        try:
            old_instance = CoachingSession.objects.get(pk=instance.pk)
            
            # Check if status changed to cancelled
            if (old_instance.status != 'cancelled' and 
                instance.status == 'cancelled'):
                # Send cancellation notification after save
                def send_cancellation_notification():
                    SessionNotificationService.send_session_cancelled_notification(
                        instance, 
                        reason=getattr(instance, '_cancellation_reason', '')
                    )
                
                # Store the function to call after save
                instance._send_cancellation_notification = send_cancellation_notification
            
            # Check if session was rescheduled
            if (old_instance.scheduled_start != instance.scheduled_start or
                old_instance.scheduled_end != instance.scheduled_end):
                # Send rescheduled notification after save
                def send_reschedule_notification():
                    NotificationLog.objects.create(
                        user=instance.membership.user,
                        notification_type='session_rescheduled',
                        title='Session Rescheduled',
                        message=f'Your session has been rescheduled to {instance.scheduled_start.strftime("%Y-%m-%d at %H:%M")}'
                    )
                
                instance._send_reschedule_notification = send_reschedule_notification
                
        except CoachingSession.DoesNotExist:
            pass


@receiver(post_save, sender=CoachingSession)
def handle_session_post_save_notifications(sender, instance, created, **kwargs):
    """
    Send notifications that were queued in pre_save signal
    """
    if hasattr(instance, '_send_cancellation_notification'):
        instance._send_cancellation_notification()
        delattr(instance, '_send_cancellation_notification')
    
    if hasattr(instance, '_send_reschedule_notification'):
        instance._send_reschedule_notification()
        delattr(instance, '_send_reschedule_notification')
    
    # Handle session completion
    if not created and instance.status == 'completed':
        # Create feedback request notification
        NotificationLog.objects.get_or_create(
            user=instance.membership.user,
            notification_type='feedback_request',
            defaults={
                'title': 'How was your session?',
                'message': f'Please share your feedback about your session with {instance.coach.full_name}.',
                'email_sent': False
            }
        )