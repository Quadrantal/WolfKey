from django.db import migrations
from django.contrib.auth.hashers import make_password

def forward_func(apps, schema_editor):
    # Since we can't access the old users directly, we'll create a new superuser
    User = apps.get_model('forum', 'User')
    


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