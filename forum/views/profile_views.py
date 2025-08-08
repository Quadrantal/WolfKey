from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import logging
from forum.models import ( 
    UserProfile
)

from forum.forms import ( 
    UserProfileForm,
    WolfNetSettingsForm
)

# Import the new service layer
from forum.services.profile_service import (
    get_profile_context,
    update_profile_info,
    update_profile_picture,
    update_profile_courses,
    add_user_experience,
    add_user_help_request,
    remove_user_experience,
    remove_user_help_request,
)

# Import the auto-complete service
from forum.services.auto_complete_service import (
    auto_complete_user_courses_service,
    auto_complete_courses_registration_service
)

logger = logging.getLogger(__name__)


@login_required
def profile_view(request, username):
    if request.method == 'POST':
        success, msg = update_profile_info(request, username)
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect('profile', username=request.user.username)
    context = get_profile_context(request, username)
    return render(request, 'forum/profile.html', context)

@login_required
def upload_profile_picture(request):
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        update_profile_picture(request)
        return redirect('my_profile')
    return render(request, 'forum/upload_profile_picture.html')

@login_required
def my_profile(request):
    return redirect('profile', username=request.user.username)

@login_required
def add_experience(request):
    if request.method == 'POST':
        success, error = add_user_experience(request)
        if success:
            messages.success(request, 'Course experience added successfully!')
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': error})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@login_required
def add_help_request(request):
    if request.method == 'POST':
        success, error = add_user_help_request(request)
        if success:
            messages.success(request, 'Help request added successfully!')
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': error})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@login_required
def remove_experience(request, experience_id):
    if request.method == 'POST':
        success, msg = remove_user_experience(request, experience_id)
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    return redirect('profile', username=request.user.username)

@login_required
def remove_help_request(request, help_id):
    if request.method == 'POST':
        success, msg = remove_user_help_request(request, help_id)
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    return redirect('profile', username=request.user.username)

@login_required
def update_courses(request):
    if request.method == 'POST':
        success, msg = update_profile_courses(request)
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect('profile', username=request.user.username)
    return redirect('profile', username=request.user.username)

@login_required
@require_POST
def auto_complete_courses_view(request):
    """
    View to trigger auto-completion of courses from WolfNet for logged-in users
    """
    try:
        result = auto_complete_user_courses_service(request.user)
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        })

@require_POST
def auto_complete_courses_registration(request):
    """
    View to trigger auto-completion of courses from WolfNet during registration
    """
    try:
        # Get wolfnet password and school email from request
        wolfnet_password = request.POST.get('wolfnet_password')
        school_email = request.POST.get('school_email')
        
        result = auto_complete_courses_registration_service(school_email, wolfnet_password)
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        })