from rest_framework.routers import SimpleRouter
from .views import PaymentOrderViewSet, PaymentViewSet, RefundRequestViewSet

from django.urls import path
from .webhooks import stripe_webhook_view, mercadopago_webhook_view

router = SimpleRouter()
router.register("orders", PaymentOrderViewSet, basename="payment-order")
router.register("payments", PaymentViewSet, basename="payment")
router.register("refunds", RefundRequestViewSet, basename="refunds")


urlpatterns = [
    path('webhooks/stripe/', stripe_webhook_view, name='stripe-webhook'),
# path("webhooks/mercadopago/", mercadopago_webhook_view, name="mercadopago-webhook"),
]


urlpatterns += router.urls
