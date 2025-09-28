import django_filters
from .models import PaymentOrder

class PaymentOrderFilter(django_filters.FilterSet):
    booking_id = django_filters.UUIDFilter(field_name='booking__id', lookup_expr='exact')

    class Meta:
        model = PaymentOrder
        fields = ['booking_id'] 