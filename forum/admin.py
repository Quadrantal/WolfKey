from django.contrib import admin
from .models import Post, Tag, File, UserProfile, SavedPost, Solution, Course, User, UserCourseExperience, UserCourseHelp,UpdateAnnouncement, Comment, FollowedPost, SavedSolution
from django.contrib.auth.admin import UserAdmin

# Register your models here.
admin.site.register(Post)
admin.site.register(Tag)
admin.site.register(File)
admin.site.register(UserProfile)
admin.site.register(SavedPost)
admin.site.register(FollowedPost)
admin.site.register(Solution)
admin.site.register(SavedSolution)
admin.site.register(Comment)
admin.site.register(Course)
admin.site.register(UserCourseExperience)
admin.site.register(UserCourseHelp)
admin.site.register(UpdateAnnouncement)
admin.site.register(User, UserAdmin)


def create_moderator_group():
    moderator_group, created = Group.objects.get_or_create(name='Moderators')
    if created:
        permissions = [
            'can_delete_posts',
            'can_edit_posts',
            'can_ban_users',
            'can_pin_posts'
        ]
        for perm in permissions:
            moderator_group.permissions.add(Permission.objects.get(codename=perm))