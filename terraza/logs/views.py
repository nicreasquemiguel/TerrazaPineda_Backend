from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta


class LogPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200

from .models import (
    ActivityLog, BookingLog, PaymentLog, UserActivityLog, 
    SystemLog, AuditLog
)
from .serializers import (
    ActivityLogSerializer, BookingLogSerializer, PaymentLogSerializer,
    UserActivityLogSerializer, SystemLogSerializer, AuditLogSerializer
)

class IsAdminUser(permissions.BasePermission):
    """Custom permission to only allow admin users"""
    def has_permission(self, request, view):
        return request.user and request.user.is_staff

class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing activity logs"""
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAdminUser]
    pagination_class = LogPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['category', 'action', 'log_level', 'user']
    ordering_fields = ['timestamp', 'category', 'action']
    ordering = ['-timestamp']
    search_fields = ['description', 'action', 'user__email']

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary statistics for activity logs"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        recent_logs = self.queryset.filter(timestamp__gte=start_date)

        total_activities = recent_logs.count()
        by_category = dict(
            recent_logs.values('category').annotate(count=Count('id')).values_list('category', 'count')
        )
        by_level = dict(
            recent_logs.values('log_level').annotate(count=Count('id')).values_list('log_level', 'count')
        )
        top_actions = dict(
            recent_logs.values('action').annotate(count=Count('id'))
            .order_by('-count').values_list('action', 'count')[:10]
        )

        return Response({
            'period_days': days,
            'start_date': start_date.date(),
            'end_date': timezone.now().date(),
            'total_activities': total_activities,
            'by_category': by_category,
            'by_level': by_level,
            'top_actions': top_actions,
        })
    
    @action(detail=False, methods=['get'])
    def recent_activity(self, request):
        """Get recent activity for dashboard"""
        limit = int(request.query_params.get('limit', 50))
        recent_logs = self.queryset.order_by('-timestamp')[:limit]
        serializer = self.get_serializer(recent_logs, many=True)
        return Response(serializer.data)

class BookingLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing booking logs"""
    queryset = BookingLog.objects.all()
    serializer_class = BookingLogSerializer
    permission_classes = [IsAdminUser]
    pagination_class = LogPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['action', 'old_status', 'new_status', 'user']
    ordering_fields = ['timestamp', 'action']
    ordering = ['-timestamp']
    search_fields = ['description', 'user__email']
    
    @action(detail=False, methods=['get'])
    def by_booking(self, request):
        """Get all logs for a specific booking"""
        booking_id = request.query_params.get('booking_id')
        if not booking_id:
            return Response(
                {'error': 'booking_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logs = self.queryset.filter(booking_id=booking_id).order_by('-timestamp')
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)

class PaymentLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing payment logs"""
    queryset = PaymentLog.objects.all()
    serializer_class = PaymentLogSerializer
    permission_classes = [IsAdminUser]
    pagination_class = LogPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['action', 'method', 'gateway', 'old_status', 'new_status', 'user']
    ordering_fields = ['timestamp', 'action', 'amount']
    ordering = ['-timestamp']
    search_fields = ['description', 'user__email', 'transaction_id']

    @action(detail=False, methods=['get'])
    def by_payment(self, request):
        """Get all logs for a specific payment"""
        payment_id = request.query_params.get('payment_id')
        if not payment_id:
            return Response(
                {'error': 'payment_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        logs = self.queryset.filter(payment_id=payment_id).order_by('-timestamp')
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def payment_summary(self, request):
        """Get payment activity summary"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        recent_logs = self.queryset.filter(timestamp__gte=start_date)

        total_payments = recent_logs.count()
        successful_payments = recent_logs.filter(new_status='paid').count()
        failed_payments = recent_logs.filter(new_status='failed').count()
        pending_payments = recent_logs.filter(new_status='pending').count()
        by_method = dict(
            recent_logs.exclude(method__isnull=True).exclude(method='')
            .values('method').annotate(count=Count('id')).values_list('method', 'count')
        )
        by_gateway = dict(
            recent_logs.exclude(gateway__isnull=True).exclude(gateway='')
            .values('gateway').annotate(count=Count('id')).values_list('gateway', 'count')
        )

        return Response({
            'period_days': days,
            'total_payments': total_payments,
            'successful_payments': successful_payments,
            'failed_payments': failed_payments,
            'pending_payments': pending_payments,
            'success_rate': (successful_payments / total_payments * 100) if total_payments > 0 else 0,
            'by_method': by_method,
            'by_gateway': by_gateway,
        })

class UserActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing user activity logs"""
    queryset = UserActivityLog.objects.all()
    serializer_class = UserActivityLogSerializer
    permission_classes = [IsAdminUser]
    pagination_class = LogPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['action', 'user']
    ordering_fields = ['timestamp', 'action']
    ordering = ['-timestamp']
    search_fields = ['description', 'user__email']
    
    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """Get all logs for a specific user"""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logs = self.queryset.filter(user_id=user_id).order_by('-timestamp')
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)

class SystemLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing system logs"""
    queryset = SystemLog.objects.all()
    serializer_class = SystemLogSerializer
    permission_classes = [IsAdminUser]
    pagination_class = LogPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['level', 'component']
    ordering_fields = ['timestamp', 'level', 'component']
    ordering = ['-timestamp']
    search_fields = ['message', 'component']
    
    @action(detail=False, methods=['get'])
    def errors(self, request):
        """Get only error and critical level logs"""
        error_logs = self.queryset.filter(level__in=['error', 'critical']).order_by('-timestamp')
        serializer = self.get_serializer(error_logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_component(self, request):
        """Get logs for a specific component"""
        component = request.query_params.get('component')
        if not component:
            return Response(
                {'error': 'component parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logs = self.queryset.filter(component=component).order_by('-timestamp')
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing audit logs"""
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
    pagination_class = LogPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['audit_type', 'table_name', 'user']
    ordering_fields = ['timestamp', 'audit_type', 'table_name']
    ordering = ['-timestamp']
    search_fields = ['description', 'table_name', 'record_id']
    
    @action(detail=False, methods=['get'])
    def data_changes(self, request):
        """Get only data change audit logs"""
        data_changes = self.queryset.filter(audit_type='data_change').order_by('-timestamp')
        serializer = self.get_serializer(data_changes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def security_events(self, request):
        """Get only security event audit logs"""
        security_events = self.queryset.filter(audit_type='security_event').order_by('-timestamp')
        serializer = self.get_serializer(security_events, many=True)
        return Response(serializer.data)
