from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from functools import wraps
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from PIL import ImageGrab
import random
import time
from threading import Thread
from .models import Image
from django.core.files.base import ContentFile
import io
from django.http import JsonResponse
from django.db import transaction
from playsound import playsound
import os
from .models import *

from django.contrib.auth import get_user_model

User = get_user_model()

# Create your views here.
def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                auth_login(request, user)
                return redirect('home')  # Replace 'home' with your home page URL name
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if username and email and password:
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
            elif User.objects.filter(email=email).exists():
                messages.error(request, "Email already exists.")
            else:
                user = User.objects.create(
                    username=username,
                    email=email,
                    password=make_password(password)
                )
                messages.success(request, "Registration successful. Please log in.")
                return redirect('login')
        else:
            messages.error(request, "Please provide all required fields.")
    
    return render(request, 'signup.html')

def login_required_decorator(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        else:
            return redirect('login')  # Redirect to login page if user is not authenticated
    return wrapper

@login_required_decorator
def home(request):
    return render(request, 'home.html')

def take_random_screenshots(user):
    user = User.objects.get(pk=user.id)
    while not user.stop_screenshots:
        # Random interval between 1 to 10 minutes
        interval = random.randint(6, 10)
        print("interval", interval)
        time.sleep(interval)
        
        user.refresh_from_db()

        # Skip taking screenshot if paused
        if user.pause_screenshots:
            continue

        # Take screenshot
        screenshot = ImageGrab.grab()

        # Play sound
        sound_file = os.path.join(os.path.dirname(__file__), 'screenshot.mp3')
        playsound(sound_file)

        # Save screenshot to a bytes buffer
        buffer = io.BytesIO()
        screenshot.save(buffer, format='PNG')
        image_content = ContentFile(buffer.getvalue())

        image = Image(user=user)
        print("screenshot taken")
        image.image.save(f"screenshots/screenshot_{user.id}_{int(time.time())}.png", image_content)

        # Refresh the user object to get the latest stop_screenshots value
        user.refresh_from_db()

@login_required_decorator
def start_screenshot_capture(request):
    # Reset the stop_screenshots flag when starting capture
    request.user.stop_screenshots = False
    request.user.save()
    
    # Start the screenshot capture in a separate thread
    thread = Thread(target=take_random_screenshots, args=(request.user,))
    thread.daemon = True
    thread.start()
    return JsonResponse({"success": True, "message": "Screenshot capture started."})

@login_required_decorator
def logout(request):
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=request.user.id)
        user.stop_screenshots = True
        user.save()
    
    auth_logout(request)
    return JsonResponse({"success": True, "message": "Screenshot capture started."})

@login_required_decorator
def screenshot_list(request):
    images = Image.objects.filter(user=request.user).order_by('-date_taken')
    
    screenshots = [{
        'image_url': image.image.url,
        'title': f"Screenshot {image.id}",
        'date_taken': image.date_taken.strftime('%Y-%m-%d %H:%M:%S')
    } for image in images]
    
    return render(request, 'screenshot_list.html', {'screenshots': screenshots})

@login_required_decorator
def stop_screenshot_capture(request):
    elapsed_time = request.GET.get('elapsedTime')

    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=request.user.id)
        user.stop_screenshots = True
        user.save()
        user = User.objects.get(id=request.user.id)
        DailyTimestamp.objects.create(user=user, time=elapsed_time)
    return JsonResponse({"success": True, "message": "Screenshot capture stopped."})


@login_required_decorator
def pause_screenshot_capture(request):
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=request.user.id)
        user.pause_screenshots = True
        user.save()
    return JsonResponse({"success": True, "message": "Screenshot capture paused."})

@login_required_decorator
def resume_screenshot_capture(request):
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=request.user.id)
        user.pause_screenshots = False
        user.save()
    return JsonResponse({"success": True, "message": "Screenshot capture resumed."})



