from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from forum.models import Post, SavedPost, FollowedPost, Solution, SavedSolution
from forum.services.utils import process_post_preview, add_course_context, annotate_post_card_context
from forum.services.solution_services import save_solution_service
import json

@login_required
def follow_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    followed, created = FollowedPost.objects.get_or_create(user=request.user, post=post)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        followers_count = post.followers.count()
        return JsonResponse({
            'success': True, 
            'followed': True,
            'followers_count': followers_count
        })
    
    return redirect('post_detail', post_id=post.id)

@login_required
def unfollow_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    FollowedPost.objects.filter(user=request.user, post=post).delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        followers_count = post.followers.count()
        return JsonResponse({
            'success': True, 
            'followed': False,
            'followers_count': followers_count
        })
    
    return redirect('post_detail', post_id=post.id)

@login_required
def followed_posts(request):
    posts = Post.objects.filter(followers__user=request.user)

    posts = annotate_post_card_context(posts, request.user)

    return render(request, 'forum/followed_posts.html', {'posts': posts})

@login_required
def save_solution(request, solution_id):
    if request.method == 'POST':
        result = save_solution_service(request.user, solution_id)
        
        if 'error' in result:
            return JsonResponse({
                'success': False,
                'message': result['error'],
                'messages': result.get('messages', [])
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'saved': result['saved'],
            'messages': result.get('messages', [])
        })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method',
        'messages': [{'message': 'Invalid request method', 'tags': 'error'}]
    }, status=400)

@login_required
def saved_solutions(request):
    solutions = Solution.objects.filter(saves__user=request.user)

    for solution in solutions:
        solution.preview_text = process_post_preview(solution)

    return render(request, 'forum/saved_solutions.html', {'solutions': solutions})
