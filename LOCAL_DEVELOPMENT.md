# WolfKey Grade Checking System

## Overview

The parallel grade checking system uses **Celery** with **Redis** to:
- Check user grades in parallel (instead of sequentially)
- Schedule automatic grade checks every 30 minutes
- Handle email notifications in a separate queue

## ✅ What's Working

- **Celery + Redis** for task queuing and parallel processing
- **Automatic scheduling** every 30 minutes via Celery Beat
- **Separate email queue** to avoid blocking grade checks
- **Proper logging** instead of print statements
- **Management command** for manual testing

## 🗂️ Key Files

- `forum/tasks.py` - All grade checking and email tasks
- `student_forum/celery.py` - Celery configuration and scheduling
- `student_forum/settings.py` - Redis/Celery settings
- `forum/management/commands/check_grades.py` - Manual testing command
- `Procfile` - Heroku deployment configuration

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
celery -A student_forum worker --loglevel=info
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
1. **Celery Beat** schedules `check_all_user_grades` every 30 minutes
2. **Main Task** creates individual `check_single_user_grades` tasks for each user
3. **Worker Pool** processes multiple users in parallel
4. **Email Queue** handles notifications separately

### Task Types
- `check_all_user_grades` - Schedules grade checking for all users (runs every 30 minutes)
- `check_single_user_grades` - Checks grades for one specific user
- `send_email_notification` - Sends email notifications in separate queue

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
worker: celery -A student_forum worker --loglevel=info
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

## Performance Benefits

1. **Parallel Processing**: Multiple users' grades are checked simultaneously
2. **Separate Email Queue**: Email sending doesn't block grade checking
3. **Automatic Scheduling**: No manual intervention needed
4. **Scalable**: Easy to add more workers as user base grows

## Troubleshooting

### Common Issues
1. **Redis Connection Error**: Check `REDIS_URL` environment variable
2. **Tasks Not Running**: Ensure worker and beat processes are running
3. **Email Delays**: Check email task queue separately

### Debug Commands
```bash
# Check Redis connection
redis-cli ping

# View detailed logs
celery -A student_forum worker --loglevel=debug

# Check task status
python -c "
from forum.tasks import check_all_user_grades
task = check_all_user_grades.delay()
print(f'Task ID: {task.id}')
print(f'Status: {task.status}')
"
```

## 🔧 Performance Notes

- **Local Development**: Single worker handles ~11 concurrent tasks
- **Task Duration**: Each user check takes ~30 seconds
- **Memory Usage**: Monitor Chrome processes, they can accumulate
- **Redis Storage**: Results are stored temporarily in Redis

## 📈 Ready for Production

The system is now clean, efficient, and ready for Heroku deployment.
