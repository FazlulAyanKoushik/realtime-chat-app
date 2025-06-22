# chat/urls.py
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('threads/', views.ThreadListView.as_view(), name='thread-list'),
    path('threads/create/', views.ThreadCreateView.as_view(), name='thread-create'),
    path('threads/<uuid:thread_uid>/assign-admin/', views.AssignAdminView.as_view(), name='assign-admin'),
    path('threads/<uuid:thread_uid>/messages/', views.MessageListView.as_view(), name='message-list'),
    path('threads/<uuid:thread_uid>/messages/create/', views.MessageCreateView.as_view(), name='message-create'),
]