from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate 
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm  
from django.contrib import messages 
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity
from .models import Post, Solution, Comment, SolutionUpvote, CommentUpvote, Tag
from .forms import PostForm, CommentForm, SolutionForm, TagForm
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import F


def home(request):
    query = request.GET.get('q')
    if query:
        search_query = SearchQuery(query)
        posts = Post.objects.annotate(
            rank=SearchRank(F('search_vector'), search_query) + TrigramSimilarity('title', query)
        ).filter(rank__gte=0.3).order_by('-rank')
    else:
        posts = Post.objects.all().order_by('-created_at')
    return render(request, 'forum/home.html', {'posts': posts, 'query': query})

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
                solution = solution_form.save(commit=False)
                solution.post = post
                solution.author = request.user
                solution.save()
                messages.success(request, 'Solution added successfully!')

        # Handle solution editing
        elif action == 'edit_solution':
            solution_id = request.POST.get('solution_id')
            solution = get_object_or_404(Solution, id=solution_id, author=request.user)
            solution_form = SolutionForm(request.POST, instance=solution)
            if solution_form.is_valid():
                solution_form.save()
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

    return render(request, 'forum/post_detail.html', {
        'post': post,
        'solutions': solutions,
        'solution_form': solution_form,
        'comment_form': comment_form,
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
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')

@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()  # Save the many-to-many data for the form
            messages.success(request, 'Post created successfully!')
            return redirect('post_detail', post_id=post.id)
    else:
        form = PostForm()
    return render(request, 'forum/post_form.html', {'form': form, 'action': 'Create'})

@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
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
    if not SolutionUpvote.objects.filter(solution=solution, user=request.user).exists():
        SolutionUpvote.objects.create(solution=solution, user=request.user)
        solution.upvotes += 1
        solution.save()
        messages.success(request, 'Solution upvoted successfully!')
    else:
        messages.warning(request, 'You have already upvoted this solution.')
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
    if query:
        search_query = SearchQuery(query)
        posts = Post.objects.annotate(
            rank=SearchRank(F('search_vector'), search_query) + TrigramSimilarity('title', query)
        ).filter(rank__gte=0.3).order_by('-rank')
    else:
        posts = Post.objects.all().order_by('-created_at')

    results = [{
        'title': post.title,
        'content': post.content[:100],  # Truncate content for preview
        'url': request.build_absolute_uri(post.get_absolute_url()),
        'author': post.author.username,
        'created_at': post.created_at.strftime("%B %d, %Y")
    } for post in posts]

    return JsonResponse({'results': results}, safe=False)