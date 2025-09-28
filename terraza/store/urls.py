from rest_framework.routers import DefaultRouter
from .views import PaymentOrderViewSet, PaymentViewSet, RefundRequestViewSet

from django.urls import path
from .webhooks import stripe_webhook_view, mercadopago_webhook_view

router = DefaultRouter()
router.register("orders", PaymentOrderViewSet, basename="payment-order")
router.register("payments", PaymentViewSet, basename="payment")
router.register("refunds", RefundRequestViewSet, basename="refunds")


urlpatterns = [
    path('webhooks/stripe/', stripe_webhook_view, name='stripe-webhook'),
# path("webhooks/mercadopago/", mercadopago_webhook_view, name="mercadopago-webhook"),
]


urlpatterns += router.urls
