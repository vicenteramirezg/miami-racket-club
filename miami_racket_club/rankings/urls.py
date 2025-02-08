from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import CustomLoginView

urlpatterns = [
    path('submit/', views.submit_match, name='submit_match'),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('player-directory/', views.player_directory, name='player_directory'),
    path('leaderboard/', views.leaderboard, name='leaderboard')
]