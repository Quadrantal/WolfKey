from django.contrib.auth import login
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from forum.models import User, UserCourseHelp, UserCourseExperience

def authenticate_user(request, school_email, password):
    try:
        user = User.objects.get(school_email=school_email)
    except User.DoesNotExist:
        return None, "No account found with this school email"

    if not user.check_password(password):
        return None, "Invalid password"

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

def register_user(request, form, help_courses, experience_courses, wolfnet_password=None, schedule_data=None):
    """
    Centralized service for user registration
    Returns (user, error_message) tuple
    """
    try:
        # Lower the threshold for registration - these are optional now
        if len(experience_courses) > 0 and len(experience_courses) < 2:
            return None, 'If selecting experience courses, please select at least 2.'
            
        if len(help_courses) > 0 and len(help_courses) < 2:
            return None, 'If selecting help courses, please select at least 2.'

        user = form.save()
        
        # Set WolfNet password if provided
        if wolfnet_password:
            from forum.forms import WolfNetSettingsForm
            wolfnet_form = WolfNetSettingsForm()
            encrypted_password = wolfnet_form.encrypt_password(wolfnet_password)
            user.userprofile.wolfnet_password = encrypted_password
            user.userprofile.save()
        
        # Set schedule courses if provided
        if schedule_data:
            from forum.models import Course
            for block_key, course_id in schedule_data.items():
                if course_id.isdigit():
                    try:
                        course = Course.objects.get(id=int(course_id))
                        setattr(user.userprofile, block_key, course)
                    except Course.DoesNotExist:
                        pass
            user.userprofile.save()
        
        # Add help courses
        for course_id in help_courses:
            if course_id.isdigit():
                UserCourseHelp.objects.create(
                    user=user,
                    course_id=int(course_id),
                    active=True
                )
            
        # Add experience courses
        for course_id in experience_courses:
            if course_id.isdigit():
                UserCourseExperience.objects.create(
                    user=user,
                    course_id=int(course_id)
                )
        
        login(request, user)
        return user, None
        
    except Exception as e:
        return None, str(e)