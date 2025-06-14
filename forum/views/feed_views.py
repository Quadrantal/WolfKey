from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from forum.services.feed_services import get_for_you_posts, get_all_posts, paginate_posts
from forum.models import Post, User
from forum.views.greetings import get_random_greeting
from forum.views.schedule_views import (
    get_block_order_for_day, 
    process_schedule_for_user,
    is_ceremonial_uniform_required
)
from forum.views.course_views import get_user_courses
from forum.views.utils import process_post_preview, add_course_context
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

@login_required
def for_you(request):
    if not request.user.is_authenticated:
        return redirect('login')

    posts_qs = get_for_you_posts(request.user)
    page = request.GET.get('page', 1)
    paginated_data = paginate_posts(posts_qs, page)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'forum/components/post_list.html', 
                     {'posts': paginated_data["page_obj"]})

    # Get schedule info
    pst = ZoneInfo("America/Los_Angeles")
    now_pst = datetime.now(pst)
    today = now_pst.strftime("%a, %b %d").lstrip("0").replace(" 0", " ")
    tomorrow = (now_pst + timedelta(days=1)).strftime("%a, %b %d").lstrip("0").replace(" 0", " ")

    greeting = get_random_greeting(request.user.first_name, user_timezone="America/Vancouver")
    ceremonial_required_today = is_ceremonial_uniform_required(request.user, today)
    ceremonial_required_tomorrow = is_ceremonial_uniform_required(request.user, tomorrow)
    
    raw_schedule_today = get_block_order_for_day(today)
    raw_schedule_tomorrow = get_block_order_for_day(tomorrow)
    processed_schedule_today = process_schedule_for_user(request.user, raw_schedule_today)
    processed_schedule_tomorrow = process_schedule_for_user(request.user, raw_schedule_tomorrow)

    return render(request, 'forum/for_you.html', {
        'posts': paginated_data["page_obj"],
        'greeting': greeting,
        'current_date': today,
        'tomorrow_date': tomorrow,
        'schedule_today': processed_schedule_today,
        'schedule_tomorrow': processed_schedule_tomorrow,
        'ceremonial_required_today': ceremonial_required_today,
        'ceremonial_required_tomorrow': ceremonial_required_tomorrow,
    })

def all_posts(request):
    query = request.GET.get('q', '')
    posts_qs = get_all_posts(request.user, query)
    page = request.GET.get('page', 1)
    paginated_data = paginate_posts(posts_qs, page)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'forum/components/post_list.html', 
                     {'posts': paginated_data["page_obj"]})

    return render(request, 'forum/all_posts.html', {
        'posts': paginated_data["page_obj"],
        'query': query,
    })

@login_required
def my_posts(request):
    posts = Post.objects.filter(author = request.user)
    experienced_courses, help_needed_courses = get_user_courses(request.user)
    
    # Process posts
    for post in posts:
        post.preview_text = process_post_preview(post)
        add_course_context(post, experienced_courses, help_needed_courses)
    return render(request,'forum/my_posts.html', {'posts': posts})