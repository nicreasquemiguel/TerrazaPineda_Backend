import uuid
from django.conf import settings
from django.db import models

# Create your models here.
class PaymentOrder(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey("booking.Booking", on_delete=models.CASCADE, related_name="payment_orders")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    external_session_id = models.CharField(max_length=255, blank=True, null=True)  # Stripe session ID or similar
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    gateway = models.CharField(max_length=64, blank=True, null=True)
    
    def __str__(self):
        return f"Order #{self.id} for Booking {self.booking_id}"
    
    @property
    def calculated_amount_due(self):
        """Calculate amount due based on total price minus paid payments"""
        if not hasattr(self, 'booking') or not self.booking:
            return 0
            
        total_paid = sum(
            payment.amount 
            for payment in self.payments.filter(status='paid')
        )
        return max(0, self.booking.total_price - total_paid)
    
    def save(self, *args, **kwargs):
        # Only calculate amount_due if this is an update (not a new object)
        if self.pk:
            self.amount_due = self.calculated_amount_due
        
        # Update status logic based on amount_due
        if self.amount_due and self.amount_due <= 0:
            self.status = "paid"
        elif self.status == "paid" and self.amount_due and self.amount_due > 0:
            # If status was paid but there's still amount due, revert to pending
            self.status = "pending"
            
        super().save(*args, **kwargs)


    
    
class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(PaymentOrder, related_name="payments", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    method = models.CharField(max_length=20, choices=[('card', 'Card'), ('paypal', 'PayPal'), ('cash', 'Cash'), ('transfer', 'Transfer')])
    gateway = models.CharField(max_length=32,blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed')], default='pending')
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    card_last4 = models.CharField(max_length=4, blank=True, null=True)
    payment_photo = models.ImageField(upload_to='payment_photos/', blank=True, null=True)
    payment_photo_base64 = models.TextField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - ${self.amount} ({self.status})"
    
    
class RefundRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField(Payment, related_name="refund_request", on_delete=models.CASCADE)
    reason = models.TextField()
    approved = models.BooleanField(null=True)  # None = pending
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"RefundRequest for {self.payment}"
