from rest_framework.views import exception_handler
from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    if isinstance(exc, IntegrityError):
        if 'booking_event_slug_key' in str(exc):
            return Response(
                {"detail": "A booking with this slug already exists."},
                status=status.HTTP_409_CONFLICT
            )
        return Response(
            {"detail": "A database error occurred."},
            status=status.HTTP_400_BAD_REQUEST
        )
    return exception_handler(exc, context) 