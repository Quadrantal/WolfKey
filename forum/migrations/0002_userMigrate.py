from django.db import migrations
from django.contrib.auth.hashers import make_password

def forward_func(apps, schema_editor):
    # Since we can't access the old users directly, we'll create a new superuser
    User = apps.get_model('forum', 'User')
    
    # Create a default superuser if none exists
    if not User.objects.filter(is_superuser=True).exists():
        User.objects.create(
            username='admin',
            email='admin@wpga.ca',
            school_email='admin@wpga.ca',
            password=make_password('admin123'),  # Set a default password
            is_staff=True,
            is_superuser=True,
            is_active=True
        )

def reverse_func(apps, schema_editor):
    User = apps.get_model('forum', 'User')
    User.objects.filter(username='admin').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('forum', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(forward_func, reverse_func),
    ]