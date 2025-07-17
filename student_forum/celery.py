import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_forum.settings')

app = Celery('student_forum')

# Using a string here means the worker doesn't have to serialize the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'check-all-user-grades': {
        'task': 'forum.tasks.check_all_user_grades',
        'schedule': 30.0 * 60,  # Every 30 minutes
    },
}

app.conf.timezone = 'UTC'
