# views/comment_views.py
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from forum.models import Post, Solution, Comment
from forum.forms import CommentForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.serializers.json import DjangoJSONEncoder
from django.template.loader import render_to_string
from .notification_views import send_notification, send_comment_notifications
import json
from .utils import process_messages_to_json

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
            
            # Create the comment
            comment = Comment.objects.create(
                solution=solution, 
                author=request.user, 
                content=content,
                parent=parent_comment
            )

            # Send notifications
            send_comment_notifications(comment, solution, parent_comment)

            messages.success(request, 'Comment created succesfully')
            messages_data = process_messages_to_json(request)
            return JsonResponse({'status': 'success','messages': messages_data}, status=201)

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
            messages.success(request, 'Solution edited succesfully')
            messages_data = process_messages_to_json(request)
            return JsonResponse({'status': 'success','messages': messages_data}, status=200)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)

    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Solution deleted succesfully')
        messages_data = process_messages_to_json(request)
        return JsonResponse({'status': 'success','messages': messages_data}, status=200)

    return JsonResponse({'error': 'Invalid request'}, status=400)

def get_comments(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id)
    comments = Comment.objects.filter(solution=solution).order_by('created_at')

    def process_comment(comment):
        return {
            'id': comment.id,
            'content': comment.content,
            'author': {
                'name': comment.author.get_full_name(),
                'id': comment.author.id
            },
            'created_at': comment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'replies': [process_comment(reply) for reply in comment.replies.all()]
        }
    
    comments_data = [process_comment(comment) for comment in comments]

    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        print("--------------------------------------")
        return JsonResponse({
            'comments': comments_data,
            'html': render_to_string('forum/components/comments_list.html', {
                'comments': comments,
                'solution': solution
            }, request=request)
        })
    
    return render(request, 'forum/components/comments_list.html', {
        'comments': comments,
        'solution': solution
    })