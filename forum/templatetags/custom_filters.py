from django import template

register = template.Library()

@register.filter(name='endswith')
def endswith(value, arg):
    return value.lower().endswith(arg)


@register.filter
def image_files(files):
    return [file for file in files if file.file.url.lower().endswith(('.jpg', '.jpeg', '.png'))]


@register.filter
def media_files(files):
    return [file for file in files if file.file.url.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.webm', '.ogg'))]

@register.filter
def exclude_media_files(files):
    return [file for file in files if not file.file.url.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.webm', '.ogg'))]