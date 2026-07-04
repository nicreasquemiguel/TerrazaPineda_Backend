from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from .models import PaymentOrder, Payment
from django.utils.timezone import now
from django.conf import settings

STRIPE_SECRET_KEY = settings.STRIPE_SECRET_KEY
STRIPE_WEBHOOK_KEY = settings.STRIPE_WEBHOOK_KEY

stripe.api_key = STRIPE_SECRET_KEY


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook_view(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = STRIPE_WEBHOOK_KEY

    # print(payload) 
    # print("RAW payload:", request.body)
    # print("Decoded payload:", request.body.decode())
    # print("Stripe-Signature header:", request.META.get("HTTP_STRIPE_SIGNATURE"))
    # print("Webhook secret:", STRIPE_WEBHOOK_KEY)


    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        print("gooood")
        session = event["data"]["object"]
        order_id = session["metadata"].get("order_id")
        print(event)
        
        # Get amount_total from the session object
        amount_total = session.get("amount_total", 0)  # in cents
        amount_in_pesos = amount_total / 100  # convert from cents to pesos
        
        payment_intent_id = session.get("payment_intent")
        if payment_intent_id:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            booking_id = payment_intent.metadata.get("booking_id")
            user_id = payment_intent.metadata.get("user_id")
            gateway = payment_intent.metadata.get("gateway")
            print(gateway)
            print(order_id)
        
        order = PaymentOrder.objects.get(id=order_id)
        # Guard by transaction_id so duplicate webhook deliveries don't create duplicate payments
        # and partial-payment orders (status=pending) can still receive additional payments
        if not Payment.objects.filter(transaction_id=payment_intent_id).exists():
            Payment.objects.create(
                order=order,
                user=order.user,
                amount=amount_in_pesos,
                method="card",
                status="paid",
                gateway=gateway,
                transaction_id=payment_intent_id,
                paid_at=now()
            )
            # Signal handles updating booking.advance_paid, booking.status, and order.amount_due
            
            # if order.booking.advance_paid >= order.booking.total_price:
            #     order.status = "paid"
            
            # order.booking.save() 
            # order.save()
        # except PaymentOrder.DoesNotExist:
        #     pass

    return HttpResponse(status=200)


@csrf_exempt
def mercadopago_webhook_view(request):
    import mercadopago
    mercado = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

    topic = request.GET.get("topic") or request.GET.get("type")
    payment_id = request.GET.get("id") or request.GET.get("data.id")

    # Also handle JSON body format (newer webhook style)
    if not payment_id and request.content_type == "application/json":
        import json
        try:
            body = json.loads(request.body)
            topic = body.get("type", topic)
            payment_id = body.get("data", {}).get("id")
        except (ValueError, KeyError):
            pass

    if topic != "payment" or not payment_id:
        return JsonResponse({"received": True})

    try:
        mp_response = mercado.payment().get(payment_id)
        payment_data = mp_response.get("response", {})
        if mp_response.get("status") not in (200, 201):
            return JsonResponse({"received": True})

        if payment_data.get("status") != "approved":
            return JsonResponse({"received": True})

        external_reference = payment_data.get("external_reference")
        order = PaymentOrder.objects.get(id=external_reference)

        if not Payment.objects.filter(transaction_id=str(payment_id)).exists():
            amount = payment_data.get("transaction_amount", order.amount_due)
            Payment.objects.create(
                order=order,
                user=order.user,
                amount=amount,
                method="card",
                status="paid",
                gateway="mercadopago",
                transaction_id=str(payment_id),
                paid_at=now()
            )
    except PaymentOrder.DoesNotExist:
        pass
    except Exception:
        pass

    return JsonResponse({"received": True})
