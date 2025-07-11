from django.db.models import F, Count
from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramSimilarity
from forum.models import Post, User
from forum.services.utils import process_post_preview, add_course_context, annotate_post_card_context
from forum.services.course_services import get_user_courses

def search_posts(user, query):
    search_query = SearchQuery(query)
    posts = Post.objects.annotate(
        rank=SearchRank(F('search_vector'), search_query) + TrigramSimilarity('title', query),
        solution_count=Count('solutions', distinct=True),
        comment_count=Count('solutions__comments', distinct=True),
        total_response_count=Count('solutions', distinct=True) + Count('solutions__comments', distinct=True)
    ).filter(rank__gte=0.3).order_by('-rank')

    posts = annotate_post_card_context(posts, user)
    return posts

def search_users(user, query):
    search_query = SearchQuery(query)

    users = User.objects.annotate(
        rank=SearchRank(F('search_vector'), search_query),
    ).filter(rank__gte=0.1).order_by('-rank')

    return users
