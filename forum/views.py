from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate 
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm  
from django.contrib import messages 
from django.contrib.auth.decorators import login_required
from .models import Post
from .forms import PostForm
from django.http import HttpResponseForbidden 
def home(request):
    posts = Post.objects.all().order_by('-created_at')
    return render(request, 'forum/home.html', {'posts': posts})

def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    return render(request, 'forum/post_detail.html', {'post': post})

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


@login_required  # This ensures only logged-in users can access this view
def create_post(request):
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