import uuid
from decimal import Decimal, ROUND_HALF_UP, ROUND_UP
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
from logs.utils import log_payment_activity, log_booking_activity

stripe.api_key = settings.STRIPE_SECRET_KEY
mercado = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)


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
            "amount": order.calculated_amount_due,
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
            # Observed actual rate from Stripe dashboard: 4.1% + $3.00 (before IVA 16%)
            # Stripe also charges IVA on its fee, so total deduction = (charge * rate + fixed) * 1.16
            # Gross-up: charge = (booking_amount + fixed * IVA) / (1 - rate * IVA)
            STRIPE_RATE = Decimal("0.041")
            STRIPE_FIXED = Decimal("3.00")
            STRIPE_IVA = Decimal("1.16")

            booking_amount = Decimal(str(amount)) if amount else Decimal(str(order.calculated_amount_due))
            charge_amount = ((booking_amount + STRIPE_FIXED * STRIPE_IVA) / (1 - STRIPE_RATE * STRIPE_IVA)).quantize(Decimal("0.01"), rounding=ROUND_UP)
            commission = charge_amount - booking_amount

            success_url = f"{settings.SITE_URL_FRONTEND}/detalle-reserva/{booking.id}?session_id={{CHECKOUT_SESSION_ID}}"
            cancel_url = f"{settings.SITE_URL_FRONTEND}/detalle-reserva/{booking.id}"
            print(f"DEBUG: Stripe success_url={repr(success_url)}")
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="payment",
                line_items=[
                    {
                        "price_data": {
                            "currency": "mxn",
                            "product_data": {
                                "name": f"Reserva en {booking.venue.name}",
                                "description": f"Paquete: {booking.package.title}",
                            },
                            "unit_amount": int(booking_amount * 100),
                        },
                        "quantity": 1,
                    },
                    {
                        "price_data": {
                            "currency": "mxn",
                            "product_data": {
                                "name": "Comisión de procesamiento",
                                "description": "Stripe 3.6% + $3.00 MXN",
                            },
                            "unit_amount": int(commission * 100),
                        },
                        "quantity": 1,
                    },
                ],
                metadata={"order_id": str(order.id)},
                payment_intent_data={
                    "metadata": {
                        "order_id": str(order.id),
                        "booking_id": str(booking.id),
                        "user_id": str(request.user.id),
                        "gateway": str(gateway),
                        "booking_amount": str(booking_amount),
                    }
                },
                success_url=success_url,
                cancel_url=cancel_url,
            )
            order.external_session_id = session.id
            order.payment_url = session.url
            order.save()
            return Response({"payment_url": session.url, "order_id": order.id, "commission": str(commission), "charge_amount": str(charge_amount)})

        elif gateway == "mercadopago":
            MP_IVA = Decimal("1.16")
            MP_FIXED = Decimal("4.00")
            MP_RATES = {
                "card_instant": Decimal("0.0349"),
                "card_14":      Decimal("0.0319"),
                "card_30":      Decimal("0.0295"),
                "cash":         Decimal("0.0379"),
            }
            mp_release_time = request.data.get("mp_release_time", "instant")  # instant | 14 | 30
            mp_payment_type = request.data.get("mp_payment_type", "card")     # card | cash

            rate_key = "cash" if mp_payment_type == "cash" else f"card_{mp_release_time}"
            rate = MP_RATES.get(rate_key, MP_RATES["card_instant"])

            booking_amount = Decimal(str(amount)) if amount else Decimal(str(order.calculated_amount_due))
            # Gross-up: charge = (booking_amount + fixed×IVA) / (1 − rate×IVA)
            effective_rate = rate * MP_IVA
            effective_fixed = MP_FIXED * MP_IVA
            charge_amount = ((booking_amount + effective_fixed) / (1 - effective_rate)).quantize(Decimal("0.01"), rounding=ROUND_UP)
            commission = charge_amount - booking_amount

            preference_data = {
                "items": [
                    {
                        "title": f"Reserva en {booking.venue.name} - {booking.package.title}",
                        "quantity": 1,
                        "currency_id": "MXN",
                        "unit_price": float(booking_amount),
                    },
                    {
                        "title": "Comisión MercadoPago",
                        "description": f"{float(rate * 100):.2f}% + $4.00 + IVA",
                        "quantity": 1,
                        "currency_id": "MXN",
                        "unit_price": float(commission),
                    },
                ],
                "metadata": {"booking_amount": str(booking_amount)},
                "external_reference": str(order.id),
                "back_urls": {
                    "success": f"{settings.SITE_URL_FRONTEND}/detalle-reserva/{booking.id}",
                    "failure": f"{settings.SITE_URL_FRONTEND}/detalle-reserva/{booking.id}",
                    "pending": f"{settings.SITE_URL_FRONTEND}/detalle-reserva/{booking.id}",
                },
                "auto_return": "approved",
                "notification_url": f"{settings.SITE_URL}/api/store/webhooks/mercadopago/",
            }
            preference_response = mercado.preference().create(preference_data)
            preference = preference_response["response"]
            if preference_response["status"] not in (200, 201):
                return Response({"error": "MercadoPago preference creation failed", "detail": preference}, status=502)
            order.external_session_id = preference["id"]
            is_test = getattr(settings, "MERCADO_PAGO_TEST_MODE", False) or settings.MERCADO_PAGO_ACCESS_TOKEN.startswith("TEST-")
            checkout_url = preference.get("sandbox_init_point" if is_test else "init_point", "")
            order.payment_url = checkout_url
            order.save()
            return Response({
                "preference_id": preference["id"],
                "payment_url": checkout_url,
                "order_id": order.id,
                "commission": str(commission),
                "charge_amount": str(charge_amount),
            })

        elif gateway == "transfer":
            if not amount or float(amount) <= 0:
                return Response({"error": "amount is required and must be greater than 0 for transfer payments"}, status=400)

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

    @action(detail=False, methods=["post"], url_path='register_cash_payment')
    def register_cash_payment(self, request):
        """Staff-only: register a cash payment directly for a booking."""
        if not request.user.is_staff:
            return Response({'detail': 'No autorizado.'}, status=status.HTTP_403_FORBIDDEN)

        booking_id = request.data.get('booking_id')
        raw_amount = request.data.get('amount')

        if not booking_id or raw_amount is None:
            return Response({'detail': 'booking_id y amount son requeridos.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = float(raw_amount)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response({'detail': 'El monto debe ser mayor a 0.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({'detail': 'Reserva no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        order, _ = PaymentOrder.objects.get_or_create(
            booking=booking,
            user=booking.user,
            gateway='cash',
            defaults={'amount_due': booking.total_price, 'status': 'pending'}
        )

        payment = Payment.objects.create(
            order=order,
            user=request.user,
            method='cash',
            amount=amount,
            status='paid',
            transaction_id=f'CASH-{uuid.uuid4().hex[:8].upper()}',
            paid_at=now()
        )

        order.save()  # recalculates amount_due and updates status

        # Log the cash payment registration
        log_payment_activity(
            user=request.user,
            payment_id=payment.id,
            order_id=order.id,
            action='admin_approved',
            amount=amount,
            method='cash',
            gateway='cash',
            old_status='',
            new_status='paid',
            description=f'Staff {request.user.email} registró pago en efectivo de ${amount:,.2f} para reserva {booking_id}',
            metadata={
                'booking_id': str(booking_id),
                'staff_email': request.user.email,
                'transaction_id': payment.transaction_id,
            }
        )
        log_booking_activity(
            user=request.user,
            booking_id=booking.id,
            action='payment_received',
            old_status=booking.status,
            new_status=booking.status,
            description=f'Pago en efectivo de ${amount:,.2f} registrado por {request.user.email}',
            metadata={
                'payment_id': str(payment.id),
                'amount': amount,
                'method': 'cash',
                'staff_email': request.user.email,
            }
        )

        return Response({
            'message': 'Pago en efectivo registrado exitosamente.',
            'payment_id': str(payment.id),
            'order_id': str(order.id),
            'amount': amount,
            'order_status': order.status
        })

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