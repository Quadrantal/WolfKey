from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from forum.models import User, Course, UserCourseHelp, UserCourseExperience
from forum.forms import CustomUserCreationForm
import json

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        # print(form)
        if form.is_valid():
            current_courses = request.POST.get('current_courses', '').split(',')
            experienced_courses = request.POST.get('experienced_courses', '').split(',')
            
            # print(current_courses)
            # print(experienced_courses)
            
            
            if len(experienced_courses) < 5:
                messages.error(request, 'You must select at least 5 experienced courses.')
                return render(request, 'forum/register.html', {
                    'form': form,
                    'courses': Course.objects.all().order_by('name'),
                    'form_errors': form.errors.as_json()  
                })
            if len(current_courses) < 3:
                messages.error(request, 'You must select at least 3 courses you need help with.')
                return render(request, 'forum/register.html', {
                    'form': form,
                    'courses': Course.objects.all().order_by('name'),
                    'form_errors': form.errors.as_json()  
            })
            user = form.save()
            
            # Add current courses as help needed
            for course_id in current_courses:
                UserCourseHelp.objects.create(
                    user=user,
                    course_id=course_id,
                    active=True
                )
                
            # Add experienced courses
            for course_id in experienced_courses:
                UserCourseExperience.objects.create(
                    user=user,
                    course_id=course_id
                )
            
            login(request, user)
            messages.success(request, 'Welcome to Student Forum!')
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
            user = form.get_user()
            login(request, user)
            messages.success(request, 'You are now logged in!')
            return redirect('for_you')
        else:
            school_email = request.POST.get('username')  # AuthenticationForm uses 'username' field
            try:
                user = User.objects.get(school_email=school_email)
                # print(f"User exists: {user.school_email}, is_active: {user.is_active}")
            except User.DoesNotExist:
                # print(f"No user with email: {school_email}")
                pass
    else:
        form = AuthenticationForm()
    return render(request, 'forum/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('all_posts')