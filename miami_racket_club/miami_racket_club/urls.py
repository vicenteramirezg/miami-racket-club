from django.contrib import admin
from django.urls import path, include
from rankings.views import SignUpView
from rankings import views

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', SignUpView.as_view(), name='signup'),
    path('terms-and-conditions/', views.terms_and_conditions, name='terms_and_conditions'),
    path('profile/<str:username>/', views.profile, name='profile'),
    
    # Add the pending approval page URL pattern here
    path('pending-approval/', views.pending_approval, name='pending_approval'),
    
    path('', include('rankings.urls')),
]
