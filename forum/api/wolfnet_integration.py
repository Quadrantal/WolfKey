"""
API endpoints for auto-completing courses from WolfNet
"""
import logging
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from forum.services.auto_complete_service import (
    auto_complete_user_courses_service,
    auto_complete_courses_registration_service
)


logger = logging.getLogger(__name__)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def auto_complete_courses_api(request):
    """
    Trigger auto-completion of courses from WolfNet for the current user
    
    Request body can contain:
        - wolfnet_password (optional): WolfNet password to use instead of stored one
    
    Returns:
        Response: Auto-completion result with courses or error
    """
    try:
        wolfnet_password = request.data.get('wolfnet_password')
        result = auto_complete_user_courses_service(request.user, wolfnet_password)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error in auto_complete_courses_api for {request.user.username}: {str(e)}")
        return Response({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([])  # No authentication required for registration
def auto_complete_courses_registration_api(request):
    """
    Trigger auto-completion of courses from WolfNet during registration
    
    Request body should contain:
        - wolfnet_password: User's WolfNet password
        - school_email: User's school email
    
    Returns:
        Response: Auto-completion result with courses or error
    """
    try:
        wolfnet_password = request.data.get('wolfnet_password')
        school_email = request.data.get('school_email')
        
        result = auto_complete_courses_registration_service(school_email, wolfnet_password)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error in auto_complete_courses_registration_api for {school_email}: {str(e)}")
        return Response({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
