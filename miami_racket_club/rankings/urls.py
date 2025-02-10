from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import CustomLoginView

urlpatterns = [
    path('submit/', views.submit_match, name='submit_match'),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('player-directory/', views.player_directory, name='player_directory'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('username-retrieval/', views.username_retrieval, name='username_retrieval'),
    path('username-retrieval/done/', views.username_retrieval_done, name='username_retrieval_done'),
]