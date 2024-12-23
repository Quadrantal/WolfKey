from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate 
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm  
from django.contrib import messages 
from django.contrib.auth.decorators import login_required
from .models import Post, Solution, Comment
from .forms import PostForm, CommentForm, SolutionForm
from django.http import HttpResponseForbidden, JsonResponse

def home(request):
    posts = Post.objects.all().order_by('-created_at')
    return render(request, 'forum/home.html', {'posts': posts})

def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    solutions = post.solutions.all()
    solution_form = SolutionForm()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')

        action = request.POST.get('action')

        # Handle solution creation
        if action == 'create_solution':
            solution_form = SolutionForm(request.POST)
            if solution_form.is_valid():
                solution = solution_form.save(commit=False)
                solution.post = post
                solution.author = request.user
                solution.save()
                messages.success(request, 'Solution added successfully!')

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

        return redirect('post_detail', post_id=post.id)

    return render(request, 'forum/post_detail.html', {
        'post': post,
        'solutions': solutions,
        'solution_form': solution_form,
        'comment_form': CommentForm(),  # Initialize a new comment form
    })

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
    """
    Log out the current user and redirect to the home page.
    
    Args:
        request (HttpRequest): The request object.
    
    Returns:
        HttpResponse: Redirect to the home page.
    """
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')

@login_required  # This ensures only logged-in users can access this view
def create_post(request):
    """
    Create a new post. Only logged-in users can access this view.
    
    Args:
        request (HttpRequest): The request object.
    
    Returns:
        HttpResponse: Render the post form or redirect to the post detail page.
    """
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)  # Create post but don't save to DB yet
            post.author = request.user      # Add the current user as author
            post.save()                     # save to DB
            messages.success(request, 'Post created successfully!')
            return redirect('post_detail', post_id=post.id)
    else:
        form = PostForm()
    return render(request, 'forum/post_form.html', {'form': form, 'action': 'Create'})

@login_required
def edit_post(request, post_id):
    """
    Edit an existing post. Only the author of the post can edit it.
    
    Args:
        request (HttpRequest): The request object.
        post_id (int): The ID of the post to edit.
    
    Returns:
        HttpResponse: Render the post form or return a forbidden response.
    """
    post = get_object_or_404(Post, id=post_id)
    
    # Check if user is the author
    if post.author != request.user:
        return HttpResponseForbidden("You cannot edit this post")
        
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post updated successfully!')
            return redirect('post_detail', post_id=post.id)
    else:
        form = PostForm(instance=post)
    
    return render(request, 'forum/post_form.html', {
        'form': form,
        'action': 'Edit'
    })

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Check if user is the author
    if post.author != request.user:
        return HttpResponseForbidden("You cannot delete this post")
        
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted successfully!')
        return redirect('home')
        
    return render(request, 'forum/delete_confirm.html', {'post': post})

@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Check if user is the author
    if comment.author != request.user:
        return HttpResponseForbidden("You cannot edit this comment")
    
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Comment updated successfully!')
            return redirect('post_detail', post_id=comment.solution.post.id)
    else:
        form = CommentForm(instance=comment)
    
    return render(request, 'forum/comment_form.html', {
        'form': form,
        'comment': comment,
        'action': 'Edit',
        'post_id': comment.solution.post.id
    })

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Check if user is the author
    if comment.author != request.user:
        return HttpResponseForbidden("You cannot delete this comment")
    
    post_id = comment.post.id  # Store post_id before deleting comment
    
    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Comment deleted successfully!')
        return redirect('post_detail', post_id=post_id)
    
    return render(request, 'forum/comment_delete.html', {'comment': comment})