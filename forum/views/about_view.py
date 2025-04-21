from django.shortcuts import render

def about_view(request):
    """
    Render the About page for the WolfKey platform.
    """
    return render(request, 'forum/about.html')