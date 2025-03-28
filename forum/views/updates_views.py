import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required 
from forum.models import UpdateAnnouncement, UserUpdateView 

@login_required
def acknowledge_update(request):
    try:
        data = json.loads(request.body)
        update_id = data.get('update_id')
        update = UpdateAnnouncement.objects.get(id=update_id)
        UserUpdateView.objects.get_or_create(
            user=request.user,
            update=update
        )
        return JsonResponse({'success': True})
    except UpdateAnnouncement.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Update not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)