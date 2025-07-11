from django.db.models import F, Count
from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramSimilarity
from forum.models import Post, User
from forum.services.utils import process_post_preview, add_course_context
from forum.services.course_services import get_user_courses

def search_posts_and_users_service(user, query):
    search_query = SearchQuery(query)
    posts = Post.objects.annotate(
        rank=SearchRank(F('search_vector'), search_query) + TrigramSimilarity('title', query),
        solution_count=Count('solutions', distinct=True),
        comment_count=Count('solutions__comments', distinct=True),
        total_response_count=Count('solutions', distinct=True) + Count('solutions__comments', distinct=True)
    ).filter(rank__gte=0.3).order_by('-rank')

    users = User.objects.annotate(
        rank=SearchRank(F('search_vector'), search_query),
    ).filter(rank__gte=0.1).order_by('-rank')

    experienced_courses, help_needed_courses = get_user_courses(user)
    for post in posts:
        post.preview_text = process_post_preview(post)
        add_course_context(post, experienced_courses, help_needed_courses)
    return posts, users
