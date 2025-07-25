"""
API endpoints for auto-completing courses from WolfNet
"""
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from forum.services.auto_complete_service import (
    auto_complete_user_courses,
    auto_complete_courses_registration
)

logger = logging.getLogger(__name__)


@login_required
@require_POST
def auto_complete_courses_api(request):
    """
    API endpoint to trigger auto-completion of courses from WolfNet for logged-in users
    """
    try:
        result = auto_complete_user_courses(request.user)
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in auto_complete_courses_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        })


@csrf_exempt
@require_POST
def auto_complete_courses_registration_api(request):
    """
    API endpoint to trigger auto-completion of courses from WolfNet during registration
    """
    try:
        # Get wolfnet password and school email from request
        wolfnet_password = request.POST.get('wolfnet_password')
        school_email = request.POST.get('school_email')
        
        result = auto_complete_courses_registration(school_email, wolfnet_password)
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in auto_complete_courses_registration_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        })
