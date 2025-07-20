"""
URL configuration for student_forum project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path, include
from forum.views.auth_views import register, login_view, logout_view
from forum.views.auth_views import (
    CustomPasswordResetView,
    CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetCompleteView,
)
from forum.views.post_views import (
    post_detail, 
    edit_post, 
    delete_post, 
    create_post,
    like_post,
    unlike_post
)

from forum.views.feed_views import (
    all_posts,
    for_you,
    my_posts
)
from forum.views.solution_views import (
    create_solution,
    delete_solution,
    edit_solution,
    upvote_solution, 
    downvote_solution,
    accept_solution,
    get_sorted_solutions,
    
)
from forum.views.search_views import search_results_new_page
from forum.views.profile_views import (
    add_experience,
    remove_experience,
    add_help_request,
    remove_help_request,
    my_profile,
    profile_view,
    update_courses,
    upload_profile_picture,
    auto_complete_courses_view
)
from forum.services.course_services import (
    course_search
)
from forum.views.save_views import (
    follow_post,
    unfollow_post,
    followed_posts,
    save_solution,
    saved_solutions,
)
from forum.views.notification_views import (
    all_notifications,
    mark_notification_read,
    mark_all_notifications_read
)
from forum.views.updates_views import acknowledge_update
from forum.services.utils import upload_image

from forum.views.comments_views import (
    create_comment,
    edit_comment,
    delete_comment,
    get_comments
)
from forum.views.course_comparer_views import (
    course_comparer
)
from forum.api.schedule import(
    get_daily_schedule,
    get_user_schedule_api
)
from forum.api.auth import(
    api_login,
    api_register,
    api_upload_image,
    search_users_api
)
from forum.services.schedule_services import (
    is_ceremonial_uniform_required
)
from forum.views.api_views import(
    get_csrf_token,
    api_logout,
    for_you_api,
    api_post_detail,
    api_delete_post,
    api_create_post,
    api_update_post
)

from django.views.generic import RedirectView

from forum.views.about_view import about_view

urlpatterns = [

    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'forum/images/WolfkeyLogo.ico')),
    # Post related URLs
    path('', for_you, name='for_you'),
    path('all-posts/', all_posts, name='all_posts'),
    path('post/<int:post_id>/', post_detail, name='post_detail'),
    path('post/<int:post_id>/edit/', edit_post, name='edit_post'),
    path('post/<int:post_id>/delete/', delete_post, name='delete_post'),
    path('post/create/', create_post, name='create_post'),
    path('posts/<int:post_id>/like/', like_post, name='like_post'),
    path('posts/<int:post_id>/unlike/', unlike_post, name='unlike_post'),

    path('solution/<int:solution_id>/edit/', edit_solution, name='edit_solution'),
    path('solution/<int:solution_id>/delete/', delete_solution, name='delete_solution'),
    path('solution/<int:post_id>/create/', create_solution, name='create_solution'),
    path('post/<int:post_id>/solutions/sorted/', get_sorted_solutions, name='get_sorted_solutions'),


    path('comment/create/<int:solution_id>/', create_comment, name='create_comment'),
    path('comment/edit/<int:comment_id>/', edit_comment, name='edit_comment'),
    path('comment/delete/<int:comment_id>/', delete_comment, name='delete_comment'),

    path('solution/<int:solution_id>/comments/', get_comments, name='get_solution_comments'),

    path('about', about_view, name = 'site_info'),
    
    # Auth related URLs
    path('register/', register, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Voting URLs
    path('solution/<int:solution_id>/upvote/', upvote_solution, name='upvote_solution'),
    path('solution/<int:solution_id>/downvote/', downvote_solution, name='downvote_solution'),
    path('solution/<int:solution_id>/accept/', accept_solution, name='accept_solution'),
    
    # Search URLs
    path('search/', search_results_new_page, name='search_posts'),
    path('search-results/', search_results_new_page, name='search_results_new_page'),
    
    # Media upload URL
    path('upload-image/', upload_image, name='upload_image'),
    
    # Profile URLs
    path('profile/upload-picture/', upload_profile_picture, name='upload_profile_picture'),
    path('my-profile/', my_profile, name='my_profile'),
    path('profile/<str:username>/', profile_view, name='profile'),
    path('update-courses/', update_courses, name='update_courses'),
    path('auto-complete-courses/', auto_complete_courses_view, name='auto_complete_courses'),
    
    # Course management URLs
    path('courses/experience/add/', add_experience, name='add_experience'),
    path('courses/experience/remove/<int:experience_id>/', remove_experience, name='remove_experience'),
    path('courses/help/add/', add_help_request, name='add_help_request'),
    path('courses/help/remove/<int:help_id>/', remove_help_request, name='remove_help_request'),
    path('api/courses/', course_search, name='course-search'),
    
    # Course comparer URLs
    path('course-comparer/', course_comparer, name='course_comparer'),
    path('api/search-users/', search_users_api, name='search_users_api'),
    path('api/user-schedule/<int:user_id>/', get_user_schedule_api, name='get_user_schedule_api'),

    # Saved posts URLs
    path('followed-posts/', followed_posts, name='followed_posts'),
    path('my-posts/', my_posts, name='my_posts'),
    path('follow-post/<int:post_id>/', follow_post, name='follow_post'),
    path('unfollow-post/<int:post_id>/', unfollow_post, name='unfollow_post'),
    path('save-solution/<int:solution_id>/', save_solution, name='save_solution'),
    path('saved-solutions/', saved_solutions, name='saved_solutions'),

    # API URLs
    path('api/acknowledge-update/', acknowledge_update, name='acknowledge_update'),
    
    # Notification URLs
    path('notifications/', all_notifications, name='all_notifications'),
    path('notifications/mark-all-read/', mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:notification_id>/read/', mark_notification_read, name='mark_notification_read'),
    
    # Admin URL
    path('admin/', admin.site.urls),

    path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('api/logout/', api_logout, name='api_logout'),
    path('api/schedules/daily/<str:target_date>/', get_daily_schedule),
    path('api/schedules/uniform/<str:target_date>/', is_ceremonial_uniform_required),
    path('api/schedules/uniform/<str:target_date>/', is_ceremonial_uniform_required),
    path('api/for-you/', for_you_api, name='for_you_api'),
    path('api/csrf/', get_csrf_token),
    path('api/posts/<int:post_id>/', api_post_detail, name='api_post_detail'),
    path('api/posts/', api_create_post, name='api_create_post'),
    path('api/posts/<int:post_id>/update/', api_update_post, name='api_update_post'),
    path('api/posts/<int:post_id>/delete/', api_delete_post, name='api_delete_post'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)