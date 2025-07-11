from django.shortcuts import render, redirect
from forum.services.search_services import search_posts, search_users

def search_results_new_page(request):
    query = request.GET.get('q', '')
    if query:
        posts = search_posts(request.user, query)
        users = search_users(request.user, query)
        return render(request, 'forum/search_results.html', {
            'posts': posts,
            'users': users,
            'query': query
        })
    return redirect('all_posts')
