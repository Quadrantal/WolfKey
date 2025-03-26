import re
from django.utils.html import strip_tags

def process_post_preview(post):
    """Process post content to create preview text"""
    if isinstance(post.content, dict) and 'blocks' in post.content:
        paragraphs = []
        for block in post.content['blocks']:
            if block.get('type') == 'paragraph':
                text = block.get('data', {}).get('text', '')
                text = re.sub(r'<br\s*/?>', ' ', text)
                text = re.sub(r'<i\s*/?>', ' ', text)
                text = re.sub(r'<em\s*/?>', ' ', text)
                text = strip_tags(text)
                text = ' '.join(text.split())
                if text:
                    paragraphs.append(text)
        return ' '.join(paragraphs)
    else:
        text = str(post.content)
        text = re.sub(r'<br\s*/?>', ' ', text)
        text = strip_tags(text)
        return ' '.join(text.split())

def add_course_context(post, experienced_courses=None, help_needed_courses=None):
    """Add course context to a post"""
    post.course_context = []
    for course in post.courses.all():
        post.course_context.append({
            'name': course.name,
            'is_experienced': course in (experienced_courses or []),
            'needs_help': course in (help_needed_courses or [])
        })
    return post