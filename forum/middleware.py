from django.utils.deprecation import MiddlewareMixin

class UserRoleMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            request.user.is_moderator = request.user.groups.filter(name='Moderators').exists()