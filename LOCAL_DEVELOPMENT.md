# WolfKey Grade Checking System

## Overview

The parallel grade checking system uses **Celery** with **Redis** to:
- Check user grades in parallel (instead of sequentially)
- Schedule automatic grade checks every 30 minutes
- Handle email notifications in a separate queue
- Handle auto complete courses when users requests it


## Local Development

### 1. Setup Redis
```bash
brew install redis
brew services start redis
redis-cli ping  # Should return: PONG
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the System (3 terminals)

**Terminal 1: Celery Worker**
```bash
celery -A student_forum worker --loglevel=info --concurrency=3 -Q high,default,low
```

**Terminal 2: Celery Beat (Scheduler)**
```bash
celery -A student_forum beat --loglevel=info
```

**Terminal 3: Django Server**
```bash
python manage.py runserver
```

## Testing

### Manual Grade Checking
```bash
# Check all users' grades
python manage.py check_grades

# Check specific user's grades
python manage.py check_grades --user-email student@wpga.ca
```

### Monitor Tasks (Optional)
```bash
pip install flower
celery -A student_forum flower
# Visit http://localhost:5555
```

## How It Works

### System Architecture
1. **Celery Beat** automatically schedules both `check_all_user_grades` and `autocomplete_courses` tasks every 30 minutes, but you can also trigger grade checks manually with the management command.
2. When triggered, the main grade-checking task quickly creates individual `check_single_user_grades` tasks for each user and hands them off to Celery, which uses separate queues for different types of tasks (e.g., high, default, low, email).
3. The Celery worker pool processes tasks in parallel from these queues, so grade checking, autocomplete, and email notifications do not block the Django server or each other.
4. Email notifications and autocomplete requests are handled in their own queues, ensuring independent and efficient processing.

### Task Types
- `check_all_user_grades` - Schedules grade checking for all users (runs every 30 minutes)
- `check_single_user_grades` - Checks grades for one specific user
- `send_email_notification` - Sends email notifications in separate queue
- `autocomplete_courses` - Returns user's courses from WolfNet

## Heroku Deployment

### Required Add-ons
```bash
# Add Redis addon
heroku addons:create heroku-redis:mini

# Check Redis URL
heroku config:get REDIS_URL
```

### Procfile Processes
```
web: gunicorn student_forum.wsgi --log-file -
worker: celery -A student_forum worker --loglevel=info --concurrency=3 -Q high,default,low
beat: celery -A student_forum beat --loglevel=info
```

### Scaling
```bash
# Scale up workers for parallel processing
heroku ps:scale worker=1 beat=1

# For heavy load, you can add more workers
heroku ps:scale worker=2
```

### Heroku Logs
```bash
# View worker logs
heroku logs -t --dyno worker

# View beat logs  
heroku logs -t --dyno beat
```
