import os
from celery import Celery
from kombu import Queue

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_forum.settings')

app = Celery('student_forum')

# Using a string here means the worker doesn't have to serialize the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Define multiple queues with priorities
app.conf.task_queues = (
    Queue('high', routing_key='high.#'),      # Interactive user tasks
    Queue('default', routing_key='default.#'), # Regular tasks
    Queue('low', routing_key='low.#'),        # Background batch jobs
)

# Set default routing configuration
app.conf.task_default_queue = 'default'
app.conf.task_default_exchange_type = 'direct'
app.conf.task_default_routing_key = 'default.default'

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
