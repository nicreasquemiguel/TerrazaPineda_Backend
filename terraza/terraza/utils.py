import logging
import traceback

from django.conf import settings as django_settings
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    if isinstance(exc, IntegrityError):
        if 'booking_event_slug_key' in str(exc):
            return Response(
                {"detail": "A booking with this slug already exists."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {"detail": "A database error occurred."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Let DRF handle its own exceptions (ValidationError, NotFound, etc.)
    response = exception_handler(exc, context)

    if response is not None:
        return response

    # Unhandled exception → log the full traceback so we can diagnose it
    request = context.get('request')
    tb = traceback.format_exc()
    logger.error(
        "Unhandled exception in %s %s\n%s",
        getattr(request, 'method', 'UNKNOWN'),
        getattr(request, 'path', 'UNKNOWN'),
        tb,
        exc_info=exc,
    )

    body = {"detail": f"Internal server error: {type(exc).__name__}: {exc}"}
    if django_settings.DEBUG:
        body["traceback"] = tb

    return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)