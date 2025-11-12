from django.core.mail.backends.smtp import EmailBackend
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class CustomEmailBackend(EmailBackend):
    """
    Custom email backend that adds branding and logging to Djoser emails
    """
    
    def send_messages(self, email_messages):
        """
        Override send_messages to customize Djoser emails
        """
        for message in email_messages:
            # Add custom headers for tracking
            message.extra_headers = message.extra_headers or {}
            message.extra_headers['X-Mailer'] = 'Terraza Pineda System'
            message.extra_headers['X-Priority'] = '3'
            
            # Log email sending for debugging
            logger.info(f"Sending email to {message.to} with subject: {message.subject}")
            
        return super().send_messages(email_messages)

class TerrazaEmailService:
    """
    Custom email service for Terraza Pineda specific emails
    """
    
    @staticmethod
    def send_booking_confirmation(user, booking):
        """
        Send custom booking confirmation email
        """
        subject = f'Confirmación de reserva #{booking.id} - Terraza Pineda'
        
        # Create HTML content
        html_content = render_to_string('email/booking_confirmation.html', {
            'user': user,
            'booking': booking,
            'domain': settings.SITE_URL_FRONTEND,
        })
        
        # Create text content
        text_content = f"""
        Hola {user.first_name},
        
        Tu reserva ha sido confirmada exitosamente.
        
        Detalles de la reserva:
        - ID: #{booking.id}
        - Fecha: {booking.start_datetime.strftime('%d/%m/%Y %H:%M')}
        - Lugar: {booking.venue.name}
        - Paquete: {booking.package.title if booking.package else 'Personalizado'}
        
        Gracias por elegir Terraza Pineda.
        
        El equipo de Terraza Pineda
        """
        
        # Send email
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        logger.info(f"Booking confirmation email sent to {user.email} for booking #{booking.id}")
    
    @staticmethod
    def send_booking_status_update(user, booking, old_status):
        """
        Send booking status update email
        """
        subject = f'Actualización de reserva #{booking.id} - Terraza Pineda'
        
        html_content = render_to_string('email/booking_status_update.html', {
            'user': user,
            'booking': booking,
            'old_status': old_status,
            'domain': settings.SITE_URL_FRONTEND,
        })
        
        text_content = f"""
        Hola {user.first_name},
        
        El estado de tu reserva #{booking.id} ha cambiado.
        
        Estado anterior: {old_status}
        Estado actual: {booking.get_status_display()}
        
        Fecha del evento: {booking.start_datetime.strftime('%d/%m/%Y %H:%M')}
        Lugar: {booking.venue.name}
        
        Si tienes preguntas, no dudes en contactarnos.
        
        El equipo de Terraza Pineda
        """
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        logger.info(f"Booking status update email sent to {user.email} for booking #{booking.id}")
