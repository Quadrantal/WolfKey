import json
from django.shortcuts import render, redirect
from forum.services.search_services import search_posts, search_users

def search_results_new_page(request):
    query = request.GET.get('q', '')
    if query:
        posts = search_posts(request.user, query)
        users = search_users(request.user, query)
        
        context = {
            'posts': posts,
            'users': users,
            'query': query
        }
        
        # Add comparison context if user is authenticated
        if request.user.is_authenticated:
            context['can_compare'] = True
            # Prepare current user data for comparison
            current_user_data = {
                'id': request.user.id,
                'username': request.user.username,
                'full_name': request.user.get_full_name(),
                'school_email': getattr(request.user, 'school_email', ''),
                'profile_picture_url': request.user.userprofile.profile_picture.url,
            }
            context['current_user_data'] = json.dumps(current_user_data)
        else:
            context['can_compare'] = False
        
        return render(request, 'forum/search_results.html', context)
    return redirect('all_posts')
