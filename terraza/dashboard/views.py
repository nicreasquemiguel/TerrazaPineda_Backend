from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from decimal import Decimal

from .models import DashboardStats, AdminAction
from .serializers import (
    DashboardStatsSerializer, 
    AdminActionSerializer, 
    PaymentApprovalSerializer,
    DashboardOverviewSerializer,
    PendingCashTransferPaymentSerializer,
    DailyCardsSerializer
)
from booking.models import Booking
from store.models import PaymentOrder, Payment
from users.models import UserAccount as User

# Create your views here.

class DashboardViewSet(viewsets.ViewSet):
    """Dashboard endpoints for admins"""
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get dashboard overview statistics with month-over-month comparisons"""
        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = current_month_start - timedelta(days=1)
        
        # Current month statistics
        current_month_bookings = Booking.objects.filter(
            created_at__date__gte=current_month_start
        ).count()
        
        current_month_revenue = Payment.objects.filter(
            status='paid',
            paid_at__date__gte=current_month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        current_month_customers = User.objects.filter(
            date_joined__date__gte=current_month_start
        ).count()
        
        current_month_accepted = Booking.objects.filter(
            status='aceptacion',
            created_at__date__gte=current_month_start
        ).count()
        
        # Last month statistics
        last_month_bookings = Booking.objects.filter(
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end
        ).count()
        
        last_month_revenue = Payment.objects.filter(
            status='paid',
            paid_at__date__gte=last_month_start,
            paid_at__date__lte=last_month_end
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        last_month_customers = User.objects.filter(
            date_joined__date__gte=last_month_start,
            date_joined__date__lte=last_month_end
        ).count()
        
        last_month_accepted = Booking.objects.filter(
            status='aceptacion',
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end
        ).count()
        
        # Calculate percentage differences
        def calculate_percentage_change(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return round(((current - previous) / previous) * 100, 1)
        
        bookings_percentage = calculate_percentage_change(current_month_bookings, last_month_bookings)
        revenue_percentage = calculate_percentage_change(float(current_month_revenue), float(last_month_revenue))
        customers_percentage = calculate_percentage_change(current_month_customers, last_month_customers)
        accepted_percentage = calculate_percentage_change(current_month_accepted, last_month_accepted)
        
        # Overall statistics
        total_bookings = Booking.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        
        data = {
            # Current month metrics with comparisons
            'current_month': {
                'bookings': current_month_bookings,
                'revenue': current_month_revenue,
                'customers': current_month_customers,
                'accepted_bookings': current_month_accepted
            },
            'last_month': {
                'bookings': last_month_bookings,
                'revenue': last_month_revenue,
                'customers': last_month_customers,
                'accepted_bookings': last_month_accepted
            },
            'percentage_changes': {
                'bookings': bookings_percentage,
                'revenue': revenue_percentage,
                'customers': customers_percentage,
                'accepted_bookings': accepted_percentage
            },
            # Overall statistics
            'total_bookings': total_bookings,
            'active_users': active_users
        }
        
        serializer = DashboardOverviewSerializer(data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def daily_cards(self, request):
        """Get daily booking cards for a specific week"""
        # Get date parameter, default to today if not provided
        date_param = request.query_params.get('date')
        
        if date_param:
            try:
                # Parse the date parameter
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD format.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = timezone.now().date()
        
        # Generate 7 daily cards (Monday to Sunday) for the week containing the target date
        daily_cards = []
        spanish_days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        
        # Find the Monday of the week containing the target date
        days_since_monday = target_date.weekday()  # Monday is 0, Sunday is 6
        monday_date = target_date - timedelta(days=days_since_monday)
        
        for i in range(7):
            card_date = monday_date + timedelta(days=i)
            day_name = spanish_days[i]
            day_number = card_date.day
            
            # Get bookings for this specific day
            day_bookings = Booking.objects.filter(
                start_datetime__date=card_date,
                status__in=['aceptacion', 'solicitud', 'confirmacion', 'finalizado']
            ).select_related('user', 'package')
            
            # Create daily object with all booking data
            daily_object = {
                'day_name': day_name,
                'day_number': day_number,
                'date': card_date.strftime('%Y-%m-%d'),
                'bookings': []
            }
            
            # Add each booking's data directly to the daily object
            for booking in day_bookings:
                # Calculate amount due (total price minus advance paid)
                amount_due = booking.total_price - getattr(booking, 'advance_paid', 0)
                
                daily_object['bookings'].append({
                    'booking_id': str(booking.id),
                    'package_name': booking.package.title,
                    'people_count': getattr(booking.package, 'n_people', 0),
                    'client_first_name': booking.user.first_name or '',
                    'client_last_name': booking.user.last_name or '',
                    'client_phone': getattr(booking.user, 'phone', ''),
                    'status': booking.status,
                    'amount_due': float(amount_due)
                })
            
            daily_cards.append(daily_object)
        
        data = {
            'week_start': monday_date.strftime('%Y-%m-%d'),
            'week_end': (monday_date + timedelta(days=6)).strftime('%Y-%m-%d'),
            'target_date': target_date.strftime('%Y-%m-%d'),
            'daily_cards': daily_cards
        }
        
        serializer = DailyCardsSerializer(data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_payments(self, request):
        """Get all pending payments for admin review"""
        pending_payments = Payment.objects.filter(
            status='pending'
        ).select_related('order__booking', 'user').order_by('-created_at')
        
        payments_data = []
        for payment in pending_payments:
            payments_data.append({
                'id': payment.id,
                'amount': payment.amount,
                'method': payment.method,
                'gateway': payment.gateway,
                'user_email': payment.user.email,
                'booking_id': payment.order.booking.id,
                'payment_status': payment.status,
                'venue_name': payment.order.booking.venue.name,
                'created_at': payment.created_at,
            })
        
        return Response(payments_data)
    
    @action(detail=False, methods=['get'])
    def pending_cash_transfer_payments(self, request):
        """Get pending cash or transfer payments for bookings with specific statuses from now forward"""
        now = timezone.now()
        
        # Get pending cash/transfer payments for future bookings with specific statuses
        pending_payments = Payment.objects.filter(
            status='pending',
            method__in=['cash', 'transfer'],
            order__booking__start_datetime__gte=now,
            order__booking__status__in=['aceptacion', 'apartado', 'entregado']
        ).select_related(
            'order__booking__venue', 
            'order__booking__package', 
            'user'
        ).order_by('-created_at')
        
        serializer = PendingCashTransferPaymentSerializer(pending_payments, many=True)
        return Response({
            'total_pending': len(serializer.data),
            'payments': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def approve_payment(self, request):
        """Approve or reject a pending payment"""
        serializer = PaymentApprovalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        payment_id = serializer.validated_data['payment_id']
        action = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')
        
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if payment.status != 'pending':
            return Response({'error': 'Payment is not pending'}, status=status.HTTP_400_BAD_REQUEST)
        
        if action == 'approve':
            payment.status = 'paid'
            payment.paid_at = timezone.now()
            payment.save()
            
            # Log admin action
            AdminAction.objects.create(
                admin_user=request.user,
                action='payment_approved',
                target_id=str(payment.id),
                description=f'Payment approved: {payment.amount} for booking {payment.order.booking.id}'
            )
            
            return Response({'message': 'Payment approved successfully'})
        
        elif action == 'reject':
            payment.status = 'failed'
            payment.save()
            
            # Log admin action
            AdminAction.objects.create(
                admin_user=request.user,
                action='payment_rejected',
                target_id=str(payment.id),
                description=f'Payment rejected: {payment.amount} for booking {payment.order.booking.id}. Reason: {reason}'
            )
            
            return Response({'message': 'Payment rejected successfully'})
    
    @action(detail=False, methods=['post'])
    def approve_cash_transfer_payment(self, request):
        """Approve or reject a pending cash/transfer payment after photo review"""
        serializer = PaymentApprovalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        payment_id = serializer.validated_data['payment_id']
        action = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')
        
        try:
            payment = Payment.objects.get(
                id=payment_id,
                status='pending',
                method__in=['cash', 'transfer']
            )
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found or not eligible for approval'}, status=status.HTTP_404_NOT_FOUND)
        
        if action == 'approve':
            payment.status = 'paid'
            payment.paid_at = timezone.now()
            payment.save()
            
            # Log admin action
            AdminAction.objects.create(
                admin_user=request.user,
                action='cash_transfer_payment_approved',
                target_id=str(payment.id),
                description=f'Cash/Transfer payment approved: {payment.amount} for booking {payment.order.booking.id}'
            )
            
            return Response({
                'message': 'Payment approved successfully',
                'payment_id': str(payment.id),
                'amount': float(payment.amount),
                'method': payment.method,
                'booking_id': str(payment.order.booking.id)
            })
        
        elif action == 'reject':
            payment.status = 'failed'
            payment.save()
            
            # Log admin action
            AdminAction.objects.create(
                admin_user=request.user,
                action='cash_transfer_payment_rejected',
                target_id=str(payment.id),
                description=f'Cash/Transfer payment rejected: {payment.amount} for booking {payment.order.booking.id}. Reason: {reason}'
            )
            
            return Response({
                'message': 'Payment rejected successfully',
                'payment_id': str(payment.id),
                'amount': float(payment.amount),
                'method': payment.method,
                'booking_id': str(payment.order.booking.id),
                'rejection_reason': reason
            })
    
    @action(detail=False, methods=['post'])
    def approve_booking(self, request):
        """Approve a booking with status 'solicitud' by changing it to 'aceptacion'"""
        booking_id = request.data.get('booking_id')
        
        if not booking_id:
            return Response({'error': 'booking_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if booking.status != 'solicitud':
            return Response({
                'error': f'Booking status is {booking.status}, only "solicitud" bookings can be approved'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Change status to accepted
        old_status = booking.status
        booking.status = 'aceptacion'
        booking.save()
        
        # Log admin action
        AdminAction.objects.create(
            admin_user=request.user,
            action='booking_approved',
            target_id=str(booking.id),
            description=f'Booking approved: {old_status} → aceptacion for {booking.user.email}'
        )
        
        return Response({
            'message': 'Booking approved successfully',
            'booking_id': str(booking.id),
            'old_status': old_status,
            'new_status': 'aceptacion',
            'client_email': booking.user.email
        })
    
    @action(detail=False, methods=['post'])
    def reject_booking(self, request):
        """Reject a booking with status 'solicitud' by changing it to 'rechazado'"""
        booking_id = request.data.get('booking_id')
        reason = request.data.get('reason', 'No reason provided')
        
        if not booking_id:
            return Response({'error': 'booking_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if booking.status != 'solicitud':
            return Response({
                'error': f'Booking status is {booking.status}, only "solicitud" bookings can be rejected'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Change status to rejected
        old_status = booking.status
        booking.status = 'rechazado'
        booking.save()
        
        # Log admin action
        AdminAction.objects.create(
            admin_user=request.user,
            action='booking_rejected',
            target_id=str(booking.id),
            description=f'Booking rejected: {old_status} → rechazado for {booking.user.email}. Reason: {reason}'
        )
        
        return Response({
            'message': 'Booking rejected successfully',
            'booking_id': str(booking.id),
            'old_status': old_status,
            'new_status': 'rechazado',
            'client_email': booking.user.email,
            'rejection_reason': reason
        })
    
    @action(detail=False, methods=['get'])
    def revenue_chart(self, request):
        """Get revenue data for charts (last 30 days)"""
        today = timezone.now().date()
        dates = []
        revenue_data = []
        
        for i in range(30):
            date = today - timedelta(days=i)
            daily_revenue = Payment.objects.filter(
                status='paid',
                paid_at__date=date
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            dates.append(date.strftime('%Y-%m-%d'))
            revenue_data.append(float(daily_revenue))
        
        return Response({
            'dates': dates[::-1],  # Reverse to show oldest first
            'revenue': revenue_data[::-1]
        })
    
    @action(detail=False, methods=['get'])
    def admin_actions(self, request):
        """Get recent admin actions for audit"""
        actions = AdminAction.objects.select_related('admin_user').order_by('-created_at')[:50]
        serializer = AdminActionSerializer(actions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def solicitud_events(self, request):
        """Get all events with status 'solicitud' (reservation requests)"""
        solicitud_bookings = Booking.objects.filter(
            status='solicitud'
        ).select_related('user', 'package', 'venue').order_by('-created_at')
        
        events_data = []
        for booking in solicitud_bookings:
            events_data.append({
                'booking_id': str(booking.id),
                'created_at': booking.created_at,
                'status': booking.status,
                'client_name': f"{booking.user.first_name or ''} {booking.user.last_name or ''}".strip(),
                'client_email': booking.user.email,
                'description': booking.description,
                'package_name': booking.package.title,
                'people_count': booking.package.n_people,
                'venue_name': booking.venue.name,
                'total_price': float(booking.total_price),
                'start_datetime': booking.start_datetime,
                'end_datetime': booking.end_datetime
            })
        
        return Response({
            'total_requests': len(events_data),
            'events': events_data
        })

class DashboardStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for dashboard statistics"""
    queryset = DashboardStats.objects.all()
    serializer_class = DashboardStatsSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['post'])
    def generate_stats(self, request):
        """Generate and store dashboard statistics"""
        today = timezone.now().date()
        
        # Calculate daily stats
        daily_stats = DashboardStats.objects.filter(
            stat_type='daily',
            date=today
        ).first()
        
        if not daily_stats:
            daily_stats = DashboardStats(stat_type='daily', date=today)
        
        # Update statistics
        daily_stats.total_bookings = Booking.objects.count()
        daily_stats.total_revenue = Payment.objects.filter(status='paid').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        daily_stats.pending_payments = Payment.objects.filter(status='pending').count()
        daily_stats.completed_payments = Payment.objects.filter(status='paid').count()
        daily_stats.cancelled_bookings = Booking.objects.filter(status='cancelled').count()
        daily_stats.active_users = User.objects.filter(is_active=True).count()
        
        daily_stats.save()
        
        # Log admin action
        AdminAction.objects.create(
            admin_user=request.user,
            action='stats_generated',
            description=f'Generated daily statistics for {today}'
        )
        
        return Response({'message': 'Statistics generated successfully'})
