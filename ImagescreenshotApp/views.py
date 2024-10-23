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
import cv2
from pynput import keyboard,mouse
import threading

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
        print("screen shot taken")

        # Save screenshot to a bytes buffer
        buffer = io.BytesIO()
        screenshot.save(buffer, format='PNG')
        image_content = ContentFile(buffer.getvalue())

        image = Image(user=user)
        print("screenshot taken")
        image.image.save(f"screenshots/screenshot_{user.id}_{int(time.time())}.png", image_content)

        # Refresh the user object to get the latest stop_screenshots value
        user.refresh_from_db()

def capture_face(user):
    user = User.objects.get(pk=user.id)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(0)

    while not user.stop_screenshots:
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        if len(faces) > 0:
            x, y, w, h = faces[0]
            face = frame[y:y+h, x:x+w]

            # Convert the face image to bytes
            _, buffer = cv2.imencode('.jpg', face)
            face_bytes = buffer.tobytes()

            # Save the face capture
            face_capture = FaceCapture(user=user)
            face_capture.image.save(f"face_captures/face_{user.id}_{int(time.time())}.jpg", ContentFile(face_bytes))

            # Sleep for a while before capturing the next face
            time.sleep(60)  # Capture face every minute

        user.refresh_from_db()

    cap.release()

@login_required_decorator
def start_screenshot_capture(request):
    # Reset the stop_screenshots flag when starting capture
    request.user.stop_screenshots = False
    request.user.save()

    # Start the screenshot capture in a separate thread
    thread = Thread(target=take_random_screenshots, args=(request.user,))
    thread.daemon = True
    thread.start()

    # Start the activity tracking in a separate thread
    activity_thread = Thread(target=track_activity, args=(request.user,))
    activity_thread.daemon = True
    activity_thread.start()
    
    return JsonResponse({"success": True, "message": "Screenshot capture and activity tracking started."})

@login_required_decorator
def logout(request):
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=request.user.id)
        user.stop_screenshots = True
        user.save()
    
    auth_logout(request)
    return JsonResponse({"success": True, "message": "Logged out successfully."})

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

def track_activity(user):
    user = User.objects.get(pk=user.id)
    key_count = 0
    mouse_count = 0
    last_activity_time = time.time()
    activity_intensity = 0

    # Create or get ActivityIntensity instance for the user
    activity_intensity_obj, created = activityIntensity.objects.get_or_create(user=user)

    def on_press(key):
        nonlocal key_count, last_activity_time, activity_intensity
        key_count += 1
        update_activity()

    def on_click(x, y, button, pressed):
        nonlocal mouse_count, last_activity_time, activity_intensity
        if pressed:
            mouse_count += 1
            update_activity()

    def on_scroll(x, y, dx, dy):
        nonlocal mouse_count, last_activity_time, activity_intensity
        mouse_count += 1
        update_activity()

    def update_activity():
        nonlocal key_count, mouse_count, last_activity_time, activity_intensity, activity_intensity_obj
        current_time = time.time()
        time_diff = current_time - last_activity_time
        
        # Calculate activity intensity based on time between actions
        if time_diff < 0.5:  # High intensity if actions are frequent
            activity_intensity += 2
        elif time_diff < 1:  # Medium intensity
            activity_intensity += 1
        else:  # Low intensity
            activity_intensity = max(0, activity_intensity - 1)
        
        last_activity_time = current_time

        # Update user's activity data every 100 actions
        if (key_count + mouse_count) % 100 == 0:
            with transaction.atomic():
                activity_intensity_obj.refresh_from_db()
                activity_intensity_obj.key_count += key_count
                activity_intensity_obj.mouse_count += mouse_count
                activity_intensity_obj.activity_intensity = min(10, activity_intensity)  # Cap intensity at 10
                activity_intensity_obj.save()
            key_count = 0
            mouse_count = 0

    # Start key and mouse listeners
    keyboard_listener = keyboard.Listener(on_press=on_press)
    mouse_listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
    
    keyboard_listener.start()
    mouse_listener.start()

    while not user.stop_screenshots:
        time.sleep(1)
        user.refresh_from_db()

    keyboard_listener.stop()
    mouse_listener.stop()




# Removed features

# @login_required_decorator
# def stop_screenshot_capture(request):
#     elapsed_time = request.GET.get('elapsedTime')

#     with transaction.atomic():
#         user = User.objects.select_for_update().get(pk=request.user.id)
#         user.stop_screenshots = True
#         user.save()
#         user = User.objects.get(id=request.user.id)
#         DailyTimestamp.objects.create(user=user, time=elapsed_time)
#     return JsonResponse({"success": True, "message": "Screenshot capture stopped."})

# Add a new view to update elapsed time

