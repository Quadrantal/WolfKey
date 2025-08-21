from django.shortcuts import render
from django.views.decorators.http import require_http_methods
import json


@require_http_methods(["GET"])
def timetable_assigner(request):
    """Render the timetable assigner page and pass initial course selections from the user's profile."""
    user = request.user
    profile = getattr(user, 'userprofile', None)

    blocks = ['1A', '1B', '1D', '1E', '2A', '2B', '2C', '2D', '2E']
    initial = {}

    if profile:
        # Map profile FK fields to blocks
        mapping = {
            '1A': profile.block_1A,
            '1B': profile.block_1B,
            '1D': profile.block_1D,
            '1E': profile.block_1E,
            '2A': profile.block_2A,
            '2B': profile.block_2B,
            '2C': profile.block_2C,
            '2D': profile.block_2D,
            '2E': profile.block_2E,
        }

        for b in blocks:
            course = mapping.get(b)
            if course and getattr(course, 'name', None) and 'study' not in course.name.lower():
                initial[b] = {
                    'id': course.id,
                    'name': course.name,
                    'category': course.category if hasattr(course, 'category') else 'Misc',
                    'experienced_count': 0
                }
            else:
                initial[b] = None
    else:
        for b in blocks:
            initial[b] = None

    context = {
        'initial_selections_json': json.dumps(initial)
    }
    return render(request, 'forum/timetable_assigner.html', context)
