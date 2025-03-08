def notifications(request):
    if request.user.is_authenticated:
        notifications = request.user.notifications.filter(is_read=False).order_by('-created_at')[:5]
        return {
            'notifications': notifications,
            'unread_notifications_count': notifications.count()
        }
    return {}