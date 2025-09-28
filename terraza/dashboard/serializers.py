from rest_framework import serializers
from .models import DashboardStats, AdminAction
from booking.models import Booking
from store.models import PaymentOrder, Payment

class DashboardStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardStats
        fields = '__all__'

class AdminActionSerializer(serializers.ModelSerializer):
    admin_user_email = serializers.CharField(source='admin_user.email', read_only=True)
    
    class Meta:
        model = AdminAction
        fields = ['id', 'admin_user', 'admin_user_email', 'action', 'target_id', 'description', 'created_at']
        read_only_fields = ['admin_user', 'created_at']

class PaymentApprovalSerializer(serializers.Serializer):
    """Serializer for payment approval/rejection"""
    payment_id = serializers.UUIDField()
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    reason = serializers.CharField(required=False, allow_blank=True)

class PendingCashTransferPaymentSerializer(serializers.Serializer):
    """Serializer for pending cash/transfer payments"""
    payment_id = serializers.UUIDField(source='id')
    booking_id = serializers.UUIDField(source='order.booking.id')
    booking_date = serializers.DateTimeField(source='order.booking.start_datetime')
    booking_status = serializers.CharField(source='order.booking.status')
    payment_status = serializers.CharField(source='status')
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_photo_base64 = serializers.CharField()
    created_at = serializers.DateTimeField()
    user_name = serializers.SerializerMethodField()
    amount_due = serializers.DecimalField(source='order.amount_due', max_digits=10, decimal_places=2)
    
    def get_user_name(self, obj):
        user = obj.user
        first_name = user.first_name or ''
        last_name = user.last_name or ''
        return f"{first_name} {last_name}".strip() or user.email

class DashboardOverviewSerializer(serializers.Serializer):
    """Serializer for dashboard overview statistics"""
    # Current month metrics
    current_month = serializers.DictField()
    # Last month metrics  
    last_month = serializers.DictField()
    # Percentage changes
    percentage_changes = serializers.DictField()
    # Overall statistics
    total_bookings = serializers.IntegerField()
    active_users = serializers.IntegerField()

class DailyCardsSerializer(serializers.Serializer):
    """Serializer for daily cards response"""
    week_start = serializers.CharField()
    week_end = serializers.CharField()
    target_date = serializers.CharField()
    daily_cards = serializers.ListField() 