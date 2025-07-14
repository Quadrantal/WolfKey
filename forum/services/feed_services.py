from django.db.models import Q, F, Count
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from forum.models import Post
from forum.services.course_services import get_user_courses
from forum.services.utils import process_post_preview, add_course_context, annotate_post_card_context
from django.core.paginator import Paginator
from django.utils.timezone import localtime

def get_for_you_posts(user, page=1, per_page=8):
    """
    Return a tuple of (annotated posts on the current page, page_obj).
    """
    experienced_courses, help_needed_courses = get_user_courses(user)
    profile = user.userprofile

    current_courses = list(filter(None, [
        profile.block_1A, profile.block_1B, profile.block_1D, profile.block_1E,
        profile.block_2A, profile.block_2B, profile.block_2C, profile.block_2D, profile.block_2E
    ]))

    base_qs = Post.objects.filter(
        Q(courses__in=experienced_courses) | 
        Q(courses__in=help_needed_courses) | 
        Q(author=user) |
        Q(courses__in=current_courses)
    ).distinct().order_by('-created_at')

    paginator = Paginator(base_qs, per_page)
    page_obj = paginator.get_page(page)

    post_ids = [post.id for post in page_obj.object_list]

    posts = Post.objects.filter(id__in=post_ids).annotate(
        solution_count=Count('solutions', distinct=True),
        comment_count=Count('solutions__comments', distinct=True),
        total_response_count=Count('solutions', distinct=True) + Count('solutions__comments', distinct=True)
    ).select_related('author').prefetch_related('courses', 'solutions__comments')

    posts_dict = {post.id: post for post in posts}
    ordered_posts = [posts_dict[pid] for pid in post_ids if pid in posts_dict]
    ordered_posts = annotate_post_card_context(ordered_posts, user)

    return ordered_posts, page_obj

def get_all_posts(user, query='', page=1, per_page=8):
    """
    Returns a dict with paginated posts and page_obj, similar to get_for_you_posts.
    """
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

    posts = annotate_post_card_context(posts, user)

    paginator = Paginator(posts, per_page)
    page_obj = paginator.get_page(page)

    return {
        "page_obj": page_obj,
        "has_next": page_obj.has_next()
    }

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
    posts = Post.objects.filter(author = user).order_by('-created_at')
    posts = annotate_post_card_context(posts, user)
    return posts