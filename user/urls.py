from django.urls import path
from .views import (
    RegisterView,
    UserDetailView,
    UserProfileView,
    UserDashboardView,
    UserSubmissionsView,
)

urlpatterns = [
    path('register/',    RegisterView.as_view(),       name='user-register'),
    path('me/',          UserDetailView.as_view(),     name='user-detail'),
    path('me/profile/',  UserProfileView.as_view(),    name='user-profile'),
    path('dashboard/',   UserDashboardView.as_view(),  name='user-dashboard'),
    path('submissions/', UserSubmissionsView.as_view(), name='user-submissions'),
]
