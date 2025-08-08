import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from forum.services.schedule_services import (
    get_block_order_for_day,
    _parse_iso_date,
    _convert_to_sheet_date_format,
    is_ceremonial_uniform_required
)
from forum.services.course_comparer_services import get_user_schedule_service

@ensure_csrf_cookie
@require_http_methods(["GET"])
def get_daily_schedule(request, target_date):
    try:
        schedule = get_block_order_for_day(target_date)
        date_obj = _parse_iso_date(target_date)
        formatted_date = _convert_to_sheet_date_format(date_obj)
        
        return JsonResponse({
            'date': formatted_date,
            'blocks': schedule['blocks'],
            'times': schedule['times']
        })
    except ValueError as e:
        return JsonResponse({
            'error': 'Invalid date format. Expected YYYY-MM-DD',
            'details': str(e)
        }, status=400)
    except Exception as e:
        print(f"Error in get_daily_schedule: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_user_schedule_api(request, user_id):
    """Get user's course schedule for comparison"""
    schedule_data, error = get_user_schedule_service(user_id)
    
    if error:
        return JsonResponse({'error': error}, status=404)
    
    return JsonResponse(schedule_data)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def check_ceremonial_uniform(request, target_date):
    """Check if ceremonial uniform is required for a specific date"""

    try:
        is_required = is_ceremonial_uniform_required(user=request.user, iso_date=target_date)
        date_obj = _parse_iso_date(target_date)
        formatted_date = _convert_to_sheet_date_format(date_obj)
        
        return Response({
            'date': formatted_date,
            'ceremonial_uniform_required': is_required
        }, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({
            'error': 'Invalid date format. Expected YYYY-MM-DD',
            'details': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(f"Error in check_ceremonial_uniform: {e}")
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)