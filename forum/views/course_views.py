from django.http import JsonResponse
from django.db.models import Q
from forum.models import Course, UserCourseExperience, UserCourseHelp

def get_user_courses(user):
    """Get user's experienced and help-needed courses"""
    if not user.is_authenticated:
        return [], []
        
    experienced_courses = Course.objects.filter(
        id__in=UserCourseExperience.objects.filter(
            user=user
        ).values_list('course_id', flat=True)
    )
    
    help_needed_courses = Course.objects.filter(
        id__in=UserCourseHelp.objects.filter(
            user=user,
            active=True
        ).values_list('course_id', flat=True)
    )
    
    return experienced_courses, help_needed_courses


def course_search(request):
    query = request.GET.get('q', '')
    courses = Course.objects.filter(
        name__icontains=query
    ) if query else Course.objects.all()
    
    data = [{
        "id": course.id,
        "name": course.name,
        "code": course.code,
        "category": course.category,
        "experienced_count" : UserCourseExperience.objects.filter(course=course).count()

    } for course in courses[:10]] 
    
    return JsonResponse(data, safe=False)