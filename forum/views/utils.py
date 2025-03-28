import re
from django.utils.html import strip_tags
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse

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

def upload_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image = request.FILES['image']
        # Optionally, process the image before saving (e.g., resize, convert formats) TODO
        
        # Save the image in your static or media directory
        filename = default_storage.save('uploads/' + image.name, ContentFile(image.read()))
        
        # Return the URL of the uploaded image
        image_url = default_storage.url(filename)
        
        return JsonResponse({'success': 1, 'file': {'url': image_url}})
    else:
        return JsonResponse({'error': 'No image uploaded'}, status=400)
    
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
        .replace('True', 'true')     
        .replace('False', 'false')
        .replace('None', 'null')
        .replace('\n', '\\n')
        .replace('\r', '\\r')
        .replace('\t', '\\t')
        .strip())

    # Restore inlineMath quotes
    content = content.replace("__INLINEMATH__", "'inline-math'")

    return content