from django.apps import AppConfig
import os
class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):

        ENV = os.getenv("DJANGO_ENV", "dev")
        if ENV == "dev":
            if os.environ.get('RUN_MAIN', 'false') == 'true':
                from .startup import setup_graphdb
                setup_graphdb()

        from .admin_setup import create_admin_user
        # Run the function to create admin user if it doesn't exist
        create_admin_user()
