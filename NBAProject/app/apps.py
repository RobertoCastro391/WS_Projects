from django.apps import AppConfig


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        from .admin_setup import create_admin_user

        # Run the function to create admin user if it doesn't exist
        create_admin_user()
