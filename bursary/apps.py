from django.apps import AppConfig


class BursaryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bursary'
    
    # connect the signals
    def ready(self):
        import bursary.signals  # Make sure this file runs

    