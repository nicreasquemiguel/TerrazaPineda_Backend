import json
from django.conf import settings

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

SCOPES = ['https://www.googleapis.com/auth/calendar']

# Map booking status → Google Calendar color IDs
# https://developers.google.com/calendar/api/v3/reference/colors/get
_STATUS_COLOR = {
    'solicitud': '5',           # Banana (yellow) — pending request
    'aceptacion': '2',          # Sage (green) — accepted
    'apartado': '3',            # Grape (purple) — deposit paid
    'liquidado': '10',          # Basil (dark green) — fully paid
    'liquidado_entregado': '10',
    'entregado': '9',           # Blueberry — venue handed over
    'finalizado': '8',          # Graphite — finished
    'cancelado': '11',          # Tomato (red) — cancelled
    'rechazado': '11',          # Tomato (red) — rejected
}


def _get_service():
    if not GOOGLE_AVAILABLE:
        return None

    credentials_json = getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_JSON', None)
    key_file = getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_KEY_FILE', None)

    if not credentials_json and not key_file:
        return None

    try:
        if credentials_json:
            info = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(
                info, scopes=SCOPES
            )
        else:
            credentials = service_account.Credentials.from_service_account_file(
                key_file, scopes=SCOPES
            )
        return build('calendar', 'v3', credentials=credentials)
    except Exception as e:
        print(f"[Google Calendar] Failed to build service: {e}")
        return None


def _build_event_body(booking):
    user = booking.user
    full_name = user.get_full_name() if hasattr(user, 'get_full_name') else ''
    display_name = full_name.strip() or user.email

    description_lines = [
        f"Cliente: {display_name}",
        f"Email: {user.email}",
        f"Lugar: {booking.venue.name}",
        f"Paquete: {booking.package.title} ({booking.package.n_people} personas)",
        f"Estado: {booking.get_status_display()}",
        f"Total: ${booking.total_price}",
        f"Adelanto: ${booking.advance_paid}",
    ]

    try:
        extras = list(booking.extra_services.all())
        if extras:
            description_lines.append(f"Servicios extra: {', '.join(e.name for e in extras)}")
    except Exception:
        pass

    if booking.description:
        description_lines.append(f"Notas: {booking.description}")

    return {
        'summary': f"Reserva: {display_name} — {booking.venue.name}",
        'description': '\n'.join(description_lines),
        'start': {
            'dateTime': booking.start_datetime.isoformat(),
            'timeZone': settings.TIME_ZONE,
        },
        'end': {
            'dateTime': booking.end_datetime.isoformat(),
            'timeZone': settings.TIME_ZONE,
        },
        'colorId': _STATUS_COLOR.get(booking.status, '1'),
    }


def create_event(booking):
    """Create a Google Calendar event for a booking. Returns the event ID or None."""
    service = _get_service()
    if not service:
        return None

    calendar_id = getattr(settings, 'GOOGLE_CALENDAR_ID', 'primary')
    try:
        event = service.events().insert(
            calendarId=calendar_id,
            body=_build_event_body(booking),
        ).execute()
        return event.get('id')
    except HttpError as e:
        print(f"[Google Calendar] API error creating event: {e}")
        return None
    except Exception as e:
        print(f"[Google Calendar] Error creating event: {e}")
        return None


def update_event(booking, event_id):
    """Update an existing Google Calendar event. Returns True on success."""
    service = _get_service()
    if not service or not event_id:
        return False

    calendar_id = getattr(settings, 'GOOGLE_CALENDAR_ID', 'primary')
    try:
        service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=_build_event_body(booking),
        ).execute()
        return True
    except HttpError as e:
        print(f"[Google Calendar] API error updating event {event_id}: {e}")
        return False
    except Exception as e:
        print(f"[Google Calendar] Error updating event {event_id}: {e}")
        return False


def delete_event(event_id):
    """Delete a Google Calendar event. Returns True on success."""
    service = _get_service()
    if not service or not event_id:
        return False

    calendar_id = getattr(settings, 'GOOGLE_CALENDAR_ID', 'primary')
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return True
    except HttpError as e:
        print(f"[Google Calendar] API error deleting event {event_id}: {e}")
        return False
    except Exception as e:
        print(f"[Google Calendar] Error deleting event {event_id}: {e}")
        return False
