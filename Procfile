web: gunicorn student_forum.wsgi --log-file -
# Dedicated worker for grade checking tasks (uses WebDriver, memory intensive)
grades_worker: celery -A student_forum worker --loglevel=info --concurrency=1 -Q grades --pool=solo
# General worker for all other tasks (emails, notifications, high priority tasks)
general_worker: celery -A student_forum worker --loglevel=info --concurrency=2 -Q general,high,default,low
beat: celery -A student_forum beat --loglevel=info