# booking/filters.py
from django_filters import rest_framework as filters
from .models import Booking

class BookingFilter(filters.FilterSet):
    start_from = filters.DateTimeFilter(field_name='start_datetime', lookup_expr='gte')
    start_to = filters.DateTimeFilter(field_name='start_datetime', lookup_expr='lte')
    end_from = filters.DateTimeFilter(field_name='end_datetime', lookup_expr='gte')
    end_to = filters.DateTimeFilter(field_name='end_datetime', lookup_expr='lte')

    class Meta:
        model = Booking
        fields = ['status', 'venue', 'package']
