from django.urls import path
from . import views

app_name = 'downloader'

urlpatterns = [
    path('', views.home, name='home'),
    path('download/', views.download_video, name='download_video'),
    path('get-info/', views.get_video_info, name='get_video_info'),
]