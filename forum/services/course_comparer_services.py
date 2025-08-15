from django.http import JsonResponse
from forum.models import User, UserProfile

def get_user_schedule_service(user_id):
    """Get user's course schedule for comparison"""
    try:
        user = User.objects.get(id=user_id)
        
        try:
            profile = user.userprofile
            schedule_data = {
                'user_id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'profile_picture_url': user.userprofile.profile_picture.url,
                'schedule': {
                    '1A': {
                        'course': profile.block_1A.name if profile.block_1A else None,
                        'course_id': profile.block_1A.id if profile.block_1A else None,
                    },
                    '1B': {
                        'course': profile.block_1B.name if profile.block_1B else None,
                        'course_id': profile.block_1B.id if profile.block_1B else None,
                    },
                    '1D': {
                        'course': profile.block_1D.name if profile.block_1D else None,
                        'course_id': profile.block_1D.id if profile.block_1D else None,
                    },
                    '1E': {
                        'course': profile.block_1E.name if profile.block_1E else None,
                        'course_id': profile.block_1E.id if profile.block_1E else None,
                    },
                    '2A': {
                        'course': profile.block_2A.name if profile.block_2A else None,
                        'course_id': profile.block_2A.id if profile.block_2A else None,
                    },
                    '2B': {
                        'course': profile.block_2B.name if profile.block_2B else None,
                        'course_id': profile.block_2B.id if profile.block_2B else None,
                    },
                    '2C': {
                        'course': profile.block_2C.name if profile.block_2C else None,
                        'course_id': profile.block_2C.id if profile.block_2C else None,
                    },
                    '2D': {
                        'course': profile.block_2D.name if profile.block_2D else None,
                        'course_id': profile.block_2D.id if profile.block_2D else None,
                    },
                    '2E': {
                        'course': profile.block_2E.name if profile.block_2E else None,
                        'course_id': profile.block_2E.id if profile.block_2E else None,
                    },
                }
            }
            
            return schedule_data, None
            
        except UserProfile.DoesNotExist:
            return None, 'User profile not found'
            
    except User.DoesNotExist:
        return None, 'User not found'
