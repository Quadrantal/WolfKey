from django.contrib import admin
from django.contrib.auth.models import Group, Permission
from .models import Post, File, UserProfile, SavedPost, Solution, Course, User, UserCourseExperience, UserCourseHelp,UpdateAnnouncement, DailySchedule, SavedSolution, FollowedPost


# Register your models here.
admin.site.register(Post)
admin.site.register(File)
admin.site.register(UserProfile)
admin.site.register(SavedPost)
admin.site.register(FollowedPost)
admin.site.register(Solution)
admin.site.register(SavedSolution)
admin.site.register(Course)
admin.site.register(UserCourseExperience)
admin.site.register(UserCourseHelp)
admin.site.register(UpdateAnnouncement)
admin.site.register(User)
admin.site.register(DailySchedule)