from django.urls import path
from . import views

urlpatterns = [
    path('submit/', views.submit_match, name='submit_match'),
    path('leaderboard/', views.leaderboard, name='leaderboard')
]