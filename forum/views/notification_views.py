from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from forum.models import Notification
from forum.services.notification_services import (
    send_course_notifications_service,
    send_solution_notification_service,
    send_comment_notifications_service,
    all_notifications_service,
    mark_notification_read_service,
)

@login_required
def all_notifications(request):
    notifications = all_notifications_service(request.user)
    return render(request, 'forum/notifications.html', {'notifications': notifications})

@login_required
def mark_notification_read(request, notification_id):
    notification = mark_notification_read_service(request.user, notification_id)
    if notification and notification.post:
        return redirect('post_detail', post_id=notification.post.id)
    return redirect('all_notifications')

def send_course_notifications(post, courses):
    send_course_notifications_service(post, courses)

def send_solution_notification(solution):
    send_solution_notification_service(solution)

def send_comment_notifications(comment, solution, parent_comment=None):
    send_comment_notifications_service(comment, solution, parent_comment)