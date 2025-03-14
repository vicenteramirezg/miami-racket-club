from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from rankings.views import SignUpView
from rankings import views
from django.conf.urls import handler404

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', SignUpView.as_view(), name='signup'),
    path('terms-and-conditions/', views.terms_and_conditions, name='terms_and_conditions'),
    path('faq/', views.faq, name='faq'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('pending-approval/', views.pending_approval, name='pending_approval'),
    
    # Include app-specific URLs
    path('', include('rankings.urls')),
]

def custom_404_view(request, exception):
    return render(request, "404.html", status=404)

handler404 = custom_404_view