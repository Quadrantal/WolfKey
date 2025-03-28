# views/comment_views.py
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from forum.models import Post, Solution, Comment
from forum.forms import CommentForm

@login_required
def create_comment(request, solution_id):
    if request.method == 'POST':
        solution = get_object_or_404(Solution, id=solution_id)
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.solution = solution
            comment.author = request.user
            comment.save()
            return JsonResponse({'message': 'Comment created successfully.'}, status=201)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)

    if request.method == 'POST':
        comment_form = CommentForm(request.POST, instance=comment)
        if comment_form.is_valid():
            comment_form.save()
            return JsonResponse({'message': 'Comment updated successfully.'}, status=200)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)

    if request.method == 'POST':
        comment.delete()
        return JsonResponse({'message': 'Comment deleted successfully.'}, status=200)

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def upvote_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if not CommentUpvote.objects.filter(comment=comment, user=request.user).exists():
        CommentUpvote.objects.create(comment=comment, user=request.user)
        comment.upvotes += 1
        comment.save()
        messages.success(request, 'Comment upvoted successfully!')
    else:
        messages.warning(request, 'You have already upvoted this comment.')
    return redirect('post_detail', post_id=comment.solution.post.id)