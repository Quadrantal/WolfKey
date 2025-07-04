from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from forum.models import UserCourseExperience, Notification, Post, Solution
import logging

logger = logging.getLogger(__name__)

def send_course_notifications_service(post, courses):
    experienced_users = UserCourseExperience.objects.filter(
        course__in=courses
    ).select_related('user').distinct('user')
    experienced_users = experienced_users.exclude(user=post.author)
    for exp_user in experienced_users:
        recipient = exp_user.user
        message = f'New post in {", ".join(c.name for c in courses)}: {post.title}'
        url = post.get_absolute_url()
        email_subject = f'New post in your experienced course: {post.title}'
        email_message = f"""
        Hello {recipient.get_full_name()},
        
        A new post has been created in a course you have experience in:
        
        Title: {post.title}
        Course(s): {', '.join(c.name for c in courses)}
        
        You can view the post here:
        {settings.SITE_URL}{url}
        
        Best regards,
        WolfKey Team
        """
        send_notification_service(
            recipient=recipient,
            sender=post.author,
            notification_type='post',
            message=message,
            url=url,
            post=post,
            email_subject=email_subject,
            email_message=email_message,
        )

def send_solution_notification_service(solution):
    post = solution.post
    author = post.author
    message = f'New solution to your question: {post.title}'
    url = post.get_absolute_url()
    email_subject = f'New solution to your question: {post.title}'
    email_message = f"""
    Hello {author.get_full_name()},
    
    A new solution has been posted to your question:
    
    Post: {post.title}
    Solution by: {solution.author.get_full_name()}
    
    You can view the solution here:
    {settings.SITE_URL}{url}
    
    Best regards,
    WolfKey Team
    """
    send_notification_service(
        recipient=author,
        sender=solution.author,
        notification_type='solution',
        message=message,
        url=url,
        post=post,
        solution=solution,
        email_subject=email_subject,
        email_message=email_message,
    )

def send_comment_notifications_service(comment, solution, parent_comment=None):
    notified_users = set()
    if solution.author != comment.author:
        solution_author_message = f"{comment.author.get_full_name()} commented on your solution."
        solution_author_email_subject = f"New comment on your solution for '{solution.post.title}'"
        solution_author_email_message = f"""
        Hello {solution.author.get_full_name()},
        
        You can view the solution and comment here:
        {settings.SITE_URL}{solution.get_absolute_url()}
        
        Best regards,
        WolfKey Team
        """
        send_notification_service(
            recipient=solution.author,
            sender=comment.author,
            notification_type='comment',
            message=solution_author_message,
            url=solution.get_absolute_url(),
            post=solution.post,
            solution=solution,
            email_subject=solution_author_email_subject,
            email_message=solution_author_email_message,
        )
        notified_users.add(solution.author)
    if parent_comment and parent_comment.author != comment.author and parent_comment.author not in notified_users:
        parent_author_message = f"{comment.author.get_full_name()} replied to your comment."
        parent_author_email_subject = f"New reply to your comment on '{solution.post.title}'"
        parent_author_email_message = f"""
        Hello {parent_comment.author.get_full_name()},
        
        {comment.author.get_full_name()} has replied to your comment:
  
        You can view the reply here:
        {settings.SITE_URL}{comment.get_absolute_url()}
        
        Best regards,
        WolfKey Team
        """
        send_notification_service(
            recipient=parent_comment.author,
            sender=comment.author,
            notification_type='reply',
            message=parent_author_message,
            url=comment.get_absolute_url(),
            post=solution.post,
            solution=solution,
            email_subject=parent_author_email_subject,
            email_message=parent_author_email_message,
        )
        notified_users.add(parent_comment.author)

def send_notification_service(
    recipient, sender, notification_type, message, url=None, post=None, solution=None, email_subject=None, email_message=None
):
    Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        post=post,
        solution=solution,
        message=message,
    )
    if email_subject and email_message:
        try:
            send_mail(
                email_subject,
                email_message,
                settings.DEFAULT_FROM_EMAIL,
                [recipient.personal_email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Failed to send notification email to {recipient.personal_email}: {e}")

def all_notifications_service(user):
    return user.notifications.all()

def mark_notification_read_service(user, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=user)
    notification.is_read = True
    notification.save()
    return notification
