from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'core'
    verbose_name       = 'النواة المشتركة'

    def ready(self):
        import core.signals