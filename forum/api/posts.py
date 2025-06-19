from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from django.db.models import Q, F, Case, When, IntegerField
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
import json

from forum.models import Post, Course
from forum.views.course_views import get_user_courses
from forum.services.utils import process_post_preview, add_course_context, detect_bad_words
from forum.services.post_services import (
    create_post_service,
    update_post_service,
    delete_post_service,
    get_post_detail_service
)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def for_you_api(request):
    try:
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 10))

        experienced_courses, help_needed_courses = get_user_courses(request.user)

        posts_qs = Post.objects.filter(
            Q(courses__in=experienced_courses) |
            Q(courses__in=help_needed_courses) |
            Q(author=request.user)
        ).distinct().order_by('-created_at')

        paginator = Paginator(posts_qs, limit)
        page_obj = paginator.get_page(page)

        post_list = []
        for post in page_obj:
            add_course_context(post, experienced_courses, help_needed_courses)
            post.preview_text = process_post_preview(post)
            
            post_list.append({
                "id": post.id,
                "author_name": post.author.get_full_name(),
                "title": post.title,
                "preview_text": post.preview_text,
                "created_at": post.created_at.isoformat(),
                "tag": post.course_context,
                "reply_count": post.replies.count() if hasattr(post, 'replies') else 0,
            })

        return JsonResponse({
            "posts": post_list,
            "has_next": page_obj.has_next()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def post_detail_api(request, post_id):
    result = get_post_detail_service(post_id)
    if 'error' in result:
        return JsonResponse(result, status=500)
    return JsonResponse(result)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_post_api(request):
    try:
        data = json.loads(request.body)
        result = create_post_service(request.user, data)
        return JsonResponse(result, status=201 if 'id' in result else 400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['PUT', 'PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_post_api(request, post_id):
    try:
        data = json.loads(request.body)
        result = update_post_service(request.user, post_id, data)
        if 'error' in result:
            return JsonResponse(result, status=403 if 'permission' in result['error'] else 400)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_post_api(request, post_id):
    result = delete_post_service(request.user, post_id)
    if 'error' in result:
        return JsonResponse(result, status=403)
    return JsonResponse(result)
