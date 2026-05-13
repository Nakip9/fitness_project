import os
import requests
import logging
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

@receiver(post_save, sender="payments.Payment")
def handle_payment_succeeded(sender, instance, **kwargs):
    """Activate membership and call EmailJS when a payment succeeds."""
    if instance.status != "succeeded":
        return

    membership = instance.membership
    user = instance.user

    # 1. Activate the membership (only if it was pending)
    if membership.status == "pending":
        membership.status = "active"
        membership.save(update_fields=["status"])

    # 2. EmailJS API Integration
    service_id = os.getenv('EMAILJS_SERVICE_ID')
    template_id = os.getenv('EMAILJS_TEMPLATE_ID')
    public_key = os.getenv('EMAILJS_PUBLIC_KEY')
    private_key = os.getenv('EMAILJS_PRIVATE_KEY')

    if not all([service_id, template_id, public_key]):
        logger.warning("EmailJS keys missing in environment. Email not sent.")
        return

    url = "https://api.emailjs.com/api/v1.0/email/send"
    
    data = {
        'service_id': service_id,
        'template_id': template_id,
        'user_id': public_key,
        'accessToken': private_key,  # Added Private Key for security
        'template_params': {
            'to_name': user.get_full_name() or user.username,
            'to_email': user.email,
            'plan_name': membership.plan.name,
            'time_slot': membership.time_slot,
            'days_left': str(membership.days_left),
            'expiry_date': membership.end_date.strftime('%B %d, %Y'),
            'coach_notes': membership.coach_notes or "Check your dashboard for details.",
            'dashboard_url': f"{getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')}/memberships/my/{membership.pk}/"
        }
    }

    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            logger.info(f"Email successfully sent via EmailJS to {user.email}")
        else:
            logger.error(f"EmailJS Error: {response.status_code} - {response.text}")
    except Exception as exc:
        logger.error(f"Failed to connect to EmailJS for {user.email}: {exc}")
