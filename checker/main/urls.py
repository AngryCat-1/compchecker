from django.urls import path, include
from . import views

urlpatterns = [
    path('get', views.get),
    path('cmd', views.cmd),
    path('file', views.file_post),
    path('notify', views.notify),
    path('screen', views.screen),
    path('block', views.block_sites),
]
