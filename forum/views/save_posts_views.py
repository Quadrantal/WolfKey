from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from forum.models import Post, SavedPost


@login_required
def save_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    SavedPost.objects.get_or_create(user=request.user, post=post)
    return redirect('post_detail', post_id=post.id)

@login_required
def unsave_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    SavedPost.objects.filter(user=request.user, post=post).delete()
    return redirect('post_detail', post_id=post.id)

@login_required
def saved_posts(request):
    posts = Post.objects.filter(saves__user=request.user)
    return render(request, 'forum/saved_posts.html', {'posts': posts})
