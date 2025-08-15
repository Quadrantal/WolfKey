"""
Expo Push Notification Service
"""
import requests
import logging
from django.conf import settings
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ExpoPushNotificationService:
    """
    Service for sending push notifications via Expo Push Notification API
    """
    
    EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
    
    def __init__(self):
        self.access_token = getattr(settings, 'EXPO_ACCESS_TOKEN', None)
    
    def send_push_notification(
        self, 
        to: str, 
        title: str, 
        body: str, 
        data: Optional[Dict] = None,
        badge: Optional[int] = None,
        sound: str = 'default'
    ) -> Dict:
        """
        Send a push notification to a single Expo push token
        
        Args:
            to: Expo push token
            title: Notification title
            body: Notification body
            data: Custom data to send with notification
            badge: Badge count to display on app icon
            sound: Sound to play ('default' or None for silent)
        
        Returns:
            Dict with response from Expo API
        """
        if not to or not to.startswith('ExponentPushToken'):
            logger.warning(f"Invalid Expo push token format: {to}")
            return {'success': False, 'error': 'Invalid push token format'}
        
        payload = {
            'to': to,
            'title': title,
            'body': body,
            'data': data or {},
            'badge': badge,
            'sound': sound,
            'priority': 'high',
            'channelId': 'default'
        }
        
        headers = {
            'Accept': 'application/json',
            'Accept-encoding': 'gzip, deflate',
            'Content-Type': 'application/json',
        }
        
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        try:
            response = requests.post(
                self.EXPO_PUSH_URL,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            response_data = response.json()
            
            if response.status_code == 200:
                if 'data' in response_data and len(response_data['data']) > 0:
                    ticket = response_data['data'][0]
                    if ticket.get('status') == 'ok':
                        logger.info(f"Push notification sent successfully to {to}")
                        return {'success': True, 'ticket': ticket}
                    else:
                        error_msg = ticket.get('message', 'Unknown error')
                        logger.error(f"Expo API error: {error_msg}")
                        return {'success': False, 'error': error_msg}
                else:
                    logger.error("No data in Expo API response")
                    return {'success': False, 'error': 'No data in response'}
            else:
                logger.error(f"HTTP error {response.status_code}: {response_data}")
                return {'success': False, 'error': f'HTTP {response.status_code}'}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending push notification: {str(e)}")
            return {'success': False, 'error': f'Network error: {str(e)}'}
        except Exception as e:
            logger.error(f"Unexpected error sending push notification: {str(e)}")
            return {'success': False, 'error': f'Unexpected error: {str(e)}'}
    
    def send_bulk_push_notifications(self, notifications: List[Dict]) -> List[Dict]:
        """
        Send multiple push notifications in a single request
        
        Args:
            notifications: List of notification dictionaries with 'to', 'title', 'body', etc.
        
        Returns:
            List of response dictionaries
        """
        if not notifications:
            return []
        
        headers = {
            'Accept': 'application/json',
            'Accept-encoding': 'gzip, deflate',
            'Content-Type': 'application/json',
        }
        
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        try:
            response = requests.post(
                self.EXPO_PUSH_URL,
                json=notifications,
                headers=headers,
                timeout=30
            )
            
            response_data = response.json()
            
            if response.status_code == 200 and 'data' in response_data:
                results = []
                for i, ticket in enumerate(response_data['data']):
                    if ticket.get('status') == 'ok':
                        results.append({'success': True, 'ticket': ticket})
                    else:
                        error_msg = ticket.get('message', 'Unknown error')
                        results.append({'success': False, 'error': error_msg})
                
                logger.info(f"Sent {len(notifications)} bulk push notifications")
                return results
            else:
                logger.error(f"Bulk push notification error: {response_data}")
                return [{'success': False, 'error': 'Bulk request failed'} for _ in notifications]
                
        except Exception as e:
            logger.error(f"Error sending bulk push notifications: {str(e)}")
            return [{'success': False, 'error': str(e)} for _ in notifications]


expo_push_service = ExpoPushNotificationService()

def send_push_notification_to_user(user, title: str, body: str, data: Optional[Dict] = None) -> Dict:
    """
    Send a push notification to a specific user
    
    Args:
        user: Django User instance
        title: Notification title
        body: Notification body  
        data: Custom data to send with notification
    
    Returns:
        Dict with response from Expo API
    """
    try:
        user_profile = user.userprofile
        if not user_profile.expo_push_token:
            logger.info(f"User {user.get_full_name()} has no push token registered")
            return {'success': False, 'error': 'No push token registered'}
        
        # Get unread notification count for badge
        unread_count = user.notifications.filter(is_read=False).count()
        
        return expo_push_service.send_push_notification(
            to=user_profile.expo_push_token,
            title=title,
            body=body,
            data=data or {},
            badge=unread_count
        )
        
    except Exception as e:
        logger.error(f"Error sending notification to user {user.id}: {str(e)}")
        return {'success': False, 'error': str(e)}

def send_bulk_notifications_to_users(users_data: List[Dict]) -> List[Dict]:
    """
    Send push notifications to multiple users
    
    Args:
        users_data: List of dicts with 'user', 'title', 'body', 'data' keys
    
    Returns:
        List of response dictionaries
    """
    notifications = []
    
    for user_data in users_data:
        user = user_data['user']
        try:
            user_profile = user.userprofile
            if user_profile.expo_push_token:
                unread_count = user.notifications.filter(is_read=False).count()
                
                notification = {
                    'to': user_profile.expo_push_token,
                    'title': user_data['title'],
                    'body': user_data['body'],
                    'data': user_data.get('data', {}),
                    'badge': unread_count,
                    'sound': 'default',
                    'priority': 'high',
                    'channelId': 'default'
                }
                notifications.append(notification)
        except Exception as e:
            logger.error(f"Error preparing notification for user {user.id}: {str(e)}")
    
    if notifications:
        return expo_push_service.send_bulk_push_notifications(notifications)
    
    return []
