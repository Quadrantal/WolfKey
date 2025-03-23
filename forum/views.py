from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate 
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm  
from django.contrib import messages 
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity
from .models import Post, Solution, Comment, SolutionUpvote, SolutionDownvote, CommentUpvote, Tag, File, User, SavedPost, UserCourseHelp, UserCourseExperience, UserProfile, Course, Notification, UpdateAnnouncement, UserUpdateView
from .forms import PostForm, CommentForm, SolutionForm, TagForm, UserProfileForm, UserCourseExperienceForm, UserCourseHelpForm, CustomUserCreationForm
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import F, Case, When, IntegerField 
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
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST
import re
from .utils import process_post_preview, add_course_context

logger = logging.getLogger(__name__)

def acknowledge_update(request):
    try:
        data = json.loads(request.body)
        update_id = data.get('update_id')
        update = UpdateAnnouncement.objects.get(id=update_id)
        UserUpdateView.objects.get_or_create(
            user=request.user,
            update=update
        )
        return JsonResponse({'success': True})
    except UpdateAnnouncement.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Update not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
def get_user_courses(user):
    """Get user's experienced and help-needed courses"""
    if not user.is_authenticated:
        return [], []
        
    experienced_courses = Course.objects.filter(
        id__in=UserCourseExperience.objects.filter(
            user=user
        ).values_list('course_id', flat=True)
    )
    
    help_needed_courses = Course.objects.filter(
        id__in=UserCourseHelp.objects.filter(
            user=user,
            active=True
        ).values_list('course_id', flat=True)
    )
    
    return experienced_courses, help_needed_courses

def for_you(request):
    if not request.user.is_authenticated:
        return redirect('login')
        
    experienced_courses, help_needed_courses = get_user_courses(request.user)

    # Get posts for both types of courses
    posts = Post.objects.filter(
        Q(courses__in=experienced_courses) | 
        Q(courses__in=help_needed_courses)
    ).distinct().order_by('-created_at')

    # Process posts
    for post in posts:
        post.preview_text = process_post_preview(post)
        add_course_context(post, experienced_courses, help_needed_courses)
        

    return render(request, 'forum/for_you.html', {
        'posts': posts,
        'experienced_courses': experienced_courses,
        'help_needed_courses': help_needed_courses,
    })

def all_posts(request):
    query = request.GET.get('q', '')
    tag_ids = request.GET.get('tags', '').split(',')
    tag_ids = [tag_id for tag_id in tag_ids if tag_id]
    posts = Post.objects.all().order_by('-created_at')

    if query:
        search_query = SearchQuery(query)
        posts = posts.annotate(
            rank=SearchRank(F('search_vector'), search_query) + TrigramSimilarity('title', query)
        ).filter(rank__gte=0.3).order_by('-rank')

    if tag_ids:
        posts = posts.filter(tags__id__in=tag_ids).distinct()

    experienced_courses, help_needed_courses = get_user_courses(request.user)
    
    # Process posts
    for post in posts:
        post.preview_text = process_post_preview(post)
        add_course_context(post, experienced_courses, help_needed_courses)

    return render(request, 'forum/all_posts.html', {
        'posts': posts,
        'tags': Tag.objects.all().order_by('name'),
        'query': query,
        'selected_tags': tag_ids,
    })

def selective_quote_replace(content):
    """Helper function to selectively replace quotes while preserving inlineMath"""
    # First, preserve inlineMath quotes
    content = re.sub(r'data-tex="(.*?)"', r'data-tex=__INLINEMATH__\1__INLINEMATH__', content)
    
    # Do the regular quote replacements
    content = (content
        .replace('"', '\\"')  
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
        # print("check 1")
        if not request.user.is_authenticated: 
            return redirect('login')

        action = request.POST.get('action')
        
        if has_solution and action != 'delete_solution':
            return redirect('post_detail', post_id=post.id)
        
        # print(action)
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

            if solution.author != post.author:
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
            try:
                # print("hi")
                solution_id = request.POST.get('solution_id')
                solution = get_object_or_404(Solution, id=solution_id, author=request.user)
                solution.delete()
                messages.success(request, 'Solution deleted successfully!')
            except Exception as e:
                # print(e)

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
        # print("Solution: ", solution.content)
        try:
            solution_content = solution.content
            # If content is a string, convert to object
            # print(type(solution_content))
            if isinstance(solution_content, str):
                solution_content = selective_quote_replace(solution_content)
                print(f"Solution Content: f{solution_content}")
                solution_content = json.loads(solution_content)

            # print("Solution: ", solution_content)
                
            processed_solutions.append({
                'id': solution.id,
                'content': solution_content,  
                'author': f"{solution.author.first_name} {solution.author.last_name}",
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
                'author': f"{solution.author.first_name} {solution.author.last_name}",
                'created_at': solution.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                'upvotes': solution.upvotes,
                'downvotes': solution.downvotes,
            })
    # print("Author", post.author.get_full_name())
    context = {
        'post': post,
        'solutions': solutions,
        'content_json': content_json,
        'processed_solutions_json': json.dumps(processed_solutions),
        'courses': post.courses.all(),
        'has_solution': has_solution, 
    }

    # print(post.courses.all())
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

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        # print(form)
        if form.is_valid():
            user = form.save()
            current_courses = request.POST.get('current_courses', '').split(',')
            experienced_courses = request.POST.get('experienced_courses', '').split(',')
            
            # print(current_courses)
            # print(experienced_courses)
            
            
            if len(experienced_courses) < 5:
                messages.error(request, 'You must select at least 5 experienced courses.')
                return render(request, 'forum/register.html', {
                    'form': form,
                    'courses': Course.objects.all().order_by('name'),
                    'form_errors': form.errors.as_json()  
                })
            if len(current_courses) < 3:
                messages.error(request, 'You must select at least 3 courses you need help with.')
                return render(request, 'forum/register.html', {
                    'form': form,
                    'courses': Course.objects.all().order_by('name'),
                    'form_errors': form.errors.as_json()  
            })
            
            # Add current courses as help needed
            for course_id in current_courses:
                UserCourseHelp.objects.create(
                    user=user,
                    course_id=course_id,
                    active=True
                )
                
            # Add experienced courses
            for course_id in experienced_courses:
                UserCourseExperience.objects.create(
                    user=user,
                    course_id=course_id
                )
            
            login(request, user)
            messages.success(request, 'Welcome to Student Forum!')
            return redirect('all_posts')
        else:
            print(form.errors)
            return render(request, 'forum/register.html', {
                'form': form,
                'courses': Course.objects.all().order_by('name'),
                'form_errors': form.errors.as_json()  
            })
    else:
        form = CustomUserCreationForm()
    
    courses = Course.objects.all().order_by('name')
    return render(request, 'forum/register.html', {
        'form': form,
        'courses': courses
    })

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'You are now logged in!')
            return redirect('for_you')
        else:
            school_email = request.POST.get('username')  # AuthenticationForm uses 'username' field
            try:
                user = User.objects.get(school_email=school_email)
                # print(f"User exists: {user.school_email}, is_active: {user.is_active}")
            except User.DoesNotExist:
                # print(f"No user with email: {school_email}")
                pass
    else:
        form = AuthenticationForm()
    return render(request, 'forum/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('all_posts')

@login_required
def create_post(request):
    if request.method == 'POST':
        # print("Enter 1")
        print(f"POST data: {request.POST}")
        print(f"FILES: {request.FILES}")
        
        form = PostForm(request.POST)
        # print(f"Form data: {form.data}")
        print(f"Form is valid: {form.is_valid()}")
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
        return redirect('all_posts')
        
    return render(request, 'forum/delete_confirm.html', {'post': post})

@login_required
def upvote_solution(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id)
    if SolutionDownvote.objects.filter(solution=solution, user=request.user).exists():
        SolutionDownvote.objects.filter(solution=solution, user=request.user).delete()
        solution.downvotes -= 1
    elif not SolutionUpvote.objects.filter(solution=solution, user=request.user).exists():
        SolutionUpvote.objects.create(solution=solution, user=request.user)
        solution.upvotes += 1
    else:
        return JsonResponse({'success': False, 'message': 'You have already upvoted this solution.'}, status=400)
    
    solution.save()
    return JsonResponse({'success': True, 'upvotes': solution.upvotes, 'downvotes': solution.downvotes, 'vote_state': 'upvoted' if SolutionUpvote.objects.filter(solution=solution, user=request.user).exists() else 'downvoted' if SolutionDownvote.objects.filter(solution=solution, user=request.user).exists() else 'none'})


@login_required
def downvote_solution(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id)
    if SolutionUpvote.objects.filter(solution=solution, user=request.user).exists():
        SolutionUpvote.objects.filter(solution=solution, user=request.user).delete()
        solution.upvotes -= 1
    elif not SolutionDownvote.objects.filter(solution=solution, user=request.user).exists():
        SolutionDownvote.objects.create(solution=solution, user=request.user)
        solution.downvotes += 1
    else:
        return JsonResponse({'success': False, 'message': 'You have already downvoted this solution.'}, status=400)
    
    solution.save()
    return JsonResponse({'success': True, 'upvotes': solution.upvotes, 'downvotes': solution.downvotes, 'vote_state': 'upvoted' if SolutionUpvote.objects.filter(solution=solution, user=request.user).exists() else 'downvoted' if SolutionDownvote.objects.filter(solution=solution, user=request.user).exists() else 'none'})

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
            return redirect('all_posts')
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
    # print("Enters view")
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

    return redirect('all_posts')



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
        Hello {exp_user.user.get_full_name()},
        
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
                [exp_user.user.personal_email],
                fail_silently=False,
            )
            print("Sent mail")
            print(subject)
            print(message)
            print(settings.DEFAULT_FROM_EMAIL)
            print([exp_user.user.personal_email])
        except Exception as e:
            print(f"Failed to send notification email to {exp_user.user.personal_email}: {e}")

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
        message=f'New solution to your question: {post.title}'
    )
    
    # Send email notification
    subject = f'New solution to your question: {post.title}'
    message = f"""
    Hello {author.get_full_name()},
    
    A new solution has been posted to your question:
    
    Post: {post.title}
    Solution by: {solution.author.get_full_name()}
    
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
            [author.personal_email],
            fail_silently=False,
        )
        print("Sent mail")
    except Exception as e:
        logger.error(f"Failed to send solution notification email to {author.personal_email}: {e}")

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

@login_required
def accept_solution(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id)
    post = solution.post
    
    # Only post author can accept solutions
    if request.user != post.author:
        return HttpResponseForbidden("Only the post author can accept solutions")
    
    if post.accepted_solution == solution:
        # Unaccept the solution
        post.accepted_solution = None
        post.save()
        messages.success(request, 'Solution unmarked as accepted.')
    else:
        if post.accepted_solution:
            # Unaccept the previous solution
            post.accepted_solution = None
            post.save()
            messages.info(request, 'Previous accepted solution has been unmarked.')
        # Accept the solution
        post.accepted_solution = solution
        post.save()
        messages.success(request, 'Solution marked as accepted!')
        
    return redirect('post_detail', post_id=post.id)