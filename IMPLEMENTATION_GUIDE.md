# Coaching Management System - Implementation Guide

## Overview

This implementation provides a comprehensive Coaching Management System that builds upon your existing Django project structure. The system includes automated conflict prevention, trainee transparency, dynamic lifecycle management, transactional automation, and interactive feedback loops.

## Installation Steps

### 1. Add the Coaching App to Settings

Update your `gymfit_project/settings.py`:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "rest_framework",  # Add this
    "core",
    "accounts",
    "memberships",
    "payments",
    "coaching",  # Add this
]

# Add REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# Email configuration for notifications
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@example.com')
```

### 2. Install Required Dependencies

Add to your `requirements.txt`:

```
djangorestframework>=3.14.0
```

Then install:

```bash
pip install djangorestframework
```

### 3. Update URL Configuration

Update `gymfit_project/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("memberships/", include("memberships.urls")),
    path("payments/", include("payments.urls")),
    path("coaching/", include("coaching.urls")),  # Add this
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### 4. Create and Run Migrations

```bash
python manage.py makemigrations coaching
python manage.py migrate
```

### 5. Create Coach Profiles

You'll need to create Coach profiles for users who will be coaches. You can do this through the Django admin or create a management command:

```python
# coaching/management/commands/create_coach_profiles.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from coaching.models import Coach

User = get_user_model()

class Command(BaseCommand):
    help = 'Create coach profiles for staff users'
    
    def handle(self, *args, **options):
        staff_users = User.objects.filter(is_staff=True)
        
        for user in staff_users:
            coach, created = Coach.objects.get_or_create(
                user=user,
                defaults={
                    'specialization': 'Personal Training',
                    'hourly_rate': 50.00,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created coach profile for {user.get_full_name()}')
                )
            else:
                self.stdout.write(f'Coach profile already exists for {user.get_full_name()}')
```

### 6. Set Up Cron Jobs for Automated Tasks

Add these to your crontab (`crontab -e`):

```bash
# Send session reminders every hour
0 * * * * /path/to/your/venv/bin/python /path/to/your/project/manage.py send_session_reminders

# Process membership expirations daily at 9 AM
0 9 * * * /path/to/your/venv/bin/python /path/to/your/project/manage.py process_membership_expirations
```

### 7. Configure Stripe Webhooks (Optional)

If you want to use Stripe webhooks for payment automation, add this to your `payments/views.py`:

```python
import stripe
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from coaching.payment_automation import handle_stripe_webhook

@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        handle_stripe_webhook(event)
        return HttpResponse(status=200)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
```

## API Usage Examples

### 1. Check Schedule Conflicts

```javascript
// Check if a time slot is available
fetch('/coaching/api/sessions/check-conflict/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({
        coach_id: 1,
        start_time: '2024-03-15T10:00:00Z',
        end_time: '2024-03-15T11:00:00Z'
    })
})
.then(response => response.json())
.then(data => {
    if (data.is_available) {
        console.log('Time slot is available');
    } else {
        console.log('Conflicts:', data.conflicts);
    }
});
```

### 2. Schedule a Session

```javascript
// Schedule a new coaching session
fetch('/coaching/api/sessions/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({
        membership_id: 1,
        coach_id: 1,
        scheduled_start: '2024-03-15T10:00:00Z',
        scheduled_end: '2024-03-15T11:00:00Z',
        session_notes: 'Focus on upper body strength training'
    })
})
.then(response => response.json())
.then(data => {
    console.log('Session scheduled:', data);
});
```

### 3. Get User's Sessions

```javascript
// Get all sessions for the current user
fetch('/coaching/api/sessions/')
.then(response => response.json())
.then(data => {
    console.log('User sessions:', data.results);
});
```

### 4. Add Membership Note

```javascript
// Add a note to a membership
fetch('/coaching/api/memberships/1/notes/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({
        content: 'Great progress on squats today!',
        is_pinned: false
    })
})
.then(response => response.json())
.then(data => {
    console.log('Note added:', data);
});
```

## Key Features Implemented

### 1. Automated Conflict Prevention ✅
- Server-side validation in `CoachingSession.clean()`
- Real-time conflict checking API endpoint
- Detailed conflict information with existing session details

### 2. Trainee Transparency & Dashboard ✅
- Complete session information in API responses
- Real-time status updates
- Payment tracking integration
- Notification system for all updates

### 3. Dynamic Lifecycle Management ✅
- Full CRUD operations for sessions and memberships
- State management with proper status transitions
- Automated notifications for state changes
- Flexible rescheduling with conflict prevention

### 4. Transactional Automation ✅
- Payment success triggers via signals
- Automated email generation with templates
- Notification logging system
- Stripe webhook integration ready

### 5. Interactive Feedback Loop ✅
- Threaded comment system with replies
- Pinned coach directives
- Bi-directional session feedback
- Real-time messaging capabilities

## Security Considerations

1. **Authentication**: All API endpoints require authentication
2. **Authorization**: Row-level permissions ensure users can only access their own data
3. **Input Validation**: All inputs are validated using Django REST Framework serializers
4. **CSRF Protection**: CSRF tokens required for state-changing operations
5. **Rate Limiting**: Consider adding rate limiting for production use

## Performance Optimizations

1. **Database Queries**: Uses `select_related` and `prefetch_related` for efficient queries
2. **Pagination**: API responses are paginated to handle large datasets
3. **Caching**: Consider adding Redis caching for frequently accessed data
4. **Indexing**: Add database indexes for commonly queried fields

## Monitoring and Logging

The system includes comprehensive logging for:
- Payment processing events
- Email delivery status
- Session scheduling conflicts
- Error tracking and debugging

## Next Steps

1. **Frontend Integration**: Build React/Vue.js components to consume the API
2. **Mobile App**: Use the same API endpoints for mobile app development
3. **Advanced Analytics**: Add reporting and analytics features
4. **Integration Testing**: Write comprehensive tests for all workflows
5. **Performance Monitoring**: Add APM tools like Sentry or New Relic

## Support

For questions or issues with the implementation:
1. Check the Django admin interface for data management
2. Review the API documentation in the code comments
3. Use the management commands for maintenance tasks
4. Monitor the notification logs for delivery issues