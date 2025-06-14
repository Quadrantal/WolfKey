from django.db.models import Q, F, Count
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from forum.models import Post
from forum.views.course_views import get_user_courses
from forum.views.utils import process_post_preview, add_course_context
from django.core.paginator import Paginator
from django.utils.timezone import localtime

def get_for_you_posts(user):
    experienced_courses, help_needed_courses = get_user_courses(user)
    user_profile = user.userprofile

    current_courses = list(filter(None, [
        user_profile.block_1A,
        user_profile.block_1B,
        user_profile.block_1D,
        user_profile.block_1E,
        user_profile.block_2A,
        user_profile.block_2B,
        user_profile.block_2C,
        user_profile.block_2D,
        user_profile.block_2E
    ]))

    posts = Post.objects.filter(
        Q(courses__in=experienced_courses) | 
        Q(courses__in=help_needed_courses) | 
        Q(author=user) |
        Q(courses__in=current_courses)
    ).annotate(
        solution_count=Count('solutions', distinct=True),
        comment_count=Count('solutions__comments', distinct=True),
        total_response_count=Count('solutions', distinct=True) + Count('solutions__comments', distinct=True)
    ).distinct().order_by('-created_at')

    process_posts(posts, experienced_courses, help_needed_courses)
    return posts

def get_all_posts(user, query=''):
    posts = Post.objects.annotate(
        solution_count=Count('solutions', distinct=True),
        comment_count=Count('solutions__comments', distinct=True),
        total_response_count=Count('solutions', distinct=True) + Count('solutions__comments', distinct=True)
    ).order_by('-created_at')

    if query:
        search_query = SearchQuery(query)
        posts = posts.annotate(
            rank=SearchRank(F('search_vector'), search_query) + TrigramSimilarity('title', query)
        ).filter(rank__gte=0.3).order_by('-rank')

    experienced_courses, help_needed_courses = get_user_courses(user)
    process_posts(posts, experienced_courses, help_needed_courses)
    return posts

def process_posts(posts, experienced_courses, help_needed_courses):
    for post in posts:
        post.preview_text = process_post_preview(post)
        add_course_context(post, experienced_courses, help_needed_courses)

def paginate_posts(posts_queryset, page=1, limit=10):
    """
    Handles pagination of posts queryset and returns formatted post data
    """
    paginator = Paginator(posts_queryset, limit)
    page_obj = paginator.get_page(page)

    post_list = [{
        "id": post.id,
        "author_name": post.author.get_full_name(),
        "title": post.title,
        "preview_text": post.preview_text,
        "created_at": localtime(post.created_at).isoformat(),
        "tag": post.course_context,
        "reply_count": post.replies.count() if hasattr(post, 'replies') else 0,
    } for post in page_obj]

    return {
        "posts": post_list,
        "page_obj": page_obj,
        "has_next": page_obj.has_next()
    }

def get_user_posts(user):
    posts = Post.objects.filter(author = user)
    experienced_courses, help_needed_courses = get_user_courses(user)
    
    # Process posts
    for post in posts:
        post.preview_text = process_post_preview(post)
        add_course_context(post, experienced_courses, help_needed_courses)
    return posts