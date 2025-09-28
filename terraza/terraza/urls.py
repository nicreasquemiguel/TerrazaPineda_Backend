"""terraza URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path

from django.conf import settings
from django.conf.urls.static import static
# from django.conf.urls import url

from booking.views import *
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from rest_framework import permissions
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)


# router = DefaultRouter()
# # router.register('lugares', VenueViewSet, basename='lugares')
# router.register('orders', OrdersView, basename='orders')



urlpatterns = [
    path('admin/', admin.site.urls),

    # Djoser auth endpoints: registration, login, logout, password reset, activation, token management
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),

    # Social auth URLs (if using social-auth-app-django)
    path('auth/social/', include('social_django.urls', namespace='social')),

    # Your users app API (optional, if you have extra views)
    path('api/users/', include('users.urls')),

    # Other apps (booking, payments, etc.)
    path('api/bookings/', include('booking.urls')),
    path('api/store/', include('store.urls')),
    path('api/dashboard/', include('dashboard.urls')),
    path('api/logs/', include('logs.urls')),
    
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]


# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)