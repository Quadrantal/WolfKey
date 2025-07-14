import json
from django.shortcuts import get_object_or_404
from forum.models import User, Course, Post, Solution, UserCourseExperience, UserCourseHelp, UserProfile
from forum.forms import UserCourseExperienceForm, UserCourseHelpForm
from forum.services.utils import detect_bad_words

def get_profile_context(request, username):
    profile_user = get_object_or_404(User, username=username)
    recent_posts = Post.objects.filter(
        author=profile_user,
        is_anonymous=False
    ).order_by('-created_at')[:3]
    posts_count = Post.objects.filter(author=profile_user).count()
    solutions_count = Solution.objects.filter(author=profile_user).count()

    initial_courses = {}
    blocks = ['1A', '1B', '1D', '1E', '2A', '2B', '2C', '2D', '2E']
    for block in blocks:
        course = getattr(profile_user.userprofile, f'block_{block}', None)
        if course:
            initial_courses[f'block_{block}'] = {
                'id': course.id,
                'name': course.name,
                'category': course.category,
            }
    initial_courses_json = json.dumps(initial_courses)

    experienced_courses = UserCourseExperience.objects.filter(user=profile_user)
    help_needed_courses = UserCourseHelp.objects.filter(user=profile_user, active=True)
    experienced_courses_json = json.dumps([experience.course.id for experience in experienced_courses])
    help_needed_courses_json = json.dumps([help.course.id for help in help_needed_courses])

    context = {
        'profile_user': profile_user,
        'recent_posts': recent_posts,
        'experience_form': UserCourseExperienceForm(user=profile_user),
        'help_form': UserCourseHelpForm(user=profile_user),
        'posts_count': posts_count,
        'solutions_count': solutions_count,
        'experienced_courses': experienced_courses,
        'help_needed_courses': help_needed_courses,
        'experienced_courses_json': experienced_courses_json,
        'help_needed_courses_json': help_needed_courses_json,
        'initial_courses_json': initial_courses_json,
    }
    
    # Add comparison data if viewing someone else's profile
    if request.user.is_authenticated and request.user != profile_user:
        initial_users = [
            {
                'id': request.user.id,
                'username': request.user.username,
                'full_name': request.user.get_full_name(),
                'school_email': request.user.school_email,
                'profile_picture_url': request.user.userprofile.profile_picture.url,
            },
            {
                'id': profile_user.id,
                'username': profile_user.username,
                'full_name': profile_user.get_full_name(),
                'school_email': profile_user.school_email,
                'profile_picture_url': profile_user.userprofile.profile_picture.url,
            }
        ]
        context['initial_users'] = json.dumps(initial_users)
        context['can_compare'] = True
    else:
        context['can_compare'] = False
    
    return context

def update_profile_info(request, username):
    profile_user = get_object_or_404(User, username=username)
    try:
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.personal_email = request.POST.get('personal_email', request.user.personal_email)
        request.user.phone_number = request.POST.get('phone_number', request.user.phone_number)
        request.user.save()

        if 'bio' in request.POST:
            bio = request.POST.get('bio', profile_user.userprofile.bio)
            detect_bad_words(bio)
            profile_user.userprofile.bio = bio
            profile_user.userprofile.save()

        hue_value = request.POST.get('background_hue', profile_user.userprofile.background_hue)
        profile_user.userprofile.background_hue = int(hue_value)
        profile_user.userprofile.save()

        return True, 'Profile updated successfully!'
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f'Error updating profile: {str(e)}'

def update_profile_picture(request):
    profile = request.user.userprofile
    profile.profile_picture = request.FILES['profile_picture']
    profile.save()

def update_profile_courses(request):
    profile = request.user.userprofile
    try:
        for key, value in request.POST.items():
            if key.startswith("block_"):
                block = key.replace("block_", "")
                course_id = value
                if course_id == 'NOCOURSE':
                    setattr(profile, f'block_{block}', None)
                else:
                    course = Course.objects.get(id=course_id)
                    setattr(profile, f'block_{block}', course)
        profile.save()
        return True, 'Courses updated successfully!'
    except Course.DoesNotExist:
        return False, f"Course with ID {course_id} does not exist."
    except Exception as e:
        return False, f"Error updating courses: {str(e)}"

def add_user_experience(request):
    form = UserCourseExperienceForm(request.POST, user=request.user)
    if form.is_valid():
        experience = form.save(commit=False)
        experience.user = request.user
        experience.save()
        return True, None
    else:
        return False, 'Form is invalid.'

def add_user_help_request(request):
    form = UserCourseHelpForm(request.POST, user=request.user)
    if form.is_valid():
        help_request = form.save(commit=False)
        help_request.user = request.user
        help_request.save()
        return True, None
    else:
        return False, 'Form is invalid.'

def remove_user_experience(request, experience_id):
    try:
        experience = get_object_or_404(UserCourseExperience, id=experience_id, user=request.user)
        experience.delete()
        return True, 'Course experience removed successfully!'
    except UserCourseExperience.DoesNotExist:
        return False, 'Course experience not found.'
    except Exception as e:
        return False, f'Error removing course experience: {str(e)}'

def remove_user_help_request(request, help_id):
    try:
        help_request = get_object_or_404(UserCourseHelp, id=help_id, user=request.user)
        help_request.delete()
        return True, 'Help request removed successfully!'
    except UserCourseHelp.DoesNotExist:
        return False, 'Help request not found.'
    except Exception as e:
        return False, f'Error removing help request: {str(e)}'
