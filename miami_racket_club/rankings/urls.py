from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import CustomLoginView, CustomPasswordResetView


urlpatterns = [
    path('submit/', views.submit_match, name='submit_match'),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('player-directory/', views.player_directory, name='player_directory'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('password-reset/', CustomPasswordResetView.as_view(  # Use the custom view
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',  # Plain text fallback
        html_email_template_name='registration/password_reset_email.html'  # HTML email
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
    path('username-retrieval/', views.username_retrieval, name='username_retrieval'),
    path('username-retrieval/done/', views.username_retrieval_done, name='username_retrieval_done'),
]