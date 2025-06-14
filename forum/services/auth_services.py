from django.contrib.auth import login
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from forum.models import User, UserCourseHelp, UserCourseExperience

def authenticate_and_login_user(request, school_email, password):
    try:
        user = User.objects.get(school_email=school_email)
    except User.DoesNotExist:
        return None, "No account found with this school email"

    if not user.check_password(password):
        return None, "Invalid password"

    login(request, user)
    return user, None

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'csrfToken': request.META.get('CSRF_COOKIE')})

def get_user_profile_data(user):
    """Centralized function to get user profile data"""
    profile = user.userprofile
    return {
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

def register_user(request, form, current_courses, experienced_courses):
    """
    Centralized service for user registration
    Returns (user, error_message) tuple
    """
    try:
        if len(experienced_courses) < 5:
            return None, 'You must select at least 5 experienced courses.'
            
        if len(current_courses) < 3:
            return None, 'You must select at least 3 courses you need help with.'

        user = form.save()
        
        # Add current courses as help needed
        for course_id in current_courses:
            UserCourseHelp.objects.create(
                user=user,
                course_id=course_id,
                active=True
            )
            
        # Add experienced courses
        for course_id in experienced_courses:
            UserCourseExperience.objects.create(
                user=user,
                course_id=course_id
            )
        
        login(request, user)
        return user, None
        
    except Exception as e:
        return None, str(e)