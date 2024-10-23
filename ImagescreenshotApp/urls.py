from django.urls import path
from . import views


urlpatterns = [
    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('', views.home, name='home'),
    path('start_screenshot_capture/', views.start_screenshot_capture, name='start_screenshot_capture'),
    path('logout/', views.logout, name='logout'),
    path('screenshot_list/', views.screenshot_list, name='screenshot_list'),
    # path('stop_screenshot_capture/', views.stop_screenshot_capture, name='stop_screenshot'),
    path('pause_screenshot_capture/', views.pause_screenshot_capture, name='pause_screenshot'),
    path('resume_screenshot_capture/', views.resume_screenshot_capture, name='resume_screenshot'),
    path('update_elapsed_time/', views.update_elapsed_time, name='update_elapsed_time'),
    

]
