from django.db import migrations
from django.db.utils import ProgrammingError

def create_extension(apps, schema_editor):
    # Only run this for PostgreSQL
    if schema_editor.connection.vendor == 'postgresql':
        try:
            schema_editor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        except ProgrammingError:
            # Log warning or handle the case where we can't create the extension
            pass

def remove_extension(apps, schema_editor):
    # Only run this for PostgreSQL
    if schema_editor.connection.vendor == 'postgresql':
        try:
            schema_editor.execute("DROP EXTENSION IF EXISTS pg_trgm;")
        except ProgrammingError:
            pass

class Migration(migrations.Migration):
    dependencies = [
        ('forum', '0002_userMigrate'),
    ]

    operations = [
        migrations.RunPython(create_extension, remove_extension),
    ]