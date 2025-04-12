import re
from django.utils.html import strip_tags
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.contrib import messages


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

def process_messages_to_json(request):
    messages_data = [
        {
            'message': message.message,
            'tags': message.tags
        }
        for message in messages.get_messages(request)
    ]

    return messages_data

leet_mapping = str.maketrans({
    '4': 'a', '@': 'a',
    '8': 'b',
    '(': 'c', '{': 'c', '[': 'c', '<': 'c',
    '3': 'e',
    '6': 'g', '9': 'g',
    '1': 'i', '!': 'i', '|': 'i',
    '0': 'o',
    '5': 's', '$': 's',
    '7': 't', '+': 't',
    '2': 'z'
})

def normalize_text(text):
    """Normalizes text by converting leetspeak, removing special characters, and reducing repeated letters."""
    if not text:
        return ""
    
    text = text.translate(leet_mapping)  # Convert leetspeak
    text = re.sub(r'[^a-zA-Z\s]', '', text)  # Remove non-alphabetic characters, keep spaces
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize spaces
    text = re.sub(r'(.)\1{2,}', r'\1', text)  # Reduce repeated letters (e.g., "loooool" -> "lol")
    
    return text.lower()

bad_word_list = ['fuck', 'bitch', 'shit', 'ass', 'dick', 'cunt', 'cock', 'pussy']
bad_word_pattern = re.compile(r'\b(' + '|'.join(map(re.escape, bad_word_list)) + r')\b', re.IGNORECASE)

def detect_bad_words(content):
    """
    Detects bad words in plain text or structured Editor.js content.
    Raises ValueError if bad words are found, specifying the location.
    """
    if isinstance(content, str):
        normalized_text = normalize_text(content)
        if bad_word_pattern.search(normalized_text):
            raise ValueError("Bad word detected in text.")
    
    elif isinstance(content, dict) and 'blocks' in content:
        for block in content['blocks']:
            block_type = block.get("type", "unknown")
            data = block.get("data", {})
            
            text = data.get("text", "")
            items = data.get("items", [])
            
            if text:
                normalized_text = normalize_text(text)
                if bad_word_pattern.search(normalized_text):
                    raise ValueError(f"Bad word detected in block of type '{block_type}'.")
            
            for item in items:
                item_text = normalize_text(item.get("content"))
                if bad_word_pattern.search(item_text):
                    raise ValueError(f"Bad word detected in list item in block of type '{block_type}'.")
    else:
        raise ValueError("Unsupported content format for bad word detection.")