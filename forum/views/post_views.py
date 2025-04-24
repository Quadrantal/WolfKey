from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import F, Case, When, IntegerField
from django.core.serializers.json import DjangoJSONEncoder
import json
import logging
from django.http import JsonResponse
from django.utils.html import escape
from forum.models import Post, Solution, Comment, Course, FollowedPost, SavedSolution
from forum.forms import SolutionForm, CommentForm, PostForm
from .utils import selective_quote_replace
from django.contrib import messages
from .notification_views import send_course_notifications, send_solution_notification
from django.http import HttpResponseForbidden


logger = logging.getLogger(__name__)


@login_required
def create_post(request):
    if request.method == 'POST':
        # print("Enter 1")
        # print(f"POST data: {request.POST}")
        # print(f"FILES: {request.FILES}")
        
        form = PostForm(request.POST)
        # print(f"Form data: {form.data}")
        # print(f"Form is valid: {form.is_valid()}")
        if not form.is_valid():
            print(f"Form errors: {form.errors}")
        
        if form.is_valid():
            # print("Enter 2")
            try:
                # Create and save the post first
                post = form.save(commit=False)
                post.author = request.user
                
                # Handle content
                content_json = request.POST.get('content')
                print(f"Content JSON: {content_json}")
                content_data = json.loads(content_json) if content_json else {}
                post.content = content_data
                
                # Save post to generate ID
                post.save()
                
                # Handle courses from the form
                course_ids = request.POST.getlist('courses')
                print(f"Course IDs: {course_ids}")
                if course_ids:
                    courses = Course.objects.filter(id__in=course_ids)
                    post.courses.set(courses)
                    print(f"Added courses: {list(courses.values_list('id', 'name'))}")

                    send_course_notifications(post, courses)
                
                return redirect(post.get_absolute_url())
                
            except Exception as e:
                print(f"Error creating post: {str(e)}")
                messages.error(request, f"Error creating post: {str(e)}")
                return redirect('create_post')
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
    solution_form = SolutionForm()
    comment_form = CommentForm()
    
    has_solution = Solution.objects.filter(post=post, author=request.user).exists()

    if request.method == 'POST':
        if not request.user.is_authenticated: 
            return redirect('login')

        action = request.POST.get('action')
        
        if has_solution and action != 'delete_solution' and action != 'edit_solution':
            return redirect('post_detail', post_id=post.id)

        if action == 'create_solution':
            solution_form = SolutionForm(request.POST)
            if solution_form.is_valid():
                solution_json = request.POST.get('content')
                solution_data = json.loads(solution_json) if solution_json else {}
                solution = solution_form.save(commit=False)
                solution.content = solution_data
                solution.post = post
                solution.author = request.user
                solution.save()
                messages.success(request, 'Solution added successfully!')

            if solution.author != post.author:
                send_solution_notification(solution)

        elif action == 'edit_solution':
            solution_id = request.POST.get('solution_id')
            solution = get_object_or_404(Solution, id=solution_id, author=request.user)
            solution_form = SolutionForm(request.POST, instance=solution)
            if solution_form.is_valid():
                solution_json = request.POST.get('content')
                solution_data = json.loads(solution_json) if solution_json else {}
                solution = solution_form.save(commit=False)
                solution.content = solution_data
                solution.post = post
                solution.author = request.user
                solution.save()
                messages.success(request, 'Solution updated successfully!')

        elif action == 'delete_solution':
            solution_id = request.POST.get('solution_id')
            solution = get_object_or_404(Solution, id=solution_id, author=request.user)
            solution.delete()
            messages.success(request, 'Solution deleted successfully!')

        elif action == 'create_comment':
            comment_form = CommentForm(request.POST)
            solution_id = request.POST.get('solution_id')
            solution = get_object_or_404(Solution, id=solution_id)
            parent_id = request.POST.get('parent_id')

            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.solution = solution
                comment.author = request.user
                if parent_id:
                    parent_comment = get_object_or_404(Comment, id=parent_id)
                    comment.parent = parent_comment
                comment.save()
                messages.success(request, 'Comment added successfully!')

        elif action == 'edit_comment':
            comment_id = request.POST.get('comment_id')
            comment = get_object_or_404(Comment, id=comment_id, author=request.user)
            comment.content = comment_form.cleaned_data['content']
            comment.save()
            messages.success(request, 'Comment updated successfully!')

        elif action == 'delete_comment':
            comment_id = request.POST.get('comment_id')
            comment = get_object_or_404(Comment, id=comment_id, author=request.user)
            comment.delete()
            messages.success(request, 'Comment deleted successfully!')

        return redirect('post_detail', post_id=post.id)
    
    # Process post content
    try:
        content_json = json.dumps(post.content, cls=DjangoJSONEncoder)
    except (TypeError, ValueError) as e:
        logger.error(f"Error serializing post content: {e}")
        content_json = json.dumps({
            "blocks": [{"type": "paragraph", "data": {"text": "Error displaying content"}}]
        })
    
    processed_solutions = []
    for solution in solutions:
        try:
            solution_content = solution.content
            # If content is a string, convert to object
            if isinstance(solution_content, str):
                try:
                    solution_content = selective_quote_replace(solution_content)
                    solution_content = json.loads(solution_content)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in solution {solution.id}")
                    solution_content = {
                        "blocks": [{"type": "paragraph", "data": {"text": "Error parsing solution content"}}]
                    }
                
            # Check if the solution is saved by the current user
            is_saved = False
            if request.user.is_authenticated:
                is_saved = SavedSolution.objects.filter(user=request.user, solution=solution).exists()
            
            processed_solutions.append({
                'id': solution.id,
                'content': solution_content,  
                'author': f"{solution.author.first_name} {solution.author.last_name}",
                'created_at': solution.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                'upvotes': solution.upvotes,
                'downvotes': solution.downvotes,
                'is_saved': is_saved
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
            })
    
    # Check if the current user is following this post
    is_following = False
    if request.user.is_authenticated:
        is_following = FollowedPost.objects.filter(user=request.user, post=post).exists()
    
    context = {
        'post': post,
        'solutions': solutions,
        'content_json': content_json,
        'processed_solutions_json': json.dumps(processed_solutions),
        'courses': post.courses.all(),
        'has_solution_from_user': has_solution,
        'solution_form': solution_form,
        'comment_form': comment_form,
        'is_following': is_following
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
            
            # Update post
            post.content = content
            
            # Handle courses
            course_ids = request.POST.getlist('courses')
            if course_ids:
                post.courses.set(course_ids)
            
            post.save()
            messages.success(request, 'Post updated successfully!')
            return redirect('post_detail', post_id=post.id)
            
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
