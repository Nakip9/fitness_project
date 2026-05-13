from django.apps import AppConfig


class CoachingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'coaching'
    verbose_name = 'Coaching Management'
    
    def ready(self):
        import coaching.signals