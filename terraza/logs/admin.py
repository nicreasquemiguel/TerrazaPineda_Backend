from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    ActivityLog, BookingLog, PaymentLog, UserActivityLog, 
    SystemLog, AuditLog
)

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'category', 'action', 'log_level', 'ip_address']
    list_filter = ['category', 'action', 'log_level', 'timestamp']
    search_fields = ['user__email', 'description', 'action']
    readonly_fields = ['timestamp', 'id']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'timestamp', 'user', 'ip_address', 'user_agent')
        }),
        ('Activity Details', {
            'fields': ('category', 'action', 'description', 'log_level')
        }),
        ('Related Object', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Additional Context', {
            'fields': ('metadata', 'session_id'),
            'classes': ('collapse',)
        }),
    )

@admin.register(BookingLog)
class BookingLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'booking_id', 'action', 'old_status', 'new_status']
    list_filter = ['action', 'old_status', 'new_status', 'timestamp']
    search_fields = ['user__email', 'booking_id', 'description']
    readonly_fields = ['timestamp', 'id']
    date_hierarchy = 'timestamp'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'payment_id', 'action', 'amount', 'method', 'gateway']
    list_filter = ['action', 'method', 'gateway', 'old_status', 'new_status', 'timestamp']
    search_fields = ['user__email', 'payment_id', 'order_id', 'description']
    readonly_fields = ['timestamp', 'id']
    date_hierarchy = 'timestamp'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'ip_address']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__email', 'description']
    readonly_fields = ['timestamp', 'id']
    date_hierarchy = 'timestamp'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'level', 'component', 'message_preview']
    list_filter = ['level', 'component', 'timestamp']
    search_fields = ['message', 'component']
    readonly_fields = ['timestamp', 'id']
    date_hierarchy = 'timestamp'
    
    def message_preview(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_preview.short_description = 'Message'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'timestamp', 'level', 'component')
        }),
        ('Message Details', {
            'fields': ('message', 'stack_trace')
        }),
        ('Additional Context', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'audit_type', 'table_name', 'record_id', 'field_name']
    list_filter = ['audit_type', 'table_name', 'timestamp']
    search_fields = ['user__email', 'description', 'table_name', 'record_id']
    readonly_fields = ['timestamp', 'id']
    date_hierarchy = 'timestamp'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'timestamp', 'user', 'audit_type', 'ip_address')
        }),
        ('Change Details', {
            'fields': ('table_name', 'record_id', 'field_name', 'old_value', 'new_value')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Additional Context', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )

# Custom admin site configuration
admin.site.site_header = "Terraza Admin"
admin.site.site_title = "Terraza Admin Portal"
admin.site.index_title = "Welcome to Terraza Administration"
