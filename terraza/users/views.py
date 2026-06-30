from django.shortcuts import render
from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from djoser.views import UserViewSet as DjoserUserViewSet
from djoser import signals as djoser_signals
from djoser.conf import settings as djoser_settings
from djoser.utils import get_user_email
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
        to = [get_user_email(user)]
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