from rest_framework import serializers
from .models import (
    ActivityLog, BookingLog, PaymentLog, UserActivityLog, 
    SystemLog, AuditLog
)

class ActivityLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            'id', 'timestamp', 'user', 'user_email', 'user_name', 'ip_address', 'user_agent',
            'category', 'action', 'description', 'log_level', 'content_type', 'content_type_name',
            'object_id', 'metadata', 'session_id'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_user_name(self, obj):
        if obj.user:
            first_name = obj.user.first_name or ''
            last_name = obj.user.last_name or ''
            return f"{first_name} {last_name}".strip() or obj.user.email
        return 'System'

class BookingLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = BookingLog
        fields = [
            'id', 'timestamp', 'user', 'user_email', 'user_name', 'booking_id',
            'action', 'old_status', 'new_status', 'description', 'metadata'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_user_name(self, obj):
        if obj.user:
            first_name = obj.user.first_name or ''
            last_name = obj.user.last_name or ''
            return f"{first_name} {last_name}".strip() or obj.user.email
        return 'System'

class PaymentLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentLog
        fields = [
            'id', 'timestamp', 'user', 'user_email', 'user_name', 'payment_id', 'order_id',
            'action', 'amount', 'method', 'gateway', 'old_status', 'new_status',
            'description', 'error_message', 'metadata'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_user_name(self, obj):
        if obj.user:
            first_name = obj.user.first_name or ''
            last_name = obj.user.last_name or ''
            return f"{first_name} {last_name}".strip() or obj.user.email
        return 'System'

class UserActivityLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserActivityLog
        fields = [
            'id', 'timestamp', 'user', 'user_email', 'user_name', 'action',
            'description', 'ip_address', 'user_agent', 'metadata'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_user_name(self, obj):
        if obj.user:
            first_name = obj.user.first_name or ''
            last_name = obj.user.last_name or ''
            return f"{first_name} {last_name}".strip() or obj.user.email
        return 'System'

class SystemLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemLog
        fields = [
            'id', 'timestamp', 'level', 'component', 'message', 'stack_trace', 'metadata'
        ]
        read_only_fields = ['id', 'timestamp']

class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'timestamp', 'user', 'user_email', 'user_name', 'audit_type',
            'table_name', 'record_id', 'field_name', 'old_value', 'new_value',
            'description', 'ip_address', 'metadata'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_user_name(self, obj):
        if obj.user:
            first_name = obj.user.first_name or ''
            last_name = obj.user.last_name or ''
            return f"{first_name} {last_name}".strip() or obj.user.email
        return 'System'

# Summary serializers for dashboard
class LogSummarySerializer(serializers.Serializer):
    """Serializer for log summary statistics"""
    period_days = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    total_activities = serializers.IntegerField()
    by_category = serializers.DictField()
    by_level = serializers.DictField()
    top_actions = serializers.DictField()

class PaymentLogSummarySerializer(serializers.Serializer):
    """Serializer for payment log summary"""
    period_days = serializers.IntegerField()
    total_payments = serializers.IntegerField()
    successful_payments = serializers.IntegerField()
    failed_payments = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    success_rate = serializers.FloatField()
    by_method = serializers.DictField()
    by_gateway = serializers.DictField()
