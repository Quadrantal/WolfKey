web: gunicorn student_forum.wsgi --log-file -
worker: celery -A student_forum worker --loglevel=info --concurrency=2 -Q high,default,low
beat: celery -A student_forum beat --loglevel=info