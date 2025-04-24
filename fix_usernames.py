import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_forum.settings')
django.setup()

from forum.models import User

def fix_usernames():
    """Find users with null or empty usernames and set their username to their school_email"""
    
    # Get users with null or empty usernames
    users_without_username = User.objects.filter(username__isnull=True) | User.objects.filter(username='')
    
    count = users_without_username.count()
    print(f"Found {count} users without a username")
    
    # Set usernames for these users
    for user in users_without_username:
        user.username = user.school_email
        user.save()
        print(f"Set username for {user.get_full_name()} to {user.username}")
    
    print(f"Fixed {count} users")

if __name__ == "__main__":
    fix_usernames() 