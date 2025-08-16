import os
from celery import Celery
from kombu import Queue
import ssl

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

# Memory optimization settings for Heroku
app.conf.worker_prefetch_multiplier = 1  # Reduce task prefetching
app.conf.worker_max_tasks_per_child = 10  # Restart worker after 10 tasks to free memory
app.conf.worker_disable_rate_limits = True
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'check-all-user-grades': {
        'task': 'forum.tasks.periodic_grade_check_trigger',
        'schedule': 30.0 * 60,  # Every 30 minutes
        'options': {'queue': 'default', 'routing_key': 'default.trigger'}
    },
    # Alternative: Use batched approach (comment out above and uncomment below)
    # 'check-all-user-grades-batched': {
    #     'task': 'forum.tasks.check_user_grades_batched_dispatch',
    #     'schedule': 30.0 * 60,  # Every 30 minutes
    #     'options': {'queue': 'default', 'routing_key': 'default.coordination'},
    #     'kwargs': {'batch_size': 1}  # Process 1 user at a time for memory efficiency
    # },
}

# Reduced time limits for memory efficiency
CELERY_TASK_SOFT_TIME_LIMIT = 45 
CELERY_TASK_TIME_LIMIT = 90 

app.conf.timezone = 'UTC'

# Ensure compatibility with Celery 6.0 and above
app.conf.broker_connection_retry_on_startup = True
