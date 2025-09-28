
from rest_framework import serializers
from .models import PaymentOrder, Payment, RefundRequest
from booking.models import Booking


class PaymentSerializer(serializers.ModelSerializer):
    payment_photo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = ['id', 'order', 'user', 'method', 'amount', 'status', 'transaction_id', 'paid_at', 'created_at', 'gateway', 'card_last4', 'payment_photo', 'payment_photo_base64', 'payment_photo_url']
        read_only_fields = ['id', 'created_at', 'paid_at']
    
    def get_payment_photo_url(self, obj):
        """Convert filename to URL or return base64 data"""
        if obj.payment_photo_base64:
            # Check if it's a filename (contains .png, .jpg, etc.)
            if any(ext in obj.payment_photo_base64.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                # It's a filename, construct the URL
                return f"/media/user_{obj.user.id}/{obj.payment_photo_base64}"
            else:
                # It's actual base64 data, return as is
                return obj.payment_photo_base64
        return None


class PaymentOrderSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)
    booking_detail = serializers.SerializerMethodField()

    class Meta:
        model = PaymentOrder
        fields = [
            "id", "booking", "user", "amount_due", "status",
            "external_session_id", "created_at", "expires_at",
            "payments", "booking_detail", "gateway"
        ]
        read_only_fields = ("status", "created_at", "external_session_id", "payments")

    def get_booking_detail(self, obj):
        return {
            "start_datetime": obj.booking.start_datetime,
            "end_datetime": obj.booking.end_datetime,
            "total_price": obj.booking.total_price,
            "status": obj.booking.status,
        }



class RefundRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundRequest
        fields = "__all__"
        read_only_fields = ("approved", "reviewed_by", "reviewed_at", "created_at")
