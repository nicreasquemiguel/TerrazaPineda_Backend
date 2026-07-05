from django.shortcuts import render
from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from djoser.views import UserViewSet as DjoserUserViewSet
from djoser import signals as djoser_signals
from djoser.conf import settings as djoser_settings
from rest_framework_simplejwt.tokens import RefreshToken
import requests as http_requests
import logging

from .serializers import ProfileSerializer, UserProfileUpdateSerializer
from .models import UserAccount, Profile

logger = logging.getLogger(__name__)


class SafeUserViewSet(DjoserUserViewSet):
    def perform_create(self, serializer):
        # Create the user atomically; email is sent outside the transaction
        # so an SMTP failure does not roll back the account or return a 500.
        with transaction.atomic():
            user = serializer.save()
            djoser_signals.user_registered.send(
                sender=self.__class__, user=user, request=self.request
            )

        context = {"user": user}
        to = [user.email]
        try:
            if djoser_settings.SEND_ACTIVATION_EMAIL:
                djoser_settings.EMAIL.activation(self.request, context).send(to)
            elif djoser_settings.SEND_CONFIRMATION_EMAIL:
                djoser_settings.EMAIL.confirmation(self.request, context).send(to)
        except Exception as exc:
            logger.error("Failed to send registration email to %s: %s", user.email, exc)


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ProfileSerializer

    def get_object(self):
        user_id = self.kwargs['user_id']
        user = UserAccount.objects.get(id=user_id)
        profile = Profile.objects.get(user=user)
        print(profile.total_events)
        return profile
    
    def patch(self, request, *args, **kwargs):

        payload = request.data
        user = UserAccount.objects.get(id=payload["user_id"])

        user.first_name = payload["first_name"]
        user.last_name = payload["last_name"]
        user.phone = payload["phone"]
        user.email = payload["email"]
        user.save()

        return Response({"message": "Profile changed successfully"}, status=status.HTTP_200_OK)
    


class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileUpdateSerializer

    def get_object(self):
        return self.request.user


class SocialAuthJWTView(APIView):
    """
    Exchange a Google id_token or Facebook access_token for JWT tokens.

    POST /api/users/social/jwt/
    Body: { "provider": "google" | "facebook", "token": "<token>" }
    Returns: { "access": "...", "refresh": "...", "created": true/false }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        provider = request.data.get('provider', '').lower()
        token = request.data.get('token', '').strip()

        if not provider or not token:
            return Response(
                {'detail': 'Se requieren los campos provider y token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if provider == 'google':
            user_info = self._verify_google(token)
        elif provider == 'facebook':
            user_info = self._verify_facebook(token)
        else:
            return Response(
                {'detail': f'Proveedor no soportado: {provider}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_info is None:
            return Response(
                {'detail': 'Token inválido o expirado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = user_info.get('email')
        if not email:
            return Response(
                {'detail': 'El proveedor no devolvió un correo electrónico.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, created = UserAccount.objects.get_or_create(
            email=email,
            defaults={
                'first_name': user_info.get('first_name', ''),
                'last_name': user_info.get('last_name', ''),
                'is_active': True,
                'email_verified': True,
            },
        )

        if not created:
            # Ensure existing accounts can log in via social (mark active/verified)
            changed = False
            if not user.is_active:
                user.is_active = True
                changed = True
            if not user.email_verified:
                user.email_verified = True
                changed = True
            if changed:
                user.save(update_fields=['is_active', 'email_verified'])

        # Save profile picture from social provider (only when it's still the default)
        picture_url = user_info.get('picture')
        if picture_url:
            try:
                profile = Profile.objects.get(user=user)
                is_default = not profile.image or 'default_user' in str(profile.image)
                if is_default:
                    self._save_social_picture(profile, picture_url, user.id)
            except Profile.DoesNotExist:
                pass

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'created': created,
        }, status=status.HTTP_200_OK)

    def _verify_google(self, token):
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests
            from django.conf import settings

            # Try verifying as id_token first
            client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), client_id if client_id else None
            )
            return {
                'email': idinfo.get('email'),
                'first_name': idinfo.get('given_name', ''),
                'last_name': idinfo.get('family_name', ''),
                'picture': idinfo.get('picture'),
            }
        except Exception:
            pass

        # Fallback: treat token as access_token and call userinfo endpoint
        try:
            resp = http_requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {token}'},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'email': data.get('email'),
                    'first_name': data.get('given_name', ''),
                    'last_name': data.get('family_name', ''),
                    'picture': data.get('picture'),
                }
        except Exception as exc:
            logger.warning('Google userinfo fallback failed: %s', exc)

        return None

    def _verify_facebook(self, token):
        try:
            resp = http_requests.get(
                'https://graph.facebook.com/me',
                params={'fields': 'email,first_name,last_name', 'access_token': token},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if 'error' not in data:
                    fb_id = data.get('id')
                    return {
                        'email': data.get('email'),
                        'first_name': data.get('first_name', ''),
                        'last_name': data.get('last_name', ''),
                        'picture': f'https://graph.facebook.com/{fb_id}/picture?type=large' if fb_id else None,
                    }
        except Exception as exc:
            logger.warning('Facebook token verification failed: %s', exc)

        return None

    def _save_social_picture(self, profile, url, user_id):
        try:
            from django.core.files.base import ContentFile
            import urllib.request
            import os

            with urllib.request.urlopen(url, timeout=10) as response:
                image_data = response.read()

            ext = 'jpg'
            content_type = response.headers.get('Content-Type', '')
            if 'png' in content_type:
                ext = 'png'
            elif 'webp' in content_type:
                ext = 'webp'

            filename = f'social_{user_id}.{ext}'
            profile.image.save(filename, ContentFile(image_data), save=True)
        except Exception as exc:
            logger.warning('Failed to save social profile picture: %s', exc)