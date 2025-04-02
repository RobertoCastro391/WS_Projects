import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from dotenv import load_dotenv

User = get_user_model()

# Define the admin user credentials
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'NBAAdmin')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'nbaadmin123@example.com')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'adminpass123')

def create_admin_user():
    # Skip this during certain management commands to avoid issues
    if 'makemigrations' in os.sys.argv or 'migrate' in os.sys.argv or 'collectstatic' in os.sys.argv:
        return
    
    try:
        # Check if admin user already exists
        if User.objects.filter(username=ADMIN_USERNAME).exists():
            # User exists, ensure it has admin privileges
            user = User.objects.get(username=ADMIN_USERNAME)
            if not user.is_staff or not user.is_superuser:
                user.is_staff = True
                user.is_superuser = True
                user.save()
                print(f"Updated '{ADMIN_USERNAME}' with admin privileges")
            return
        
        # Create the superuser
        User.objects.create_superuser(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD
        )
        print(f"Admin user '{ADMIN_USERNAME}' created successfully")
    except IntegrityError:
        print(f"Could not create admin user '{ADMIN_USERNAME}' (IntegrityError)")
    except Exception as e:
        print(f"Error creating admin user: {e}")