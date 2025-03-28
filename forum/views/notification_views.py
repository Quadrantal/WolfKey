from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import send_mail
from django.conf import settings

from forum.models import UserCourseExperience, Notification 
from forum.models import Post, Solution  
from forum.models import User 
import logging

logger = logging.getLogger(__name__)
def send_course_notifications(post, courses):
    experienced_users = UserCourseExperience.objects.filter(
        course__in=courses
    ).select_related('user').distinct('user')
    
    experienced_users = experienced_users.exclude(user=post.author) 
    
    for exp_user in experienced_users:
        # Create in-site notification
        Notification.objects.create(
            recipient=exp_user.user,
            sender=post.author,
            notification_type='post',
            post=post,
            message=f'New post in {", ".join(c.name for c in courses)}: {post.title}'
        )
        
        # Send email notification
        subject = f'New post in your experienced course: {post.title}'
        message = f"""
        Hello {exp_user.user.get_full_name()},
        
        A new post has been created in a course you have experience in:
        
        Title: {post.title}
        Course(s): {', '.join(c.name for c in courses)}
        
        You can view the post here:
        {settings.SITE_URL}{post.get_absolute_url()}
        
        Best regards,
        School Forum Team
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [exp_user.user.personal_email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send notification email to {exp_user.user.personal_email}: {e}")

def send_solution_notification(solution):
    post = solution.post
    author = post.author
    
    # Create in-site notification
    Notification.objects.create(
        recipient=author,
        sender=solution.author,
        notification_type='solution',
        post=post,
        solution=solution,
        message=f'New solution to your question: {post.title}'
    )
    
    # Send email notification
    subject = f'New solution to your question: {post.title}'
    message = f"""
    Hello {author.get_full_name()},
    
    A new solution has been posted to your question:
    
    Post: {post.title}
    Solution by: {solution.author.get_full_name()}
    
    You can view the solution here:
    {settings.SITE_URL}{post.get_absolute_url()}
    
    Best regards,
    School Forum Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [author.personal_email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Failed to send solution notification email to {author.personal_email}: {e}")

@login_required
def all_notifications(request):
    notifications = request.user.notifications.all()
    return render(request, 'forum/notifications.html', {'notifications': notifications})

@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    
    if notification.post:
        return redirect('post_detail', post_id=notification.post.id)
    return redirect('all_notifications')