import os
from celery import Celery
from kombu import Queue
import ssl

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_forum.settings')

app = Celery('student_forum')

# Using a string here means the worker doesn't have to serialize the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Define multiple queues with priorities and dedicated workers
# grades: Dedicated worker for all grade checking operations (WebDriver intensive)
# general: Worker for general tasks like emails, notifications, etc.
# high: Interactive user tasks with high priority
# default: Regular tasks (fallback queue)
# low: Background batch jobs
app.conf.task_queues = (
    Queue('grades', routing_key='grades.#'),    # Grade checking tasks (dedicated worker)
    Queue('general', routing_key='general.#'),  # General tasks (emails, notifications, etc.)
    Queue('high', routing_key='high.#'),        # Interactive user tasks
    Queue('default', routing_key='default.#'),  # Regular tasks (fallback)
    Queue('low', routing_key='low.#'),          # Background batch jobs
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
        'schedule': 60.0 * 60,  # Every 60 minutes
        'options': {'queue': 'grades', 'routing_key': 'grades.trigger'}
    },
    # Alternative: Use batched approach (comment out above and uncomment below)
    # 'check-all-user-grades-batched': {
    #     'task': 'forum.tasks.check_user_grades_batched_dispatch',
    #     'schedule': 30.0 * 60,  # Every 30 minutes
    #     'options': {'queue': 'grades', 'routing_key': 'grades.coordination'},
    #     'kwargs': {'batch_size': 1}  # Process 1 user at a time for memory efficiency
    # },
}

# Reduced time limits for memory efficiency
CELERY_TASK_SOFT_TIME_LIMIT = 45 
CELERY_TASK_TIME_LIMIT = 90 

app.conf.timezone = 'UTC'

# Ensure compatibility with Celery 6.0 and above
app.conf.broker_connection_retry_on_startup = True

# Respect Redis/Celery transport options set in Django settings.
from django.conf import settings as django_settings

# Apply transport options if provided in settings (e.g. max_connections)
try:
    transport_opts = getattr(django_settings, 'CELERY_BROKER_TRANSPORT_OPTIONS', None)
    if transport_opts:
        app.conf.broker_transport_options = transport_opts
except Exception:
    # Fail quietly - defaults will be used
    pass

# Configure SSL for Redis broker if the REDIS_URL uses rediss://
# Do not disable certificate validation (no CERT_NONE).
try:
    broker_url = getattr(django_settings, 'CELERY_BROKER_URL', os.getenv('REDIS_URL', ''))
    if broker_url and broker_url.startswith('rediss://'):
        # Let redis-py handle SSL using system certs / certifi bundle.
        # If custom CA is required, set CELERY_BROKER_USE_SSL in settings as a dict.
        ssl_opts = getattr(django_settings, 'CELERY_BROKER_USE_SSL', None)
        if ssl_opts is None:
            # Default: rely on system CA bundle; do not set CERT_NONE.
            app.conf.broker_use_ssl = True
        else:
            app.conf.broker_use_ssl = ssl_opts
except Exception:
    pass
