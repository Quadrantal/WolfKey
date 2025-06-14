from forum.services.auth_services import (
    authenticate_and_login_user,
    register_user,
    get_user_profile_data
)
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from forum.forms import CustomUserCreationForm
import json

@ensure_csrf_cookie
@require_http_methods(["POST"])
def api_login(request):
    try:
        data = json.loads(request.body)
        school_email = data.get('school_email')
        password = data.get('password')

        if not school_email or not password:
            return JsonResponse({'error': 'Please provide both school email and password'}, status=400)

        user, error = authenticate_and_login_user(request, school_email, password)
        if error:
            return JsonResponse({'error': error}, status=401)

        profile = user.userprofile

        return JsonResponse({
            'user': {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'name': user.get_full_name(),
                'school_email': user.school_email,
                'is_moderator': profile.is_moderator,
                'points': profile.points,
                'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
                'background_hue': profile.background_hue,
                'courses': {
                    f'block_{block}': getattr(profile, f'block_{block}').name 
                    for block in ['1A', '1B', '1D', '1E', '2A', '2B', '2C', '2D', '2E']
                    if getattr(profile, f'block_{block}')
                }
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_logout(request):
    logout(request)
    return JsonResponse({'success': 'Logged out successfully'})

@require_http_methods(["POST"])
def api_register(request):
    try:
        data = json.loads(request.body)
        form = CustomUserCreationForm(data)
        
        if not form.is_valid():
            return JsonResponse({'error': form.errors}, status=400)
            
        current_courses = data.get('current_courses', [])
        experienced_courses = data.get('experienced_courses', [])
        
        user, error = register_user(request, form, current_courses, experienced_courses)
        
        if error:
            return JsonResponse({'error': error}, status=400)
            
        return JsonResponse({
            'message': 'Registration successful',
            'user': get_user_profile_data(user)
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

