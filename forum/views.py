from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate 
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm  
from django.contrib import messages 
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity
from .models import Post, Solution, Comment, SolutionUpvote, SolutionDownvote, CommentUpvote, Tag, File, User, SavedPost, UserCourseHelp, UserCourseExperience, UserProfile, Course, Notification
from .forms import PostForm, CommentForm, SolutionForm, TagForm, UserProfileForm, UserCourseExperienceForm, UserCourseHelpForm
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import F
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
import logging
import json
from datetime import timezone
from datetime import timedelta
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.html import escape
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q

logger = logging.getLogger(__name__)


def home(request):
    query = request.GET.get('q', '')
    tag_ids = request.GET.get('tags', '').split(',')
    tag_ids = [tag_id for tag_id in tag_ids if tag_id]  # Filter out empty strings
    posts = Post.objects.all().order_by('-created_at')

    if query:
        search_query = SearchQuery(query)
        posts = posts.annotate(
            rank=SearchRank(F('search_vector'), search_query) + TrigramSimilarity('title', query)
        ).filter(rank__gte=0.3).order_by('-rank')

    if tag_ids:
        posts = posts.filter(tags__id__in=tag_ids).distinct()

    tags = Tag.objects.all().order_by('name')  # Sort tags alphabetically

    return render(request, 'forum/home.html', {'posts': posts, 'tags': tags, 'query': query, 'selected_tags': tag_ids})

def selective_quote_replace(content):
    """Helper function to selectively replace quotes while preserving inlineMath"""
    # First, preserve inlineMath quotes
    content = content.replace('"inline-math"', "__INLINEMATH__")
    
    # Do the regular quote replacements
    content = (content
        .replace("'", '"')        # Replace single quotes with double quotes
        .replace('data-tex="', 'data-tex=\\"')
        .replace('" style=', '\\" style=')
        .replace('style="', 'style=\\"')
        .replace('class="', 'class=\\"')
        .replace('" class=', '\\" class=')
        .replace('id="', 'id=\\"')
        .replace('" id=', '\\" id=')
        .replace(';">', ';\\">')
        .replace('" >', '\\">')
        .replace('"/>', '\\"/>')
        .replace('True', 'true')     # JavaScript booleans
        .replace('False', 'false')
        .replace('None', 'null')
        .replace('\n', '\\n')
        .replace('\r', '\\r')
        .replace('\t', '\\t')
        .strip())

    # Restore inlineMath quotes
    content = content.replace("__INLINEMATH__", "'inline-math'")

    return content

@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    solutions = post.solutions.all()
    solution_form = SolutionForm()
    comment_form = CommentForm()

    if request.method == 'POST':
        if not request.user.is_authenticated: 
            return redirect('login')

        action = request.POST.get('action')

        # Handle solution creation
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

            # if solution.author != post.author:
            send_solution_notification(solution)

        # Handle solution editing
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

        # Handle solution deletion
        elif action == 'delete_solution':
            solution_id = request.POST.get('solution_id')
            solution = get_object_or_404(Solution, id=solution_id, author=request.user)
            solution.delete()
            messages.success(request, 'Solution deleted successfully!')

        # Handle comment creation or editing
        elif action in ['create_comment', 'edit_comment']:
            comment_form = CommentForm(request.POST)
            solution_id = request.POST.get('solution_id')
            solution = get_object_or_404(Solution, id=solution_id)

            if action == 'create_comment':
                if comment_form.is_valid():
                    comment = comment_form.save(commit=False)
                    comment.solution = solution
                    comment.author = request.user
                    comment.save()
                    messages.success(request, 'Comment added successfully!')

            elif action == 'edit_comment':
                comment_id = request.POST.get('comment_id')
                comment = get_object_or_404(Comment, id=comment_id, author=request.user)
                comment.content = comment_form.cleaned_data['content']
                comment.save()
                messages.success(request, 'Comment updated successfully!')

        # Handle comment deletion
        elif action == 'delete_comment':
            comment_id = request.POST.get('comment_id')
            comment = get_object_or_404(Comment, id=comment_id, author=request.user)
            comment.delete()
            messages.success(request, 'Comment deleted successfully!')

        return redirect('post_detail', post_id=post.id)

    # Process post content
    content_json = json.dumps(post.content, cls=DjangoJSONEncoder)
    
    processed_solutions = []
    for solution in solutions:
        try:
            solution_content = solution.content
            # If content is a string, convert to object
            print(type(solution_content))
            if isinstance(solution_content, str):
                solution_content = selective_quote_replace(solution_content)
                print(f"Solution Content: f{solution_content}")
                solution_content = json.loads(solution_content)
                
            processed_solutions.append({
                'id': solution.id,
                'content': solution_content,  
                'author': solution.author.username,
                'created_at': solution.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                'upvotes': solution.upvotes,
                'downvotes': solution.downvotes,
            })
        except Exception as e:
            logger.error(f"Error processing solution {solution.id}: {e}")
            processed_solutions.append({
                'id': solution.id,
                'content': {
                    "blocks": [{"type": "paragraph", "data": {"text": "Error loading solution content"}}]
                },
                'author': solution.author.username,
                'created_at': solution.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                'upvotes': solution.upvotes,
                'downvotes': solution.downvotes,
            })
    
    context = {
        'post': post,
        'solutions': solutions,
        'content_json': content_json,
        'processed_solutions_json': json.dumps(processed_solutions),
        'courses': post.courses.all(),
    }

    print(post.courses.all())
    return render(request, 'forum/post_detail.html', context)



@permission_required('forum.can_delete_posts', raise_exception=True)
def delete_post(request, post_id):
    # Only users with delete permission can access this view
    pass

def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == 'POST':
        try:
            # Get the content from the form
            content = request.POST.get('content')
            if content:
                content = json.loads(content)
            
            # Update post
            post.content = content
            
            # Handle tags
            tags = request.POST.get('tags', '').split(',')
            post.tags.clear()
            for tag_name in tags:
                tag_name = tag_name.strip()
                if tag_name:
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    post.tags.add(tag)
            
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
    except Exception as e:
        post_content = json.dumps({
            "blocks": [{"type": "paragraph", "data": {"text": ""}}]
        })

    context = {
        'post': post,
        'action': 'Edit',
        'post_content': post_content
    }
    return render(request, 'forum/edit_post.html', context)

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'forum/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'You are now logged in!')
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'forum/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')

@login_required
def create_post(request):
    if request.method == 'POST':
        print("Enter 1")
        print(f"POST data: {request.POST}")
        print(f"FILES: {request.FILES}")
        
        form = PostForm(request.POST)
        print(f"Form data: {form.data}")
        print(f"Form is valid: {form.is_valid()}")
        if not form.is_valid():
            print(f"Form errors: {form.errors}")
        
        if form.is_valid():
            print("Enter 2")
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

def upload_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image = request.FILES['image']
        # Optionally, process the image before saving (e.g., resize, convert formats)
        
        # Save the image in your static or media directory
        filename = default_storage.save('uploads/' + image.name, ContentFile(image.read()))
        
        # Return the URL of the uploaded image
        image_url = default_storage.url(filename)
        
        return JsonResponse({'success': 1, 'file': {'url': image_url}})
    else:
        return JsonResponse({'error': 'No image uploaded'}, status=400)
    

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if post.author != request.user:
        return HttpResponseForbidden("You cannot delete this post")
        
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted successfully!')
        return redirect('home')
        
    return render(request, 'forum/delete_confirm.html', {'post': post})

@login_required
def upvote_solution(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id)
    if SolutionDownvote.objects.filter(solution = solution, user = request.user).exists():
        SolutionDownvote.objects.filter(solution = solution, user = request.user).delete()
        solution.downvotes -= 1
        solution.save()
    if not SolutionUpvote.objects.filter(solution=solution, user=request.user).exists():
        SolutionUpvote.objects.create(solution=solution, user=request.user)
        solution.upvotes += 1
        solution.save()
        messages.success(request, 'Solution upvoted successfully!')
    else:
        messages.warning(request, 'You have already upvoted this solution.')
    return redirect('post_detail', post_id=solution.post.id)


@login_required
def downvote_solution(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id)
    if SolutionUpvote.objects.filter(solution = solution, user = request.user).exists():
        SolutionUpvote.objects.filter(solution = solution, user = request.user).delete()
        solution.upvotes -= 1
        solution.save()
    if not SolutionDownvote.objects.filter(solution=solution, user=request.user).exists():
        SolutionDownvote.objects.create(solution=solution, user=request.user)
        solution.downvotes += 1
        solution.save()
        messages.success(request, 'Solution downvoted successfully!')
    else:
        messages.warning(request, 'You have already downvoted this solution.')
    return redirect('post_detail', post_id=solution.post.id)

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


@login_required
def create_tag(request):
    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tag created successfully!')
            return redirect('home')
    else:
        form = TagForm()
    return render(request, 'forum/tag_form.html', {'form': form})


def search_posts(request):
    query = request.GET.get('q', '')
    tag_ids = request.GET.get('tags', '').split(',')
    tag_ids = [tag_id for tag_id in tag_ids if tag_id]  # Filter out empty strings
    posts = Post.objects.all().order_by('-created_at')

    if query:
        search_query = SearchQuery(query)
        posts = posts.annotate(
            rank=SearchRank(F('search_vector'), search_query) + TrigramSimilarity('title', query)
        ).filter(rank__gte=0.3).order_by('-rank')

    if tag_ids:
        posts = posts.filter(tags__id__in=tag_ids).distinct()

    results = []
    for post in posts:
        results.append({
            'id': post.id,
            'title': post.title,
            'content': post.content[:100],  # Truncate content for preview
            'url': post.get_absolute_url(),
            'author': post.author.username,
            'created_at': post.created_at,
        })

    return JsonResponse({'results': results, 'query': query, 'selected_tags': tag_ids})

def search_results_new_page(request):
    print("Enters view")
    query = request.GET.get('q', '')
    tag_ids = request.GET.get('tags', '').split(',')
    tag_ids = [tag_id for tag_id in tag_ids if tag_id]  # Filter out empty strings
    posts = Post.objects.all().order_by('-created_at')

    if query or tag_ids:
        if query:
            search_query = SearchQuery(query)
            posts = posts.annotate(
                rank=SearchRank(F('search_vector'), search_query) + TrigramSimilarity('title', query)
            ).filter(rank__gte=0.3).order_by('-rank')

        if tag_ids:
            posts = posts.filter(tags__id__in=tag_ids).distinct()


        return render(request, 'forum/search_results.html', {
                'posts': posts,
                'query': query,
                'selected_tags': tag_ids
            })

    return redirect('home')



@login_required
def profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    recent_posts = Post.objects.filter(author=profile_user).order_by('-created_at')[:5]
    posts_count = Post.objects.filter(author=profile_user).count()
    solutions_count = Solution.objects.filter(author=profile_user).count()
    
    context = {
        'profile_user': profile_user,
        'recent_posts': recent_posts,
        'posts_count': posts_count,
        'solutions_count': solutions_count,
        'experience_form': UserCourseExperienceForm(user=profile_user),
        'help_form': UserCourseHelpForm(user=profile_user),
        'experienced_courses': UserCourseExperience.objects.filter(user=profile_user),
        'help_needed_courses': UserCourseHelp.objects.filter(user=profile_user, active=True),
    }
    return render(request, 'forum/profile.html', context)

@login_required
def edit_profile(request):
    try:
        profile = request.user.userprofile
    except ObjectDoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile', username=request.user.username)
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'forum/edit_profile.html', {'form': form})

@login_required
def my_profile(request):
    return redirect('profile', username=request.user.username)

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

@login_required
def my_posts(request):
    posts = Post.objects.filter(author = request.user)
    return render(request,'forum/my_posts.html', {'posts': posts})

@login_required
def add_experience(request):
    if request.method == 'POST':
        form = UserCourseExperienceForm(request.POST, user=request.user) 
        if form.is_valid():
            experience = form.save(commit=False)
            experience.user = request.user
            experience.save()
            messages.success(request, 'Course experience added successfully!')
    return redirect('profile', username=request.user.username) 

@login_required
def add_help_request(request):
    if request.method == 'POST':
        form = UserCourseHelpForm(request.POST, user=request.user)  
        if form.is_valid():
            help_request = form.save(commit=False)
            help_request.user = request.user
            help_request.save()
            messages.success(request, 'Help request added successfully!')
    return redirect('profile', username=request.user.username) 

@login_required
def remove_experience(request, experience_id):
    try:
        experience = get_object_or_404(UserCourseExperience, 
                                     id=experience_id, 
                                     user=request.user)
        if request.method == 'POST':
            experience.delete()
            messages.success(request, 'Course experience removed successfully!')
    except UserCourseExperience.DoesNotExist:
        messages.error(request, 'Course experience not found.')
    except Exception as e:
        messages.error(request, f'Error removing course experience: {str(e)}')
    
    return redirect('profile', username=request.user.username)

@login_required
def remove_help_request(request, help_id):
    help_request = get_object_or_404(UserCourseHelp, id=help_id, user=request.user)
    if request.method == 'POST':
        help_request.delete()
        messages.success(request, 'Help request removed successfully!')
    return redirect('profile', username=request.user.username)

def course_search(request):
    query = request.GET.get('q', '')
    courses = Course.objects.filter(
        name__icontains=query
    ) if query else Course.objects.all()
    
    data = [{
        "id": course.id,
        "name": course.name,
        "code": course.code,
        "category": course.category
    } for course in courses[:10]] 
    
    return JsonResponse(data, safe=False)

def send_course_notifications(post, courses):
    experienced_users = UserCourseExperience.objects.filter(
        course__in=courses
    ).select_related('user').distinct('user')
    
    # experienced_users = experienced_users.exclude(user=post.author) 
    
    for exp_user in experienced_users:
        # Create in-site notification
        Notification.objects.create(
            recipient=exp_user.user,
            sender=post.author,
            notification_type='post',
            post=post,
            message=f'New post in {", ".join(c.name for c in courses)}: {post.title}'
        )
        
        # Send email notification
        subject = f'New post in your experienced course: {post.title}'
        message = f"""
        Hello {exp_user.user.username},
        
        A new post has been created in a course you have experience in:
        
        Title: {post.title}
        Course(s): {', '.join(c.name for c in courses)}
        
        You can view the post here:
        {settings.SITE_URL}{post.get_absolute_url()}
        
        Best regards,
        School Forum Team
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [exp_user.user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send notification email to {exp_user.user.email}: {e}")

def send_solution_notification(solution):
    post = solution.post
    author = post.author
    
    # Create in-site notification
    Notification.objects.create(
        recipient=author,
        sender=solution.author,
        notification_type='solution',
        post=post,
        solution=solution,
        message=f'New solution to your post: {post.title}'
    )
    
    # Send email notification
    subject = f'New solution to your post: {post.title}'
    message = f"""
    Hello {author.username},
    
    A new solution has been posted to your question:
    
    Post: {post.title}
    Solution by: {solution.author.username}
    
    You can view the solution here:
    {settings.SITE_URL}{post.get_absolute_url()}
    
    Best regards,
    School Forum Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [author.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Failed to send solution notification email to {author.email}: {e}")

@login_required
def all_notifications(request):
    notifications = request.user.notifications.all()
    return render(request, 'forum/notifications.html', {'notifications': notifications})

@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    
    if notification.post:
        return redirect('post_detail', post_id=notification.post.id)
    return redirect('all_notifications')