from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q,F
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.contrib.postgres.search import TrigramSimilarity
from forum.models import Post, User
from forum.views.utils import process_post_preview, add_course_context
from forum.views.greetings import get_random_greeting
from forum.views.course_views import get_user_courses
from forum.views.schedule_views import get_block_order_for_day, process_schedule_for_user, is_ceremonial_uniform_required
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from django.db.models import Count
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponse

def search_results_new_page(request):
    query = request.GET.get('q', '')
    posts = Post.objects.all().order_by('-created_at')
    users = User.objects.all()

    if query:
        search_query = SearchQuery(query)

        # Search in posts
        posts = posts.annotate(
            rank=SearchRank(F('search_vector'), search_query) + TrigramSimilarity('title', query),
            
            solution_count=Count('solutions', distinct=True),
            comment_count=Count('solutions__comments', distinct=True),
            total_response_count=Count('solutions', distinct=True) + Count('solutions__comments', distinct=True)
        ).filter(rank__gte=0.3).order_by('-rank')

        # Search in users
        users = users.annotate(
            rank=SearchRank(F('search_vector'), search_query),
        ).filter(rank__gte=0.3).order_by('-rank')

        experienced_courses, help_needed_courses = get_user_courses(request.user)

        # Process posts
        for post in posts:
            post.preview_text = process_post_preview(post)
            add_course_context(post, experienced_courses, help_needed_courses)

        return render(request, 'forum/search_results.html', {
            'posts': posts,
            'users': users,
            'query': query
        })

    return redirect('all_posts')


