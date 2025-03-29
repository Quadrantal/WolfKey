# views/comment_views.py
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from forum.models import Post, Solution, Comment
from forum.forms import CommentForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
import json

@login_required
def create_comment(request, solution_id):
    if request.method == 'POST':
        solution = get_object_or_404(Solution, id=solution_id)
        data = json.loads(request.body) 
        content = data.get('content')
        parent_id = data.get('parent_id') 
        
        if content:
            parent_comment = None
            if parent_id:
                parent_comment = get_object_or_404(Comment, id=parent_id)
            
            comment = Comment.objects.create(
                solution=solution, 
                author=request.user, 
                content=content,
                parent=parent_comment
            )
            return JsonResponse({'message': 'Comment created successfully.', 'comment_id': comment.id}, status=201)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)

    if request.method == 'POST':
        data = json.loads(request.body)
        content = data.get('content')

        if content:
            comment.content = content
            comment.save()
            return JsonResponse({'message': 'Comment updated successfully.'}, status=200)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)

    if request.method == 'POST':
        comment.delete()
        return JsonResponse({'message': 'Comment deleted successfully.'}, status=200)

    return JsonResponse({'error': 'Invalid request'}, status=400)