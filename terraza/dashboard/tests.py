from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

from .models import AdminAction
from booking.models import Booking, Venue, Package
from store.models import PaymentOrder, Payment

User = get_user_model()

class PendingCashTransferPaymentsTestCase(APITestCase):
    def setUp(self):
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        
        # Create venue
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='Test Address'
        )
        
        # Create package
        self.package = Package.objects.create(
            title='Test Package',
            price=100.00,
            n_people=30,
            description='Test description',
            hours='2 hours'
        )
        
        # Create future booking with status 'aceptacion'
        self.future_booking = Booking.objects.create(
            user=self.regular_user,
            venue=self.venue,
            package=self.package,
            start_datetime=timezone.now() + timedelta(days=7),
            end_datetime=timezone.now() + timedelta(days=7, hours=2),
            total_price=100.00,
            status='aceptacion'
        )
        
        # Create payment order
        self.payment_order = PaymentOrder.objects.create(
            booking=self.future_booking,
            user=self.regular_user,
            amount_due=100.00
        )
        
        # Create pending cash payment
        self.cash_payment = Payment.objects.create(
            order=self.payment_order,
            user=self.regular_user,
            method='cash',
            amount=100.00,
            status='pending',
            payment_photo_base64='base64_encoded_photo_data'
        )
        
        # Create pending transfer payment
        self.transfer_payment = Payment.objects.create(
            order=self.payment_order,
            user=self.regular_user,
            method='transfer',
            amount=100.00,
            status='pending',
            payment_photo_base64='base64_encoded_photo_data'
        )
        
        # Create past booking (should not appear in results)
        self.past_booking = Booking.objects.create(
            user=self.regular_user,
            venue=self.venue,
            package=self.package,
            start_datetime=timezone.now() - timedelta(days=7),
            end_datetime=timezone.now() - timedelta(days=7, hours=2),
            total_price=100.00,
            status='aceptacion'
        )
        
        self.past_payment_order = PaymentOrder.objects.create(
            booking=self.past_booking,
            user=self.regular_user,
            amount_due=100.00
        )
        
        self.past_payment = Payment.objects.create(
            order=self.past_payment_order,
            user=self.regular_user,
            method='cash',
            amount=100.00,
            status='pending',
            payment_photo_base64='base64_encoded_photo_data'
        )
        
        # Create paid payment (should not appear in results)
        self.paid_payment = Payment.objects.create(
            order=self.payment_order,
            user=self.regular_user,
            method='cash',
            amount=50.00,
            status='paid',
            payment_photo_base64='base64_encoded_photo_data'
        )
        
        self.client = APIClient()
    
    def test_pending_cash_transfer_payments_list(self):
        """Test listing pending cash/transfer payments"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('dashboard-pending-cash-transfer-payments')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # Should only show future pending cash/transfer payments
        self.assertEqual(data['total_pending'], 2)
        self.assertEqual(len(data['payments']), 2)
        
        # Check that only future pending payments are returned
        payment_ids = [p['payment_id'] for p in data['payments']]
        self.assertIn(str(self.cash_payment.id), payment_ids)
        self.assertIn(str(self.transfer_payment.id), payment_ids)
        self.assertNotIn(str(self.past_payment.id), payment_ids)
        self.assertNotIn(str(self.paid_payment.id), payment_ids)
        
        # Check response structure
        payment = data['payments'][0]
        required_fields = [
            'payment_id', 'booking_id', 'booking_date', 'booking_status',
            'payment_status', 'amount', 'payment_photo_base64', 'created_at',
            'user_name', 'amount_due'
        ]
        for field in required_fields:
            self.assertIn(field, payment)
    
    def test_pending_cash_transfer_payments_unauthorized(self):
        """Test that non-admin users cannot access the endpoint"""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('dashboard-pending-cash-transfer-payments')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_approve_cash_transfer_payment(self):
        """Test approving a pending cash/transfer payment"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('dashboard-approve-cash-transfer-payment')
        data = {
            'payment_id': str(self.cash_payment.id),
            'action': 'approve'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Payment approved successfully')
        
        # Check that payment status was updated
        self.cash_payment.refresh_from_db()
        self.assertEqual(self.cash_payment.status, 'paid')
        self.assertIsNotNone(self.cash_payment.paid_at)
        
        # Check that admin action was logged
        admin_action = AdminAction.objects.filter(
            action='cash_transfer_payment_approved',
            target_id=str(self.cash_payment.id)
        ).first()
        self.assertIsNotNone(admin_action)
    
    def test_reject_cash_transfer_payment(self):
        """Test rejecting a pending cash/transfer payment"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('dashboard-approve-cash-transfer-payment')
        data = {
            'payment_id': str(self.transfer_payment.id),
            'action': 'reject',
            'reason': 'Invalid payment proof'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Payment rejected successfully')
        
        # Check that payment status was updated
        self.transfer_payment.refresh_from_db()
        self.assertEqual(self.transfer_payment.status, 'failed')
        
        # Check that admin action was logged
        admin_action = AdminAction.objects.filter(
            action='cash_transfer_payment_rejected',
            target_id=str(self.transfer_payment.id)
        ).first()
        self.assertIsNotNone(admin_action)
        self.assertIn('Invalid payment proof', admin_action.description)
    
    def test_approve_cash_transfer_payment_invalid_id(self):
        """Test approving a payment with invalid ID"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('dashboard-approve-cash-transfer-payment')
        data = {
            'payment_id': 'invalid-uuid',
            'action': 'approve'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_approve_cash_transfer_payment_not_found(self):
        """Test approving a payment that doesn't exist"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('dashboard-approve-cash-transfer-payment')
        data = {
            'payment_id': '00000000-0000-0000-0000-000000000000',
            'action': 'approve'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'Payment not found or not eligible for approval')
    
    def test_approve_cash_transfer_payment_already_processed(self):
        """Test approving a payment that's already been processed"""
        # First approve the payment
        self.cash_payment.status = 'paid'
        self.cash_payment.paid_at = timezone.now()
        self.cash_payment.save()
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('dashboard-approve-cash-transfer-payment')
        data = {
            'payment_id': str(self.cash_payment.id),
            'action': 'approve'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'Payment not found or not eligible for approval')
    
    def test_pending_cash_transfer_payments_filtering(self):
        """Test that only payments with correct statuses and methods are returned"""
        # Create a booking with status 'solicitud' (should not appear)
        solicitud_booking = Booking.objects.create(
            user=self.regular_user,
            venue=self.venue,
            package=self.package,
            start_datetime=timezone.now() + timedelta(days=14),
            end_datetime=timezone.now() + timedelta(days=14, hours=2),
            total_price=100.00,
            status='solicitud'
        )
        
        solicitud_payment_order = PaymentOrder.objects.create(
            booking=solicitud_booking,
            user=self.regular_user,
            amount_due=100.00
        )
        
        solicitud_payment = Payment.objects.create(
            order=solicitud_payment_order,
            user=self.regular_user,
            method='cash',
            amount=100.00,
            status='pending',
            payment_photo_base64='base64_encoded_photo_data'
        )
        
        # Create a card payment (should not appear)
        card_payment = Payment.objects.create(
            order=self.payment_order,
            user=self.regular_user,
            method='card',
            amount=100.00,
            status='pending',
            payment_photo_base64='base64_encoded_photo_data'
        )
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('dashboard-pending-cash-transfer-payments')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # Should still only show 2 payments (the original cash and transfer)
        self.assertEqual(data['total_pending'], 2)
        
        payment_ids = [p['payment_id'] for p in data['payments']]
        self.assertIn(str(self.cash_payment.id), payment_ids)
        self.assertIn(str(self.transfer_payment.id), payment_ids)
        self.assertNotIn(str(solicitud_payment.id), payment_ids)
        self.assertNotIn(str(card_payment.id), payment_ids)


class DailyCardsTestCase(APITestCase):
    def setUp(self):
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        
        # Create venue
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='Test Address'
        )
        
        # Create package
        self.package = Package.objects.create(
            title='Test Package',
            price=100.00,
            n_people=30,
            description='Test description',
            hours='2 hours'
        )
        
        # Create a specific date for testing (Monday, January 15, 2024)
        self.test_date = datetime(2024, 1, 15).date()  # This is a Monday
        
        # Create bookings for different days of the week
        for i in range(7):
            booking_date = self.test_date + timedelta(days=i)
            booking = Booking.objects.create(
                user=self.regular_user,
                venue=self.venue,
                package=self.package,
                start_datetime=datetime.combine(booking_date, datetime.min.time()),
                end_datetime=datetime.combine(booking_date, datetime.min.time()) + timedelta(hours=2),
                total_price=100.00,
                status='aceptacion'
            )
        
        self.client = APIClient()
    
    def test_daily_cards_without_date(self):
        """Test daily cards endpoint without date parameter (defaults to today)"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('dashboard-daily-cards')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # Check response structure
        self.assertIn('week_start', data)
        self.assertIn('week_end', data)
        self.assertIn('target_date', data)
        self.assertIn('daily_cards', data)
        
        # Should return 7 days
        self.assertEqual(len(data['daily_cards']), 7)
        
        # Check that days are in correct order (Monday to Sunday)
        spanish_days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        for i, day_card in enumerate(data['daily_cards']):
            self.assertEqual(day_card['day_name'], spanish_days[i])
            self.assertIn('bookings', day_card)
    
    def test_daily_cards_with_date(self):
        """Test daily cards endpoint with specific date parameter"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('dashboard-daily-cards')
        response = self.client.get(url, {'date': '2024-01-15'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # Check that the week starts on Monday (2024-01-15 is a Monday)
        self.assertEqual(data['week_start'], '2024-01-15')
        self.assertEqual(data['week_end'], '2024-01-21')
        self.assertEqual(data['target_date'], '2024-01-15')
        
        # Should return 7 days
        self.assertEqual(len(data['daily_cards']), 7)
        
        # Check that the first day is Monday
        self.assertEqual(data['daily_cards'][0]['day_name'], 'Lunes')
        self.assertEqual(data['daily_cards'][0]['date'], '2024-01-15')
    
    def test_daily_cards_with_date_in_middle_of_week(self):
        """Test daily cards endpoint with date in middle of week"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('dashboard-daily-cards')
        response = self.client.get(url, {'date': '2024-01-17'})  # Wednesday
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # Should still return the week starting from Monday
        self.assertEqual(data['week_start'], '2024-01-15')
        self.assertEqual(data['week_end'], '2024-01-21')
        self.assertEqual(data['target_date'], '2024-01-17')
        
        # Wednesday should be the third day (index 2)
        self.assertEqual(data['daily_cards'][2]['day_name'], 'Miércoles')
        self.assertEqual(data['daily_cards'][2]['date'], '2024-01-17')
    
    def test_daily_cards_invalid_date_format(self):
        """Test daily cards endpoint with invalid date format"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('dashboard-daily-cards')
        response = self.client.get(url, {'date': 'invalid-date'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid date format. Use YYYY-MM-DD format.')
    
    def test_daily_cards_unauthorized(self):
        """Test that non-admin users cannot access the endpoint"""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('dashboard-daily-cards')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_daily_cards_week_boundaries(self):
        """Test that week boundaries are calculated correctly"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Test with a date that's a Sunday
        url = reverse('dashboard-daily-cards')
        response = self.client.get(url, {'date': '2024-01-21'})  # Sunday
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # Should return the week starting from Monday
        self.assertEqual(data['week_start'], '2024-01-15')
        self.assertEqual(data['week_end'], '2024-01-21')
        
        # Sunday should be the last day (index 6)
        self.assertEqual(data['daily_cards'][6]['day_name'], 'Domingo')
        self.assertEqual(data['daily_cards'][6]['date'], '2024-01-21')
