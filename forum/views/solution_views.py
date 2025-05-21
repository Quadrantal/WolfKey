# views/solution_views.py
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from forum.models import Post, Solution, SolutionDownvote, SolutionUpvote
from forum.forms import SolutionForm
from django.contrib import messages
from django.http import HttpResponseForbidden
from .utils import process_messages_to_json, detect_bad_words


@login_required
def create_solution(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)

        has_solution = Solution.objects.filter(post=post, author=request.user).exists()
        if has_solution:
            messages.error(request, 'You have already submitted a solution.')
            return redirect(post.get_absolute_url())

        solution_form = SolutionForm(request.POST)
        if solution_form.is_valid():
            try:
                solution_json = request.POST.get('content')
                solution_data = json.loads(solution_json) if solution_json else {}

                blocks = solution_data.get('blocks', [])
                if (len(blocks) == 1 and blocks[0].get('type') == 'paragraph' and not blocks[0].get('data', {}).get('text', '').strip()) or len(blocks) == 0:
                    messages.error(request, 'Solution cannot be empty.')
                    return redirect(post.get_absolute_url())
                detect_bad_words(solution_data) 
                solution = solution_form.save(commit=False)
                solution.content = solution_data
                solution.post = post
                solution.author = request.user
                solution.save()
                messages.success(request, 'Solution submitted succesfully.')
                
                return redirect(post.get_absolute_url())
            except ValueError as e:
                messages.error(request, str(e))

    messages.error(request, 'An error occured.')
    return redirect(post.get_absolute_url())

@login_required
def edit_solution(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id, author=request.user)

    if request.method == 'POST':
        solution_form = SolutionForm(request.POST, instance=solution)
        if solution_form.is_valid():
            try:
                solution_json = request.POST.get('content')
                solution_data = json.loads(solution_json) if solution_json else {}

                blocks = solution_data.get('blocks', [])
                if (len(blocks) == 1 and blocks[0].get('type') == 'paragraph' and not blocks[0].get('data', {}).get('text', '').strip()) or len(blocks) == 0:
                    messages.error(request, 'Solution cannot be empty.')
                    return redirect('edit_solution', solution_id=solution.id)
                
                detect_bad_words(solution_data) 
                solution = solution_form.save(commit=False)
                solution.content = solution_data
                solution.save()
                messages.success(request, 'Solution edited succesfully')
                messages_data = process_messages_to_json(request)
                return JsonResponse({'status': 'success','messages': messages_data}, status=200)
            except ValueError as e:
                print(e)
                messages.error(request,str(e))
                messages_data = process_messages_to_json(request)
                return JsonResponse({'status': 'error','messages': messages_data}, status=200)
    messages.error(request, "Invalid request.")
    
    messages_data = process_messages_to_json(request)
    return JsonResponse({'status' : 'error', 'messages': messages_data}, status=400)

@login_required
def delete_solution(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id, author=request.user)
    
    if request.method == 'POST':
        solution.delete()
        messages.success(request, 'Solution deleted succesfully')
        messages_data = process_messages_to_json(request)

        return JsonResponse({'status': 'success','messages': messages_data}, status=200)

    messages_data = process_messages_to_json(request)
    return JsonResponse({'status': 'error','messages': messages_data}, status=400)


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