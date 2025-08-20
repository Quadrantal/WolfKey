from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from forum.services.timetable_services import evaluate_multiple_schedules, generate_possible_schedules
from forum.models import Course, Block

@csrf_exempt
@require_http_methods(["GET"])
def all_courses_blocks_api(request):
    """
    API endpoint to get all courses organized by their available blocks.
    
    Returns:
    {
        "blocks": {
            "1A": ["Course 1", "Course 2"],
            "1B": ["Course 3"],
            ...
        }
    }
    """
    try:
        all_blocks = ['1A', '1B', '1D', '1E', '2A', '2B', '2C', '2D', '2E']
        
        blocks_data = {block_code: [] for block_code in all_blocks}
        
        # Determine grade threshold: use provided ?maxgrade= or user's profile grade if authenticated
        maxgrade_param = request.GET.get('maxgrade')
        user_grade = None
        try:
            if maxgrade_param is not None:
                user_grade = int(maxgrade_param)
            elif request.user and request.user.is_authenticated:
                try:
                    user_grade = int(request.user.userprofile.grade_level) if request.user.userprofile.grade_level is not None else None
                except Exception:
                    user_grade = None
        except ValueError:
            return JsonResponse({'error': 'Invalid maxgrade parameter'}, status=400)

        # Get all courses with their blocks, and filter by max_grade if user_grade provided
        courses_qs = Course.objects.prefetch_related('blocks').all()
        if user_grade is not None:
            # Include courses where max_grade is null (available to all) or max_grade >= user_grade
            from django.db.models import Q
            courses_qs = courses_qs.filter(Q(max_grade__isnull=True) | Q(max_grade__gte=user_grade))
        courses = courses_qs
        
        for course in courses:
            for block in course.blocks.all():
                if block.code in blocks_data:
                    blocks_data[block.code].append(course.name)
        
        return JsonResponse({'success': True, 'blocks': blocks_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def generate_schedules_api(request):
    """
    API endpoint to generate possible schedules for given courses.
    
    Expected POST data:
    {
        "requested_course_ids": [1, 2, 3],
        "required_course_ids": [2, 5]  # optional
    }
    """
    try:
        data = json.loads(request.body)
        requested_course_ids = data.get('requested_course_ids', [])
        if not requested_course_ids:
            return JsonResponse({'error': 'No courses requested'}, status=400)

        required_course_ids = data.get('required_course_ids', [])
        schedules = generate_possible_schedules(requested_course_ids, required_course_ids=required_course_ids)
        return JsonResponse({'success': True, 'schedules': schedules})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def evaluate_timetable_api(request):
    """
    API endpoint to evaluate timetable assignments using Hopcroft-Karp algorithm.
    
    Expected POST data:
    {
        "requested_course_ids": [1, 2, 3],
        "schedules": [ { ... } ],
        "required_course_ids": [2,5]  # optional
    }
    """
    try:
        data = json.loads(request.body)
        requested_course_ids = data.get('requested_course_ids', [])
        schedules = data.get('schedules', [])
        if not requested_course_ids:
            return JsonResponse({'error': 'No courses requested'}, status=400)
        if not schedules:
            return JsonResponse({'error': 'No schedules provided'}, status=400)

        # required_course_ids included for completeness; evaluation currently doesn't need it
        required_course_ids = data.get('required_course_ids', [])
        results = evaluate_multiple_schedules(requested_course_ids, schedules)
        return JsonResponse({'success': True, 'results': results})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
