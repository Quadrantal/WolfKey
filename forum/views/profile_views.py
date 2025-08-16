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


@login_required
@require_POST
@csrf_exempt
def check_wolfnet_password_view(request):
    """
    Check if WolfNet password is valid for the current user
    """
    try:
        import json
        data = json.loads(request.body)
        wolfnet_password = data.get('wolfnet_password')
        
        if not wolfnet_password:
            return JsonResponse({
                'success': False,
                'error': 'WolfNet password is required'
            })
        
        school_email = request.user.school_email
        if not school_email:
            return JsonResponse({
                'success': False,
                'error': 'School email is required for WolfNet verification'
            })
        
        from forum.tasks import check_wolfnet_password
        
        # Check if result backend is disabled - if so, run synchronously
        from django.conf import settings
        result_backend_disabled = getattr(settings, 'CELERY_RESULT_BACKEND', None) is None
        
        if result_backend_disabled:
            # Run task synchronously when result backend is disabled
            verification_result = check_wolfnet_password(school_email, wolfnet_password)
        else:
            # Run asynchronously with result retrieval
            result = check_wolfnet_password.delay(school_email, wolfnet_password)
            verification_result = result.get(timeout=60)
        
        # If verification is successful, save the password
        if verification_result.get('success'):
            try:
                user_profile = request.user.userprofile
                from forum.forms import WolfNetSettingsForm
                wolfnet_form = WolfNetSettingsForm()
                encrypted_password = wolfnet_form.encrypt_password(wolfnet_password)
                user_profile.wolfnet_password = encrypted_password
                user_profile.save()
                verification_result['message'] = 'WolfNet password verified and saved successfully!'
            except Exception as save_error:
                logging.getLogger(__name__).error(f"Error saving WolfNet password for {request.user.username}: {str(save_error)}")
                # Still return success for verification, but note the save issue
                verification_result['message'] = 'WolfNet password verified successfully, but there was an issue saving it. Please try again.'
        
        return JsonResponse(verification_result)
            
    except Exception as e:
        logging.getLogger(__name__).error(f"Error in check_wolfnet_password_view for {request.user.username}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'An error occurred while checking WolfNet password: {str(e)}'
        })