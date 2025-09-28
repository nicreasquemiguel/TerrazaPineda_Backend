import uuid
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils.timezone import now
from django.conf import settings
import stripe
import mercadopago

from booking.models import Booking
from .filters import PaymentOrderFilter
from .models import PaymentOrder, Payment, RefundRequest
from .serializers import PaymentOrderSerializer, PaymentSerializer, RefundRequestSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY
mercado = mercadopago.SDK("your_mercadopago_access_token")


class PaymentOrderViewSet(viewsets.ModelViewSet):
    queryset = PaymentOrder.objects.all()
    serializer_class = PaymentOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = PaymentOrderFilter

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        booking = serializer.validated_data["booking"]
        serializer.save(user=self.request.user, amount_due=booking.total_price)

    @action(detail=True, methods=["post"])
    def confirm_payment(self, request, pk=None):
        """Simulate webhook confirming a payment (for dev)"""
        order = self.get_object()
        payment_data = {
            "order": order.id,
            "user": request.user.id,
            "amount": order.amount_due,
            "method": request.data.get("method", "card"),
            "status": "paid",
            "transaction_id": request.data.get("transaction_id", "MOCK123"),
            "paid_at": now()
        }
        serializer = PaymentSerializer(data=payment_data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        order.status = "paid"
        order.save()
        return Response({
            "message": "Payment confirmed",
            "payment": PaymentSerializer(payment).data
        })

    @action(detail=False, methods=["post"])
    def create_and_initiate(self, request):
        """Create order and initiate payment in one step, reusing order if exists"""
        booking_id = request.data.get('booking_id')
        amount = request.data.get('amount')
        gateway = request.data.get('gateway', 'stripe')  # default to stripe
        print(f"DEBUG: Received gateway: '{gateway}' (type: {type(gateway)})")
        print(f"DEBUG: Amount: {amount}")
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=404)

        # Only one PaymentOrder per booking and user
        order = PaymentOrder.objects.filter(
            booking=booking,
            user=request.user
        ).first()
        print(order)
        if not order:
            order = PaymentOrder.objects.create(
                booking=booking,
                user=request.user,
                amount_due=booking.total_price,  # Set initial amount_due
                gateway=gateway,
                status="pending"
            )
        else:
            # Optionally update amount_due or gateway if needed
            # if amount and order.amount_due != amount:
            #     order.amount -= amount
  
            if gateway and order.gateway != gateway:
                order.gateway = gateway
            order.save()

        # Handle different payment gateways
        if gateway == "stripe":
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "ars",
                        "product_data": {
                            "name": f"Reserva en {booking.venue.name}",
                            "description": f"Paquete: {booking.package.name}",
                        },
                        "unit_amount": int(float(order.amount_due) * 100),
                    },
                    "quantity": 1,
                }],
                metadata={"order_id": str(order.id)},
                payment_intent_data={
                    "metadata": {
                        "order_id": str(order.id),
                        "booking_id": str(booking.id),
                        "user_id": str(request.user.id),
                        "gateway": str(gateway)
                    }
                },
                success_url=f"http://localhost:3000/detalle-reserva/{booking.id}",
                cancel_url=f"http://localhost:3000/detalle-reserva/{booking.id}",
            )
            order.external_session_id = session.id
            order.payment_url = session.url
            order.save()
            return Response({"payment_url": session.url, "order_id": order.id})

        elif gateway == "mercadopago":
            # TODO: Implement MercadoPago checkout
            return Response({"error": "MercadoPago not yet implemented"}, status=400)

        elif gateway == "transfer":       
            print(f"DEBUG: Entering transfer gateway logic")
            # For transfers, allow multiple pending payments until manually verified
            # Don't check order.status since we want to allow multiple pending transfers
            
            print(f"DEBUG: Creating transfer payment")
            payment_data = {
                "order": order,
                "user": order.user,
                "amount": amount,
                "method": "transfer",
                "status": "pending",  # Transfer payments start as pending
                "gateway": gateway,
                "transaction_id": uuid.uuid4(),
                "paid_at": None  # No paid_at for pending payments
            }
            
            # Add payment photo if provided
            if "payment_photo_base64" in request.data:
                payment_data["payment_photo_base64"] = request.data["payment_photo_base64"]
                print(f"DEBUG: Added payment photo to payment data")
            
            print(f"DEBUG: Creating payment with data: {payment_data}")
            payment = Payment.objects.create(**payment_data)
            order.save()
            print(f"DEBUG: Payment created successfully: {payment.id}")
            return Response({
                "message": "Se mando correctamente el pago a revision",
                "payment_id": payment.id,
                "order_id": order.id
            })
        
        return Response({"error": f"Unsupported gateway: {gateway}"}, status=400)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()

        if order.status in ["cancelled", "expired"]:
            return Response({"error": "Order already cancelled."}, status=400)

        # Save reason on Booking (optional)
        reason = request.data.get("reason", "No reason provided")
        booking = order.booking
        booking.cancellation_reason = reason
        booking.cancelled_at = now()
        booking.save()

        # Check for payment
        payment = order.payments.filter(status="paid").first()
        if payment:
            if RefundRequest.objects.filter(payment=payment).exists():
                return Response({"error": "Refund already requested."}, status=400)

            refund = RefundRequest.objects.create(payment=payment, reason=reason)
            order.status = "cancelled"
            order.save()
            return Response({
                "message": "Refund requested.",
                "refund": RefundRequestSerializer(refund).data
            })
        else:
            order.status = "cancelled"
            order.save()
            return Response({"message": "Order cancelled."})
        
        
        
class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)
    
    

class RefundRequestViewSet(viewsets.ModelViewSet):
    queryset = RefundRequest.objects.all()
    serializer_class = RefundRequestSerializer
    permission_classes = [permissions.IsAdminUser]  # or custom permission

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        refund = self.get_object()
        if refund.approved is not None:
            return Response({"error": "Already reviewed"}, status=400)

        refund.approved = True
        refund.reviewed_by = request.user
        refund.reviewed_at = now()
        refund.save()

        # (Optional) refund the payment in Stripe or MercadoPago here

        return Response({"message": "Refund approved"})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        refund = self.get_object()
        if refund.approved is not None:
            return Response({"error": "Already reviewed"}, status=400)

        refund.approved = False
        refund.reviewed_by = request.user
        refund.reviewed_at = now()
        refund.save()

        return Response({"message": "Refund rejected"})