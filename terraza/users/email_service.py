from django.core.mail.backends.smtp import EmailBackend
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def _contact_email():
    return getattr(settings, 'CONTACT_EMAIL', settings.DEFAULT_FROM_EMAIL)


class CustomEmailBackend(EmailBackend):
    def send_messages(self, email_messages):
        for message in email_messages:
            message.extra_headers = message.extra_headers or {}
            message.extra_headers['X-Mailer'] = 'Terraza Pineda System'
            message.extra_headers['X-Priority'] = '3'
            logger.info(f"Sending email to {message.to} with subject: {message.subject}")
        return super().send_messages(email_messages)


class TerrazaEmailService:

    @staticmethod
    def send_booking_confirmation(user, booking):
        date_str = booking.start_datetime.strftime('%d/%m/%Y')
        subject = f'Reserva confirmada · {user.first_name} · {date_str} - Terraza Pineda'

        html_content = render_to_string('email/booking_confirmation.html', {
            'user': user,
            'booking': booking,
            'domain': settings.SITE_URL_FRONTEND,
            'contact_email': _contact_email(),
        })

        text_content = (
            f"Hola {user.first_name},\n\n"
            f"Tu reserva ha sido confirmada.\n\n"
            f"Fecha: {booking.start_datetime.strftime('%d/%m/%Y %H:%M')}\n"
            f"Lugar: {booking.venue.name}\n"
            f"Paquete: {booking.package if booking.package else 'Personalizado'}\n\n"
            f"Gracias por elegir Terraza Pineda.\n"
            f"El equipo de Terraza Pineda"
        )

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Booking confirmation sent to {user.email}")

    @staticmethod
    def send_booking_status_update(user, booking, old_status):
        date_str = booking.start_datetime.strftime('%d/%m/%Y')
        subject = f'Actualización de reserva · {user.first_name} · {date_str} - Terraza Pineda'

        html_content = render_to_string('email/booking_status_update.html', {
            'user': user,
            'booking': booking,
            'old_status': old_status,
            'domain': settings.SITE_URL_FRONTEND,
            'contact_email': _contact_email(),
        })

        text_content = (
            f"Hola {user.first_name},\n\n"
            f"El estado de tu reserva ha cambiado.\n\n"
            f"Estado anterior: {old_status}\n"
            f"Estado actual: {booking.get_status_display()}\n\n"
            f"Fecha: {booking.start_datetime.strftime('%d/%m/%Y %H:%M')}\n"
            f"Lugar: {booking.venue.name}\n\n"
            f"El equipo de Terraza Pineda"
        )

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Booking status update sent to {user.email}")
