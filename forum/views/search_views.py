from django.shortcuts import render, redirect
from forum.services.search_services import search_posts_and_users_service

def search_results_new_page(request):
    query = request.GET.get('q', '')
    if query:
        posts, users = search_posts_and_users_service(request.user, query)
        return render(request, 'forum/search_results.html', {
            'posts': posts,
            'users': users,
            'query': query
        })
    return redirect('all_posts')
