from django.apps import AppConfig


class LogsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'logs'
    verbose_name = 'System Logs'
    
    def ready(self):
        """Import signals when the app is ready"""
        try:
            import logs.signals
        except ImportError:
            pass
