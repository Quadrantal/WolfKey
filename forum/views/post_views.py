from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import F, Case, When, IntegerField
from django.core.serializers.json import DjangoJSONEncoder
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
import json
import logging
from django.http import JsonResponse
from django.utils.html import escape
from forum.models import Post, Solution, Comment, Course
from forum.forms import SolutionForm, CommentForm, PostForm
from .utils import selective_quote_replace, detect_bad_words
from django.contrib import messages
from .notification_views import send_course_notifications
from django.http import HttpResponseForbidden


logger = logging.getLogger(__name__)

@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            try:
                post = form.save(commit=False)
                post.author = request.user

                # Handle content
                content_json = request.POST.get('content')
                content_data = json.loads(content_json) if content_json else {}

                # Validate post content
                if isinstance(content_data, dict) and 'blocks' in content_data:
                    blocks = content_data.get('blocks', [])
                    if (len(blocks) == 1 and blocks[0].get('type') == 'paragraph' and not blocks[0].get('data', {}).get('text', '').strip()) or len(blocks) == 0:
                        messages.error(request, 'Post content cannot be empty.')
                        return redirect('create_post')
                detect_bad_words(content_data) 
                post.content = content_data

                # Save post and handle courses
                post.save()
                course_ids = request.POST.getlist('courses')
                if course_ids:
                    courses = Course.objects.filter(id__in=course_ids)
                    post.courses.set(courses)
                    send_course_notifications(post, courses)

                return redirect(post.get_absolute_url())
            except ValueError as e:
                # Catch bad word detection errors
                messages.error(request, f"Content contains inappropriate language: {str(e)}")
            except Exception as e:
                # Catch other errors
                messages.error(request, f"Error creating post: {str(e)}")
        else:
            messages.error(request, f"Form validation failed: {form.errors}")
    else:
        form = PostForm()

    return render(request, 'forum/post_form.html', {'form': form, 'action': 'Create'})

@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    solutions = post.solutions.annotate(
        vote_score=F('upvotes') - F('downvotes')
    ).order_by(
        Case(
            When(id=post.accepted_solution_id, then=0),
            default=1,
            output_field=IntegerField(),
        ),
        '-vote_score',
        '-created_at'
    )
    
    has_solution = Solution.objects.filter(post=post, author=request.user).exists()
    # Process post content
    content_json = json.dumps(post.content, cls=DjangoJSONEncoder)
    
    processed_solutions = []
    for solution in solutions:
        try:
            solution_content = solution.content
            if isinstance(solution_content, str):
                solution_content = selective_quote_replace(solution_content)
                solution_content = json.loads(solution_content)
            
            # Get comments for this solution
            comments = solution.comments.select_related('author').order_by('created_at')
            processed_comments = []
            
            for comment in comments:
                processed_comments.append({
                    'id': comment.id,
                    'content': comment.content,
                    'author': f"{comment.author.first_name} {comment.author.last_name}",
                    'created_at': comment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    'parent_id': comment.parent_id,
                    'depth' : comment.get_depth(),
                })
            root_comments_count = sum(1 for comment in comments if comment.get_depth() == 0)
            
            processed_solutions.append({
                'id': solution.id,
                'content': solution_content,  
                'author': f"{solution.author.first_name} {solution.author.last_name}",
                'created_at': solution.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                'upvotes': solution.upvotes,
                'downvotes': solution.downvotes,
                'comments': processed_comments,
                "root_comments_count": root_comments_count,

            })
        except Exception as e:
            logger.error(f"Error processing solution {solution.id}: {e}")
            processed_solutions.append({
                'id': solution.id,
                'content': {
                    "blocks": [{"type": "paragraph", "data": {"text": "Error loading solution content"}}]
                },
                'author': f"{solution.author.first_name} {solution.author.last_name}",
                'created_at': solution.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                'upvotes': solution.upvotes,
                'downvotes': solution.downvotes,
                'comments': [],
            })

    context = {
        'post': post,
        'solutions': solutions,
        'content_json': content_json,
        'processed_solutions_json': json.dumps(processed_solutions),
        'courses': post.courses.all(),
        'has_solution_from_user': has_solution, 
    }

    return render(request, 'forum/post_detail.html', context)

@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.user != post.author:
        messages.error(request, "You don't have permission to edit this post.")
        return redirect('post_detail', post_id=post.id)
    
    if request.method == 'POST':
        try:
            # Get the content from the form
            content = request.POST.get('content')
            if content:
                content = json.loads(content)
            detect_bad_words(content)  # This will raise ValueError if bad words are detected
            # Update post
            post.content = content
            
            # Handle courses
            course_ids = request.POST.getlist('courses')
            if course_ids:
                post.courses.set(course_ids)
            
            post.save()
            messages.success(request, 'Post updated successfully!')
            return redirect('post_detail', post_id=post.id)
        except ValueError as e:
            # Catch bad word detection errors
            messages.error(request, f"Content contains inappropriate language: {str(e)}")
        except json.JSONDecodeError as e:
            messages.error(request, 'Invalid content format')
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            messages.error(request, 'Error updating post')
            logger.error(f"Error updating post: {e}")
        
        return redirect('edit_post', post_id=post.id)
    
    try:
        content = post.content
        if isinstance(content, str):
            content = json.loads(content)
            
        # Escape HTML in text content
        for block in content.get('blocks', []):
            if block.get('type') == 'paragraph':
                block['data']['text'] = escape(block['data']['text'])
        
        post_content = json.dumps(content)

        selected_courses = list(post.courses.values('id', 'name', 'code', 'category'))
        selected_courses_json = json.dumps(selected_courses)
    except Exception as e:
        post_content = json.dumps({
            "blocks": [{"type": "paragraph", "data": {"text": ""}}]
        })
        selected_courses_json = '[]'

    context = {
        'post': post,
        'action': 'Edit',
        'post_content': post_content,
        'selected_courses_json': selected_courses_json
    }

    # print(selected_courses_json)
    return render(request, 'forum/edit_post.html', context)


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if post.author != request.user:
        return HttpResponseForbidden("You cannot delete this post")
        
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted successfully!')
        return redirect('all_posts')
        
    return render(request, 'forum/delete_confirm.html', {'post': post})
