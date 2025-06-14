from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from forum.models import User, Course, UserCourseHelp, UserCourseExperience
from forum.forms import CustomUserCreationForm, CustomPasswordResetForm
import json
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.urls import reverse_lazy
from forum.services.auth_services import authenticate_and_login_user, register_user

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        
        if form.is_valid():
            current_courses = request.POST.get('current_courses', '').split(',')
            experienced_courses = request.POST.get('experienced_courses', '').split(',')
            
            user, error = register_user(request, form, current_courses, experienced_courses)
            
            if error:
                messages.error(request, error)
            else:
                messages.success(request, 'Welcome to WolfKey!')
                return redirect('all_posts')
        else:
            current_course_ids = request.POST.get('current_courses', '').split(',')
            experienced_course_ids = request.POST.get('experienced_courses', '').split(',')

            current_course_ids = [int(id) for id in current_course_ids if id]
            experienced_course_ids = [int(id) for id in experienced_course_ids if id]

            current_courses = list(Course.objects.filter(id__in=current_course_ids).values('id', 'name', 'code'))
            experienced_courses = list(Course.objects.filter(id__in=experienced_course_ids).values('id', 'name', 'code'))

            return render(request, 'forum/register.html', {
                'form': form,
                'courses': Course.objects.all().order_by('name'),
                'form_errors': form.errors.as_json(),
                'selected_current_courses': json.dumps(current_courses),
                'selected_experienced_courses': json.dumps(experienced_courses) 
            })
    else:
        form = CustomUserCreationForm()
    
    courses = Course.objects.all().order_by('name')
    return render(request, 'forum/register.html', {
        'form': form,
        'courses': courses
    })

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            school_email = form.cleaned_data.get('username')  # AuthenticationForm uses 'username' field
            password = form.cleaned_data.get('password')

            user, error = authenticate_and_login_user(request, school_email, password)
            if user:
                messages.success(request, 'You are now logged in!')
                return redirect('for_you')
            else:
                form.add_error(None, error)
        else:
            form.add_error(None, "Invalid credentials. Please try again.")
    else:
        form = AuthenticationForm()

    return render(request, 'forum/login.html', {'form': form})


from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('all_posts')

class CustomPasswordResetView(PasswordResetView):
    template_name = 'forum/registration/password_reset.html'
    email_template_name = 'forum/registration/password_reset_email.html'
    html_email_template_name = 'forum/registration/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')
    form_class = CustomPasswordResetForm

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'forum/registration/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'forum/registration/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'forum/registration/password_reset_complete.html'