from django.apps import AppConfig


class AppiotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'AppIoT'

    def ready(self):
            # Avvio del client MQTT all'avvio del server Django
            from .mqtt_client import client
            print("🔗 Client MQTT avviato!")