from django.urls import path
from . import views

urlpatterns = [
    path('me/', views.UserProfileAPIView.as_view(), name='user-profile'),
    path('social/jwt/', views.SocialAuthJWTView.as_view(), name='social-jwt'),
    path('list/', views.UserListView.as_view(), name='user-list'),
]