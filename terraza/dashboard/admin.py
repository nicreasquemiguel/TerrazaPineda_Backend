from django.contrib import admin
from .models import DashboardStats, AdminAction

@admin.register(DashboardStats)
class DashboardStatsAdmin(admin.ModelAdmin):
    list_display = ['stat_type', 'date', 'total_bookings', 'total_revenue', 'pending_payments', 'completed_payments', 'cancelled_bookings', 'active_users']
    list_filter = ['stat_type', 'date']
    search_fields = ['stat_type', 'date']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-date', '-stat_type']

@admin.register(AdminAction)
class AdminActionAdmin(admin.ModelAdmin):
    list_display = ['admin_user', 'action', 'target_id', 'description', 'created_at']
    list_filter = ['action', 'created_at', 'admin_user']
    search_fields = ['admin_user__email', 'action', 'description', 'target_id']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
