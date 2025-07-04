import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from forum.services.schedule_services import (
    get_block_order_for_day,
    _parse_iso_date,
    _convert_to_sheet_date_format
)

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