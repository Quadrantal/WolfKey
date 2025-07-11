from django.shortcuts import get_object_or_404
from django.db.models import F, Case, When, IntegerField
from forum.models import Post, Course
from forum.services.utils import detect_bad_words, selective_quote_replace
from forum.services.notification_services import send_course_notifications_service
import json
import logging

logger = logging.getLogger(__name__)

def get_post_detail_service(post_id, user=None):
    try:
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

        processed_solutions = []
        for solution in solutions:
            try:
                solution_content = solution.content
                if isinstance(solution_content, str):
                    solution_content = selective_quote_replace(solution_content)
                    solution_content = json.loads(solution_content)
                
                comments = solution.comments.select_related('author').order_by('created_at')
                processed_comments = [{
                    'id': comment.id,
                    'content': comment.content,
                    'author': comment.author.get_full_name(),
                    'created_at': comment.created_at.isoformat(),
                    'parent_id': comment.parent_id,
                    'depth': comment.get_depth(),
                } for comment in comments]

                processed_solutions.append({
                    'id': solution.id,
                    'content': solution_content,
                    'author': solution.author.get_full_name(),
                    'created_at': solution.created_at.isoformat(),
                    'upvotes': solution.upvotes,
                    'downvotes': solution.downvotes,
                    'comments': processed_comments,
                })
            except Exception as e:
                logger.error(f"Error processing solution {solution.id}: {e}")

        return {
            'id': post.id,
            'title': post.title,
            'solutions_object' : solutions,
            'content': post.content,
            'author': post.author.get_full_name(),
            'created_at': post.created_at.isoformat(),
            'solutions': processed_solutions,
            'courses': [{'id': c.id, 'name': c.name} for c in post.courses.all()],
            'like_count': post.like_count(),
            'is_liked': post.is_liked_by(user) if user else False,
        }
    except Exception as e:
        return {'error': str(e)}

def create_post_service(user, data):
    try:
        content = data.get('content')
        if not content:
            return {'error': 'Content is required'}

        detect_bad_words(content)
        
        post = Post(
            author=user,
            title=data.get('title'),
            content=content,
            is_anonymous=data.get("is_anonymous"),
        )
        post.save()

        course_ids = data.get('courses', [])
        if course_ids:
            courses = Course.objects.filter(id__in=course_ids)
            post.courses.set(courses)
            send_course_notifications_service(post, courses)

        return {
            'id': post.id,
            'url': post.get_absolute_url(),
            'message': 'Post created successfully'
        }
    except ValueError as e:
        return {'error': f"Content contains inappropriate language: {str(e)}"}
    except Exception as e:
        return {'error': str(e)}

def update_post_service(user, post_id, data):
    try:
        post = get_object_or_404(Post, id=post_id)
        
        if post.author != user:
            return {'error': 'Permission denied'}

        if 'content' in data:
            content = data['content']
            detect_bad_words(content)
            post.content = content

        if 'courses' in data:
            course_ids = data['courses']
            courses = Course.objects.filter(id__in=course_ids)
            post.courses.set(courses)

        post.save()
        return {'message': 'Post updated successfully'}
    except Exception as e:
        return {'error': str(e)}

def delete_post_service(user, post_id):
    try:
        post = get_object_or_404(Post, id=post_id)
        
        if post.author != user:
            return {'error': 'Permission denied'}
            
        post.delete()
        return {'message': 'Post deleted successfully'}
    except Exception as e:
        return {'error': str(e)}
