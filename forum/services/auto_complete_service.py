"""
Service for handling auto-completion of courses from WolfNet
"""
import logging
from django.http import JsonResponse
from forum.tasks import auto_complete_courses

logger = logging.getLogger(__name__)


def auto_complete_user_courses(user, wolfnet_password=None):
    """
    Auto-complete courses for a logged-in user
    
    Args:
        user: Django User instance
        wolfnet_password: Optional wolfnet password (if not provided, will use stored one)
    
    Returns:
        dict: Result with success status and data/error
    """
    try:
        # Use provided password or get from user profile
        if wolfnet_password:
            password = wolfnet_password
        else:
            if not hasattr(user, 'userprofile') or not user.userprofile.wolfnet_password:
                return {
                    'success': False, 
                    'error': 'WolfNet password not configured. Please set up your WolfNet credentials in preferences.'
                }
            password = None  # Let the task retrieve it from the profile
        
        # Get user's school email
        school_email = user.school_email
        if not school_email:
            return {
                'success': False,
                'error': 'School email not found for user.'
            }
        
        # Start the auto-complete task
        if password:
            task = auto_complete_courses.delay(school_email, password)
        else:
            task = auto_complete_courses.delay(school_email)
        
        # Get the result (this will wait for completion)
        result = task.get(timeout=60)
        
        logger.info(f"Auto-complete courses result for {user.username}: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in auto_complete_user_courses for {user.username}: {str(e)}")
        return {
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }


def auto_complete_courses_registration(school_email, wolfnet_password):
    """
    Auto-complete courses during registration process
    
    Args:
        school_email: User's school email
        wolfnet_password: User's WolfNet password
    
    Returns:
        dict: Result with success status and data/error
    """
    try:
        if not wolfnet_password:
            return {
                'success': False, 
                'error': 'WolfNet password required for auto-completion.'
            }
            
        if not school_email:
            return {
                'success': False, 
                'error': 'School email required for auto-completion.'
            }
        
        # Start the auto-complete task
        task = auto_complete_courses.delay(school_email, wolfnet_password)
        
        # Get the result (this will wait for completion)
        result = task.get(timeout=60)
        
        logger.info(f"Auto-complete courses result for registration {school_email}: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in auto_complete_courses_registration for {school_email}: {str(e)}")
        return {
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }
