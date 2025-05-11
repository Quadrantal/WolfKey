from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from forum.models import User, Post
from django.db.models import Q,F
from django.core.paginator import Paginator
from forum.views.course_views import get_user_courses
from forum.views.schedule_views import get_block_order_for_day, process_schedule_for_user, is_ceremonial_uniform_required
from forum.views.utils import process_post_preview, add_course_context
from django.contrib.auth.decorators import login_required
import json

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'csrfToken': request.META.get('CSRF_COOKIE')})


@ensure_csrf_cookie
@require_http_methods(["POST"])
def api_login(request):
    try:
        data = json.loads(request.body)
        print(data)
        school_email = data.get('school_email')
        password = data.get('password')

        if not school_email or not password:
            return JsonResponse({
                'error': 'Please provide both school email and password'
            }, status=400)

        try:
            # Get user by school email
            user = User.objects.get(school_email=school_email)
            if user.check_password(password):
                login(request, user)
                profile = user.userprofile

                print(profile)
                
                return JsonResponse({
                    'user': {
                        'id': user.id,
                        'name': user.get_full_name(),
                        'school_email': user.school_email,
                        'is_moderator': profile.is_moderator,
                        'points': profile.points,
                        'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
                        'courses': {
                            f'block_{block}': getattr(profile, f'block_{block}').name 
                            for block in ['1A', '1B', '1D', '1E', '2A', '2B', '2C', '2D', '2E']
                            if getattr(profile, f'block_{block}')
                        }
                    }
                })
            else:
                return JsonResponse({
                    'error': 'Invalid password'
                }, status=401)
                
        except User.DoesNotExist:
            return JsonResponse({
                'error': 'No account found with this school email'
            }, status=401)

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)
    
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

