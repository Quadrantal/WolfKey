from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.db.models import Q, F, Case, When, IntegerField
from django.core.paginator import Paginator
from django.utils.timezone import localtime
from django.utils.dateformat import DateFormat
from django.contrib.auth.decorators import login_required
import json
import logging

from forum.models import User, Post, Solution, Comment, Course
from forum.services.course_services import get_user_courses
from forum.services.utils import (
    process_post_preview, 
    add_course_context, 
    selective_quote_replace, 
    detect_bad_words
)
from forum.services.auth_services import (
    authenticate_user
)
from forum.views.notification_views import send_course_notifications

logger = logging.getLogger(__name__)

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'csrfToken': request.META.get('CSRF_COOKIE')})


    
@login_required
def api_logout(request):
    logout(request)
    return JsonResponse({'success': 'Logged out succesfully'})
    
from django.core.paginator import Paginator
from django.http import JsonResponse

from django.utils.dateformat import DateFormat
from django.utils.timezone import localtime

@login_required
def for_you_api(request):
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

        local_created_at = localtime(post.created_at).isoformat()

        post_list.append({
            "id": post.id,
            "author_name": post.author.get_full_name(),
            "title": post.title,
            "preview_text": post.preview_text,
            "created_at": local_created_at,
            "tag": post.course_context,
            "reply_count": post.replies.count() if hasattr(post, 'replies') else 0,
        })

    return JsonResponse({
        "posts": post_list,
        "has_next": page_obj.has_next()
    })



@login_required
@require_http_methods(["GET"])
def api_post_detail(request, post_id):
    """API endpoint to get post details"""
    try:
        post = get_object_or_404(Post, id=post_id)
        solutions = post.solutions.annotate(
            vote_score=F('upvotes') - F('downvotes')
        ).order_by(
            Case(
                When(id=post.accepted_solution_id, then=0),
                default=1,
                output_field=IntegerField(),
            ),
            '-vote_score',
            '-created_at'
        )

        # Process solutions
        processed_solutions = []
        for solution in solutions:
            try:
                solution_content = solution.content
                if isinstance(solution_content, str):
                    solution_content = selective_quote_replace(solution_content)
                    solution_content = json.loads(solution_content)
                
                comments = solution.comments.select_related('author').order_by('created_at')
                processed_comments = [{
                    'id': comment.id,
                    'content': comment.content,
                    'author': comment.author.get_full_name(),
                    'created_at': comment.created_at.isoformat(),
                    'parent_id': comment.parent_id,
                    'depth': comment.get_depth(),
                } for comment in comments]

                processed_solutions.append({
                    'id': solution.id,
                    'content': solution_content,
                    'author': solution.author.get_full_name(),
                    'created_at': solution.created_at.isoformat(),
                    'upvotes': solution.upvotes,
                    'downvotes': solution.downvotes,
                    'comments': processed_comments,
                })
            except Exception as e:
                logger.error(f"Error processing solution {solution.id}: {e}")
        
        print(processed_solutions)

        response_data = {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'author': post.author.get_full_name(),
            'created_at': post.created_at.isoformat(),
            'solutions': processed_solutions,
            'courses': [{'id': c.id, 'name': c.name} for c in post.courses.all()],
        }

        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def api_create_post(request):
    """API endpoint to create a new post"""
    try:
        data = json.loads(request.body)
        
        # Create post instance
        post = Post(
            author=request.user,
            title=data.get('title'),
            content=data.get('content')
        )

        # Validate content
        if isinstance(post.content, dict) and 'blocks' in post.content:
            blocks = post.content.get('blocks', [])
            if (len(blocks) == 1 and 
                blocks[0].get('type') == 'paragraph' and 
                not blocks[0].get('data', {}).get('text', '').strip()) or len(blocks) == 0:
                return JsonResponse({'error': 'Post content cannot be empty'}, status=400)

        detect_bad_words(post.content)
        post.save()

        # Handle courses
        course_ids = data.get('courses', [])
        if course_ids:
            courses = Course.objects.filter(id__in=course_ids)
            post.courses.set(courses)
            send_course_notifications(post, courses)

        return JsonResponse({
            'id': post.id,
            'url': post.get_absolute_url(),
            'message': 'Post created successfully'
        }, status=201)

    except ValueError as e:
        return JsonResponse({'error': f"Content contains inappropriate language: {str(e)}"}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error creating post: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["PUT", "PATCH"])
def api_update_post(request, post_id):
    """API endpoint to update a post"""
    try:
        post = get_object_or_404(Post, id=post_id)
        
        if request.user != post.author:
            return JsonResponse({'error': 'Permission denied'}, status=403)

        data = json.loads(request.body)
        
        # Update content if provided
        if 'content' in data:
            content = data['content']
            detect_bad_words(content)
            post.content = content

        # Update courses if provided
        if 'courses' in data:
            course_ids = data['courses']
            courses = Course.objects.filter(id__in=course_ids)
            post.courses.set(courses)

        post.save()
        return JsonResponse({'message': 'Post updated successfully'})

    except ValueError as e:
        return JsonResponse({'error': f"Content contains inappropriate language: {str(e)}"}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error updating post: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["DELETE"])
def api_delete_post(request, post_id):
    """API endpoint to delete a post"""
    try:
        post = get_object_or_404(Post, id=post_id)
        
        if post.author != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
            
        post.delete()
        return JsonResponse({'message': 'Post deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting post: {e}")
        return JsonResponse({'error': str(e)}, status=500)
