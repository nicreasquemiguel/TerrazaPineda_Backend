from django.contrib import admin
from .models import PaymentOrder, Payment, RefundRequest

# Register your models here.
@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking', 'user', 'amount_due', 'status', 'created_at', 'expires_at']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'booking__id', 'user__email']
    readonly_fields = ['id', 'created_at']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'user', 'method', 'amount', 'status', 'paid_at', 'created_at']
    list_filter = ['method', 'status', 'created_at']
    search_fields = ['id', 'order__id', 'user__email', 'transaction_id']
    readonly_fields = ['id', 'created_at']

@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'payment', 'reason', 'approved', 'reviewed_by', 'created_at', 'reviewed_at']
    list_filter = ['approved', 'created_at']
    search_fields = ['id', 'payment__id', 'reason']
    readonly_fields = ['id', 'created_at']
