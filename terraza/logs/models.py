import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

User = get_user_model()

class ActivityLog(models.Model):
    """Main activity log model for tracking all system activities"""
    
    LOG_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    CATEGORIES = [
        ('booking', 'Booking'),
        ('payment', 'Payment'),
        ('user', 'User'),
        ('admin', 'Admin'),
        ('system', 'System'),
        ('venue', 'Venue'),
        ('package', 'Package'),
        ('notification', 'Notification'),
        ('review', 'Review'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Activity details
    category = models.CharField(max_length=20, choices=CATEGORIES, db_index=True)
    action = models.CharField(max_length=100, db_index=True)
    description = models.TextField()
    log_level = models.CharField(max_length=10, choices=LOG_LEVELS, default='info')
    
    # Related object tracking
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional context
    metadata = models.JSONField(default=dict, blank=True)
    session_id = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'category']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['category', 'action']),
            models.Index(fields=['log_level', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action} ({self.category})"

class BookingLog(models.Model):
    """Specific logging for booking-related activities"""
    
    BOOKING_ACTIONS = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('status_changed', 'Status Changed'),
        ('cancelled', 'Cancelled'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('payment_received', 'Payment Received'),
        ('reminder_sent', 'Reminder Sent'),
        ('review_requested', 'Review Requested'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    booking_id = models.UUIDField(db_index=True)
    action = models.CharField(max_length=20, choices=BOOKING_ACTIONS)
    old_status = models.CharField(max_length=50, blank=True)
    new_status = models.CharField(max_length=50, blank=True)
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['booking_id', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        return f"Booking {self.booking_id} - {self.action} at {self.timestamp}"

class PaymentLog(models.Model):
    """Specific logging for payment-related activities"""
    
    PAYMENT_ACTIONS = [
        ('initiated', 'Initiated'),
        ('attempted', 'Attempted'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
        ('disputed', 'Disputed'),
        ('admin_approved', 'Admin Approved'),
        ('admin_rejected', 'Admin Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    payment_id = models.UUIDField(db_index=True)
    order_id = models.UUIDField(db_index=True)
    action = models.CharField(max_length=20, choices=PAYMENT_ACTIONS)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    method = models.CharField(max_length=20, blank=True)
    gateway = models.CharField(max_length=32, blank=True)
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    description = models.TextField()
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['payment_id', 'timestamp']),
            models.Index(fields=['order_id', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        return f"Payment {self.payment_id} - {self.action} at {self.timestamp}"

class UserActivityLog(models.Model):
    """Specific logging for user-related activities"""
    
    USER_ACTIONS = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('profile_updated', 'Profile Updated'),
        ('password_changed', 'Password Changed'),
        ('password_reset', 'Password Reset'),
        ('email_verified', 'Email Verified'),
        ('account_created', 'Account Created'),
        ('account_deactivated', 'Account Deactivated'),
        ('permissions_changed', 'Permissions Changed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=USER_ACTIONS)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"

class SystemLog(models.Model):
    """System-level logging for errors, warnings, and important events"""
    
    SYSTEM_LEVELS = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, choices=SYSTEM_LEVELS, default='info')
    component = models.CharField(max_length=50, db_index=True)
    message = models.TextField()
    stack_trace = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['level', 'timestamp']),
            models.Index(fields=['component', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.level} - {self.component}: {self.message}"

class AuditLog(models.Model):
    """Audit trail for sensitive operations and data changes"""
    
    AUDIT_TYPES = [
        ('data_change', 'Data Change'),
        ('permission_change', 'Permission Change'),
        ('configuration_change', 'Configuration Change'),
        ('security_event', 'Security Event'),
        ('compliance_check', 'Compliance Check'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    audit_type = models.CharField(max_length=20, choices=AUDIT_TYPES)
    table_name = models.CharField(max_length=100, blank=True)
    record_id = models.CharField(max_length=100, blank=True)
    field_name = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['audit_type', 'timestamp']),
            models.Index(fields=['table_name', 'record_id']),
            models.Index(fields=['user', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.audit_type} - {self.description}"
