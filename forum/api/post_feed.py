from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from forum.services.feed_services import get_for_you_posts, get_all_posts, paginate_posts

@login_required
def for_you_api(request):
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 10))

    posts_qs = get_for_you_posts(request.user)
    paginated_data = paginate_posts(posts_qs, page, limit)
    
    return JsonResponse({
        "posts": paginated_data["posts"],
        "has_next": paginated_data["has_next"]
    })

@login_required
@require_http_methods(["GET"])
def all_posts_api(request):
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 10))
    query = request.GET.get('q', '')

    posts_qs = get_all_posts(request.user, query)
    paginated_data = paginate_posts(posts_qs, page, limit)
    
    return JsonResponse({
        "posts": paginated_data["posts"],
        "has_next": paginated_data["has_next"]
    })
