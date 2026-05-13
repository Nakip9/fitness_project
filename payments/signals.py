import os
import requests
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PaymentRequest

logger = logging.getLogger(__name__)

@receiver(post_save, sender=PaymentRequest)
def notify_new_request(sender, instance, created, **kwargs):
    """Notify coach and trainee when a new membership request is submitted."""
    if not created:
        return

    # EmailJS Keys
    service_id = os.getenv('EMAILJS_SERVICE_ID')
    template_id = os.getenv('EMAILJS_TEMPLATE_ID')
    public_key = os.getenv('EMAILJS_PUBLIC_KEY')
    private_key = os.getenv('EMAILJS_PRIVATE_KEY')

    if not all([service_id, template_id, public_key]):
        return

    url = "https://api.emailjs.com/api/v1.0/email/send"
    
    # Send notification to Trainee
    data = {
        'service_id': service_id,
        'template_id': template_id,
        'user_id': public_key,
        'accessToken': private_key,
        'template_params': {
            'to_name': instance.user.get_full_name() or instance.user.username,
            'to_email': instance.user.email,
            'plan_name': instance.plan.name,
            'coach_notes': "We have received your request! Coach Jafri will review it and assign your time slot shortly.",
            'time_slot': "Awaiting Approval",
            'days_left': "Pending",
            'expiry_date': "TBD",
            'dashboard_url': "http://127.0.0.1:8000/memberships/my/"
        }
    }

    try:
        requests.post(url, json=data)
        logger.info(f"Request confirmation sent to {instance.user.email}")
    except Exception as e:
        logger.error(f"Failed to send request email: {e}")
