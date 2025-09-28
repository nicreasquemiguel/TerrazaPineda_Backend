from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class DashboardStats(models.Model):
    """Store calculated dashboard statistics"""
    STAT_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    stat_type = models.CharField(max_length=20, choices=STAT_TYPE_CHOICES)
    date = models.DateField()
    total_bookings = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_payments = models.IntegerField(default=0)
    completed_payments = models.IntegerField(default=0)
    cancelled_bookings = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['stat_type', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.stat_type} stats for {self.date}"

class AdminAction(models.Model):
    """Track admin actions for audit purposes"""
    ACTION_CHOICES = [
        ('payment_approved', 'Payment Approved'),
        ('payment_rejected', 'Payment Rejected'),
        ('booking_approved', 'Booking Approved'),
        ('booking_rejected', 'Booking Rejected'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('user_blocked', 'User Blocked'),
        ('stats_generated', 'Statistics Generated'),
    ]
    
    admin_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_actions')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_id = models.CharField(max_length=100, blank=True, null=True)  # ID of affected object
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.admin_user.email} - {self.action} at {self.created_at}"
