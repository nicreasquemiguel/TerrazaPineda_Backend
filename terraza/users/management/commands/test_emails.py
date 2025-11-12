from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.email_service import TerrazaEmailService

User = get_user_model()

class Command(BaseCommand):
    help = 'Test email sending functionality'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email address to send test email to')
        parser.add_argument('--type', type=str, choices=['activation', 'password_reset', 'booking'], 
                          default='activation', help='Type of email to test')

    def handle(self, *args, **options):
        email = options['email']
        email_type = options['type']
        
        if not email:
            self.stdout.write(self.style.ERROR('Please provide an email address with --email'))
            return
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with email {email} not found'))
            return
        
        self.stdout.write(f'Sending {email_type} email to {email}...')
        
        if email_type == 'activation':
            # This would normally be handled by Djoser
            self.stdout.write(self.style.SUCCESS('Activation emails are handled by Djoser automatically'))
        elif email_type == 'password_reset':
            # This would normally be handled by Djoser
            self.stdout.write(self.style.SUCCESS('Password reset emails are handled by Djoser automatically'))
        elif email_type == 'booking':
            # Test booking confirmation email
            from booking.models import Booking
            booking = Booking.objects.filter(user=user).first()
            if booking:
                TerrazaEmailService.send_booking_confirmation(user, booking)
                self.stdout.write(self.style.SUCCESS(f'Booking confirmation email sent for booking #{booking.id}'))
            else:
                self.stdout.write(self.style.ERROR('No bookings found for this user'))
        
        self.stdout.write(self.style.SUCCESS('Email test completed!'))
