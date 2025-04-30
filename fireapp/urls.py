# fireapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('start/', views.start_detection, name='start_detection'),
    path('video_feed/', views.video_feed, name='video_feed'),  #Added for video streaming
    path('stop/', views.stop_detection, name='stop_detection'),  #Added for stop button
    path('logs/', views.show_logs, name='show_logs'),
    path('delete-log/<int:id>/', views.delete_log, name='delete_log'),
    path('delete-all-logs/', views.delete_all_logs, name='delete_all_logs'),
]
