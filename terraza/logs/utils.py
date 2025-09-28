import json
import traceback
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db import transaction
from .models import (
    ActivityLog, BookingLog, PaymentLog, UserActivityLog, 
    SystemLog, AuditLog
)

def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_user_agent(request):
    """Extract user agent from request"""
    return request.META.get('HTTP_USER_AGENT', '')

def log_activity(
    user=None, 
    category='system', 
    action='', 
    description='', 
    log_level='info',
    content_object=None,
    metadata=None,
    request=None,
    session_id=None
):
    """Log a general activity"""
    try:
        with transaction.atomic():
            log_data = {
                'user': user,
                'category': category,
                'action': action,
                'description': description,
                'log_level': log_level,
                'metadata': metadata or {},
                'session_id': session_id or '',
            }
            
            if request:
                log_data['ip_address'] = get_client_ip(request)
                log_data['user_agent'] = get_user_agent(request)
            
            if content_object:
                log_data['content_type'] = ContentType.objects.get_for_model(content_object)
                log_data['object_id'] = content_object.id
            
            ActivityLog.objects.create(**log_data)
            
    except Exception as e:
        # Fallback to system log if activity logging fails
        log_system_error('ActivityLog', f"Failed to log activity: {str(e)}", str(e))

def log_booking_activity(
    user=None,
    booking_id=None,
    action='',
    old_status='',
    new_status='',
    description='',
    metadata=None
):
    """Log a booking-related activity"""
    try:
        with transaction.atomic():
            BookingLog.objects.create(
                user=user,
                booking_id=booking_id,
                action=action,
                old_status=old_status,
                new_status=new_status,
                description=description,
                metadata=metadata or {}
            )
            
            # Also log as general activity
            log_activity(
                user=user,
                category='booking',
                action=action,
                description=description,
                metadata=metadata
            )
            
    except Exception as e:
        log_system_error('BookingLog', f"Failed to log booking activity: {str(e)}", str(e))

def log_payment_activity(
    user=None,
    payment_id=None,
    order_id=None,
    action='',
    amount=None,
    method='',
    gateway='',
    old_status='',
    new_status='',
    description='',
    error_message='',
    metadata=None
):
    """Log a payment-related activity"""
    try:
        with transaction.atomic():
            PaymentLog.objects.create(
                user=user,
                payment_id=payment_id,
                order_id=order_id,
                action=action,
                amount=amount,
                method=method,
                gateway=gateway,
                old_status=old_status,
                new_status=new_status,
                description=description,
                error_message=error_message,
                metadata=metadata or {}
            )
            
            # Also log as general activity
            log_activity(
                user=user,
                category='payment',
                action=action,
                description=description,
                metadata=metadata
            )
            
    except Exception as e:
        log_system_error('PaymentLog', f"Failed to log payment activity: {str(e)}", str(e))

def log_user_activity(
    user,
    action='',
    description='',
    request=None,
    metadata=None
):
    """Log a user-related activity"""
    try:
        with transaction.atomic():
            log_data = {
                'user': user,
                'action': action,
                'description': description,
                'metadata': metadata or {}
            }
            
            if request:
                log_data['ip_address'] = get_client_ip(request)
                log_data['user_agent'] = get_user_agent(request)
            
            UserActivityLog.objects.create(**log_data)
            
            # Also log as general activity
            log_activity(
                user=user,
                category='user',
                action=action,
                description=description,
                metadata=metadata
            )
            
    except Exception as e:
        log_system_error('UserActivityLog', f"Failed to log user activity: {str(e)}", str(e))

def log_system_event(
    level='info',
    component='',
    message='',
    stack_trace='',
    metadata=None
):
    """Log a system-level event"""
    try:
        with transaction.atomic():
            SystemLog.objects.create(
                level=level,
                component=component,
                message=message,
                stack_trace=stack_trace,
                metadata=metadata or {}
            )
            
            # Also log as general activity for info and warning levels
            if level in ['info', 'warning']:
                log_activity(
                    category='system',
                    action=f"{component}: {level}",
                    description=message,
                    log_level=level,
                    metadata=metadata
                )
                
    except Exception as e:
        # If system logging fails, we can't do much more
        print(f"CRITICAL: Failed to log system event: {str(e)}")

def log_system_error(component, message, error_details, metadata=None):
    """Log a system error with full details"""
    log_system_event(
        level='error',
        component=component,
        message=message,
        stack_trace=error_details,
        metadata=metadata
    )

def log_audit_event(
    user=None,
    audit_type='',
    table_name='',
    record_id='',
    field_name='',
    old_value='',
    new_value='',
    description='',
    request=None,
    metadata=None
):
    """Log an audit event for sensitive operations"""
    try:
        with transaction.atomic():
            log_data = {
                'user': user,
                'audit_type': audit_type,
                'table_name': table_name,
                'record_id': str(record_id),
                'field_name': field_name,
                'old_value': str(old_value) if old_value is not None else '',
                'new_value': str(new_value) if new_value is not None else '',
                'description': description,
                'metadata': metadata or {}
            }
            
            if request:
                log_data['ip_address'] = get_client_ip(request)
            
            AuditLog.objects.create(**log_data)
            
            # Also log as general activity
            log_activity(
                user=user,
                category='admin',
                action=f"Audit: {audit_type}",
                description=description,
                log_level='warning',
                metadata=metadata
            )
            
    except Exception as e:
        log_system_error('AuditLog', f"Failed to log audit event: {str(e)}", str(e))

def log_data_change(
    user=None,
    table_name='',
    record_id='',
    field_name='',
    old_value='',
    new_value='',
    description='',
    request=None,
    metadata=None
):
    """Log a data change for audit purposes"""
    log_audit_event(
        user=user,
        audit_type='data_change',
        table_name=table_name,
        record_id=record_id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        description=description,
        request=request,
        metadata=metadata
    )

def log_security_event(
    user=None,
    description='',
    request=None,
    metadata=None
):
    """Log a security-related event"""
    log_audit_event(
        user=user,
        audit_type='security_event',
        table_name='',
        record_id='',
        field_name='',
        old_value='',
        new_value='',
        description=description,
        request=request,
        metadata=metadata
    )

def log_permission_change(
    user=None,
    target_user=None,
    old_permissions='',
    new_permissions='',
    description='',
    request=None,
    metadata=None
):
    """Log a permission change event"""
    log_audit_event(
        user=user,
        audit_type='permission_change',
        table_name='auth_user',
        record_id=target_user.id if target_user else '',
        field_name='permissions',
        old_value=old_permissions,
        new_value=new_permissions,
        description=description,
        request=request,
        metadata=metadata
    )

# Convenience functions for common operations
def log_booking_created(booking, user, request=None):
    """Log when a booking is created"""
    log_booking_activity(
        user=user,
        booking_id=booking.id,
        action='created',
        new_status=booking.status,
        description=f"Nueva reserva creada para {booking.venue.name} el {booking.start_datetime.date()}",
        metadata={
            'venue_name': booking.venue.name,
            'package_name': booking.package.title,
            'total_price': str(booking.total_price),
            'start_date': booking.start_datetime.isoformat(),
            'end_date': booking.end_datetime.isoformat()
        },
        request=request
    )

def log_booking_status_change(booking, user, old_status, new_status, request=None):
    """Log when a booking status changes"""
    log_booking_activity(
        user=user,
        booking_id=booking.id,
        action='status_changed',
        old_status=old_status,
        new_status=new_status,
        description=f"Estado de reserva cambiado de {old_status} a {new_status}",
        metadata={
            'venue_name': booking.venue.name,
            'package_name': booking.package.title,
            'old_status': old_status,
            'new_status': new_status
        },
        request=request
    )

def log_payment_attempt(payment, user, request=None):
    """Log when a payment is attempted"""
    log_payment_activity(
        user=user,
        payment_id=payment.id,
        order_id=payment.order.id,
        action='attempted',
        amount=payment.amount,
        method=payment.method,
        gateway=payment.gateway,
        old_status='',
        new_status=payment.status,
        description=f"Intento de pago via {payment.method} ({payment.gateway})",
        metadata={
            'booking_id': str(payment.order.booking.id),
            'venue_name': payment.order.booking.venue.name
        },
        request=request
    )

def log_payment_confirmation(payment, user, request=None):
    """Log when a payment is confirmed"""
    log_payment_activity(
        user=user,
        payment_id=payment.id,
        order_id=payment.order.id,
        action='confirmed',
        amount=payment.amount,
        method=payment.method,
        gateway=payment.gateway,
        old_status='pending',
        new_status='paid',
        description=f"Pago confirmado via {payment.method} ({payment.gateway})",
        metadata={
            'booking_id': str(payment.order.booking.id),
            'venue_name': payment.order.booking.venue.name,
            'transaction_id': payment.transaction_id
        },
        request=request
    )

def log_user_login(user, request):
    """Log when a user logs in"""
    log_user_activity(
        user=user,
        action='login',
        description=f"Usuario inició sesión desde {get_client_ip(request)}",
        request=request,
        metadata={
            'ip_address': get_client_ip(request),
            'user_agent': get_user_agent(request)
        }
    )

def log_user_logout(user, request):
    """Log when a user logs out"""
    log_user_activity(
        user=user,
        action='logout',
        description=f"Usuario cerró sesión desde {get_client_ip(request)}",
        request=request,
        metadata={
            'ip_address': get_client_ip(request),
            'user_agent': get_user_agent(request)
        }
    )

def log_booking_extra_services_change(booking, user, old_services, new_services, request=None):
    """Log when extra services are added/removed from a booking"""
    try:
        old_service_names = [service.name for service in old_services]
        new_service_names = [service.name for service in new_services]
        
        if set(old_services) != set(new_services):
            added_services = [s for s in new_services if s not in old_services]
            removed_services = [s for s in old_services if s not in new_services]
            
            changes = []
            if added_services:
                changes.append(f"Agregados: {', '.join([s.name for s in added_services])}")
            if removed_services:
                changes.append(f"Removidos: {', '.join([s.name for s in removed_services])}")
            
            description = f"Servicios extra modificados: {'; '.join(changes)}"
            
            log_booking_activity(
                user=user,
                booking_id=booking.id,
                action='extra_services_changed',
                old_status=booking.status,
                new_status=booking.status,
                description=description,
                metadata={
                    'venue_name': booking.venue.name,
                    'package_name': booking.package.title,
                    'old_services': old_service_names,
                    'new_services': new_service_names,
                    'added_services': [s.name for s in added_services],
                    'removed_services': [s.name for s in removed_services],
                    'total_price': str(booking.total_price)
                },
                request=request
            )
            
    except Exception as e:
        log_system_error('BookingLog', f"Failed to log extra services change: {str(e)}", str(e))

def log_booking_package_change(booking, user, old_package, new_package, request=None):
    """Log when a booking's package is changed"""
    try:
        description = f"Paquete cambiado de '{old_package.title}' a '{new_package.title}'"
        
        log_booking_activity(
            user=user,
            booking_id=booking.id,
            action='package_changed',
            old_status=booking.status,
            new_status=booking.status,
            description=description,
            metadata={
                'venue_name': booking.venue.name,
                'old_package': old_package.title,
                'new_package': new_package.title,
                'old_package_price': str(old_package.price),
                'new_package_price': str(new_package.price),
                'old_total_price': str(booking.total_price),
                'new_total_price': str(booking.total_price)
            },
            request=request
        )
        
    except Exception as e:
        log_system_error('BookingLog', f"Failed to log package change: {str(e)}", str(e))

def log_booking_date_change(booking, user, old_start, old_end, new_start, new_end, request=None):
    """Log when booking dates are changed"""
    try:
        description = f"Fechas de reserva modificadas"
        
        log_booking_activity(
            user=user,
            booking_id=booking.id,
            action='dates_changed',
            old_status=booking.status,
            new_status=booking.status,
            description=description,
            metadata={
                'venue_name': booking.venue.name,
                'package_name': booking.package.title,
                'old_start_datetime': old_start.isoformat(),
                'old_end_datetime': old_end.isoformat(),
                'new_start_datetime': new_start.isoformat(),
                'new_end_datetime': new_end.isoformat(),
                'old_duration_hours': (old_end - old_start).total_seconds() / 3600,
                'new_duration_hours': (new_end - new_start).total_seconds() / 3600
            },
            request=request
        )
        
    except Exception as e:
        log_system_error('BookingLog', f"Failed to log date change: {str(e)}", str(e))

def log_booking_price_change(booking, user, old_total_price, new_total_price, old_advance, new_advance, request=None):
    """Log when booking prices are changed"""
    try:
        changes = []
        if old_total_price != new_total_price:
            changes.append(f"Precio total: ${old_total_price} → ${new_total_price}")
        if old_advance != new_advance:
            changes.append(f"Adelanto: ${old_advance} → ${new_advance}")
        
        if changes:
            description = f"Precios modificados: {'; '.join(changes)}"
            
            log_booking_activity(
                user=user,
                booking_id=booking.id,
                action='prices_changed',
                old_status=booking.status,
                new_status=booking.status,
                description=description,
                metadata={
                    'venue_name': booking.venue.name,
                    'package_name': booking.package.title,
                    'old_total_price': str(old_total_price),
                    'new_total_price': str(new_total_price),
                    'old_advance_paid': str(old_advance),
                    'new_advance_paid': str(new_advance),
                    'price_difference': str(new_total_price - old_total_price),
                    'advance_difference': str(new_advance - old_advance)
                },
                request=request
            )
        
    except Exception as e:
        log_system_error('BookingLog', f"Failed to log price change: {str(e)}", str(e))
