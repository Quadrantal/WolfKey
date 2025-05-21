from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from forum.models import Post, SavedPost, FollowedPost, Solution, SavedSolution
from forum.views.utils import process_post_preview, add_course_context
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

    for post in posts:
        post.preview_text = process_post_preview(post)

    return render(request, 'forum/followed_posts.html', {'posts': posts})

@login_required
def save_solution(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id)
    saved, created = SavedSolution.objects.get_or_create(user=request.user, solution=solution)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'saved': True})
    
    return redirect('post_detail', post_id=solution.post.id)

@login_required
def unsave_solution(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id)
    SavedSolution.objects.filter(user=request.user, solution=solution).delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'saved': False})
    
    return redirect('post_detail', post_id=solution.post.id)

@login_required
def saved_solutions(request):
    solutions = Solution.objects.filter(saves__user=request.user)

    for solution in solutions:
        solution = json.loads(solution)
        solution.preview_text = process_post_preview(solution)

    print(solutions[0].preview_text)
    return render(request, 'forum/saved_solutions.html', {'solutions': solutions})
