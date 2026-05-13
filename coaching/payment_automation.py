"""
Payment automation system for the Coaching Management System
Handles post-payment triggers and notifications
"""
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.db import transaction

from memberships.models import Membership
from payments.models import Payment
from .models import NotificationLog

logger = logging.getLogger(__name__)


class PaymentAutomationService:
    """
    Service class to handle payment automation workflows
    """
    
    @staticmethod
    def process_successful_payment(payment_id):
        """
        Process a successful payment and trigger all automation workflows
        """
        try:
            with transaction.atomic():
                payment = Payment.objects.select_related(
                    'user', 'plan', 'membership'
                ).get(id=payment_id)
                
                if payment.status != 'succeeded':
                    logger.warning(f"Payment {payment_id} is not in succeeded status")
                    return False
                
                # Activate the membership
                membership = payment.membership
                membership.status = 'active'
                membership.save(update_fields=['status'])
                
                # Generate and send confirmation email
                PaymentAutomationService._send_confirmation_email(payment)
                
                # Create notification log
                PaymentAutomationService._create_payment_notification(payment)
                
                # Schedule follow-up notifications
                PaymentAutomationService._schedule_follow_up_notifications(payment)
                
                logger.info(f"Successfully processed payment automation for payment {payment_id}")
                return True
                
        except Payment.DoesNotExist:
            logger.error(f"Payment {payment_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error processing payment automation for {payment_id}: {str(e)}")
            return False
    
    @staticmethod
    def _send_confirmation_email(payment):
        """
        Send confirmation email to the user
        """
        try:
            membership = payment.membership
            user = payment.user
            
            # Prepare email context
            context = {
                'user': user,
                'payment': payment,
                'membership': membership,
                'plan': payment.plan,
                'site_name': getattr(settings, 'SITE_NAME', 'Coach Jafri PT'),
                'amount_paid': payment.amount,
                'currency': payment.currency.upper(),
                'payment_date': payment.created_at,
                'membership_start': membership.start_date,
                'membership_end': membership.end_date,
                'days_remaining': membership.days_left,
            }
            
            # Render email templates
            subject = f"Payment Confirmation - {payment.plan.name} Membership"
            html_message = render_to_string('coaching/emails/payment_confirmation.html', context)
            plain_message = render_to_string('coaching/emails/payment_confirmation.txt', context)
            
            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Confirmation email sent to {user.email} for payment {payment.id}")
            
        except Exception as e:
            logger.error(f"Failed to send confirmation email for payment {payment.id}: {str(e)}")
    
    @staticmethod
    def _create_payment_notification(payment):
        """
        Create a notification log entry for the successful payment
        """
        try:
            NotificationLog.objects.create(
                user=payment.user,
                notification_type='payment_success',
                title='Payment Received',
                message=f'Your payment of {payment.currency.upper()} {payment.amount} for {payment.plan.name} has been successfully processed. Your membership is now active.',
                email_sent=True
            )
        except Exception as e:
            logger.error(f"Failed to create payment notification for payment {payment.id}: {str(e)}")
    
    @staticmethod
    def _schedule_follow_up_notifications(payment):
        """
        Schedule follow-up notifications for the membership
        """
        try:
            membership = payment.membership
            
            # Schedule membership expiring notification (7 days before expiry)
            if membership.end_date:
                expiry_reminder_date = membership.end_date - timezone.timedelta(days=7)
                if expiry_reminder_date > timezone.now():
                    # In a production system, you would use a task queue like Celery
                    # For now, we'll create a notification that can be processed by a cron job
                    NotificationLog.objects.create(
                        user=payment.user,
                        notification_type='membership_expiring',
                        title='Membership Expiring Soon',
                        message=f'Your {payment.plan.name} membership will expire on {membership.end_date.strftime("%Y-%m-%d")}. Renew now to continue your training.',
                        email_sent=False  # Will be sent by scheduled task
                    )
            
            # Schedule feedback request (after first session)
            NotificationLog.objects.create(
                user=payment.user,
                notification_type='feedback_request',
                title='How was your first session?',
                message='We hope you enjoyed your first training session! Please share your feedback to help us improve.',
                email_sent=False  # Will be sent after first session completion
            )
            
        except Exception as e:
            logger.error(f"Failed to schedule follow-up notifications for payment {payment.id}: {str(e)}")


class SessionNotificationService:
    """
    Service class to handle session-related notifications
    """
    
    @staticmethod
    def send_session_scheduled_notification(session):
        """
        Send notification when a session is scheduled
        """
        try:
            context = {
                'user': session.membership.user,
                'session': session,
                'coach': session.coach,
                'membership': session.membership,
                'site_name': getattr(settings, 'SITE_NAME', 'Coach Jafri PT'),
            }
            
            # Send email to trainee
            subject = f"Session Scheduled - {session.scheduled_start.strftime('%Y-%m-%d %H:%M')}"
            html_message = render_to_string('coaching/emails/session_scheduled.html', context)
            plain_message = render_to_string('coaching/emails/session_scheduled.txt', context)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[session.membership.user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            # Create notification log
            NotificationLog.objects.create(
                user=session.membership.user,
                notification_type='session_scheduled',
                title='Session Scheduled',
                message=f'Your training session with {session.coach.full_name} has been scheduled for {session.scheduled_start.strftime("%Y-%m-%d at %H:%M")}.',
                email_sent=True
            )
            
            logger.info(f"Session scheduled notification sent for session {session.id}")
            
        except Exception as e:
            logger.error(f"Failed to send session scheduled notification for session {session.id}: {str(e)}")
    
    @staticmethod
    def send_session_reminder(session):
        """
        Send reminder notification before session starts (typically 1 hour before)
        """
        try:
            context = {
                'user': session.membership.user,
                'session': session,
                'coach': session.coach,
                'membership': session.membership,
                'site_name': getattr(settings, 'SITE_NAME', 'Coach Jafri PT'),
            }
            
            subject = f"Session Reminder - Starting in 1 hour"
            html_message = render_to_string('coaching/emails/session_reminder.html', context)
            plain_message = render_to_string('coaching/emails/session_reminder.txt', context)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[session.membership.user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            # Create notification log
            NotificationLog.objects.create(
                user=session.membership.user,
                notification_type='session_reminder',
                title='Session Reminder',
                message=f'Your training session with {session.coach.full_name} starts in 1 hour at {session.scheduled_start.strftime("%H:%M")}.',
                email_sent=True
            )
            
            logger.info(f"Session reminder sent for session {session.id}")
            
        except Exception as e:
            logger.error(f"Failed to send session reminder for session {session.id}: {str(e)}")
    
    @staticmethod
    def send_session_cancelled_notification(session, reason=""):
        """
        Send notification when a session is cancelled
        """
        try:
            context = {
                'user': session.membership.user,
                'session': session,
                'coach': session.coach,
                'membership': session.membership,
                'reason': reason,
                'site_name': getattr(settings, 'SITE_NAME', 'Coach Jafri PT'),
            }
            
            subject = f"Session Cancelled - {session.scheduled_start.strftime('%Y-%m-%d %H:%M')}"
            html_message = render_to_string('coaching/emails/session_cancelled.html', context)
            plain_message = render_to_string('coaching/emails/session_cancelled.txt', context)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[session.membership.user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            # Create notification log
            message = f'Your training session scheduled for {session.scheduled_start.strftime("%Y-%m-%d at %H:%M")} has been cancelled.'
            if reason:
                message += f' Reason: {reason}'
            
            NotificationLog.objects.create(
                user=session.membership.user,
                notification_type='session_cancelled',
                title='Session Cancelled',
                message=message,
                email_sent=True
            )
            
            logger.info(f"Session cancelled notification sent for session {session.id}")
            
        except Exception as e:
            logger.error(f"Failed to send session cancelled notification for session {session.id}: {str(e)}")


# Webhook handler for Stripe payments
def handle_stripe_webhook(event):
    """
    Handle Stripe webhook events for payment automation
    """
    try:
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            payment_intent_id = payment_intent['id']
            
            # Find the payment record
            try:
                payment = Payment.objects.get(stripe_payment_intent=payment_intent_id)
                payment.status = 'succeeded'
                payment.save(update_fields=['status'])
                
                # Trigger payment automation
                PaymentAutomationService.process_successful_payment(payment.id)
                
                logger.info(f"Processed successful payment webhook for payment {payment.id}")
                
            except Payment.DoesNotExist:
                logger.warning(f"Payment not found for Stripe payment intent {payment_intent_id}")
        
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            payment_intent_id = payment_intent['id']
            
            try:
                payment = Payment.objects.get(stripe_payment_intent=payment_intent_id)
                payment.status = 'failed'
                payment.save(update_fields=['status'])
                
                # Create failure notification
                NotificationLog.objects.create(
                    user=payment.user,
                    notification_type='payment_failed',
                    title='Payment Failed',
                    message=f'Your payment for {payment.plan.name} could not be processed. Please try again or contact support.',
                    email_sent=False
                )
                
                logger.info(f"Processed failed payment webhook for payment {payment.id}")
                
            except Payment.DoesNotExist:
                logger.warning(f"Payment not found for Stripe payment intent {payment_intent_id}")
        
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {str(e)}")
        raise