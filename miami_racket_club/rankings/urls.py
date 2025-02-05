from django.urls import path
from . import views

urlpatterns = [
    path('submit/', views.submit_match, name='submit_match'),
    path('player-directory/', views.player_directory, name='player_directory'),
    path('leaderboard/', views.leaderboard, name='leaderboard')
]