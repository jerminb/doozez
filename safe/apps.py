from django.apps import AppConfig
import firebase_admin


class SafeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'safe'

    def ready(self):
        firebase_admin.initialize_app()

