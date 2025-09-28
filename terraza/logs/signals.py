from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import user_logged_in, user_logged_out
from django.utils import timezone

# Import signals lazily to avoid circular imports
def get_logging_utils():
    """Get logging utilities lazily to avoid circular imports"""
    try:
        from .utils import (
            log_booking_created, log_booking_status_change,
            log_payment_attempt, log_payment_confirmation,
            log_user_login, log_user_logout,
            log_data_change, log_system_event
        )
        return {
            'log_booking_created': log_booking_created,
            'log_booking_status_change': log_booking_status_change,
            'log_payment_attempt': log_payment_attempt,
            'log_payment_confirmation': log_payment_confirmation,
            'log_user_login': log_user_login,
            'log_user_logout': log_user_logout,
            'log_data_change': log_data_change,
            'log_system_event': log_system_event
        }
    except ImportError as e:
        print(f"Warning: Could not import logging utilities: {e}")
        return {}

# User authentication signals
@receiver(user_logged_in)
def log_user_login_signal(sender, request, user, **kwargs):
    """Log when a user logs in"""
    try:
        utils = get_logging_utils()
        if 'log_user_login' in utils:
            utils['log_user_login'](user, request)
    except Exception as e:
        print(f"Failed to log user login: {e}")

@receiver(user_logged_out)
def log_user_logout_signal(sender, request, user, **kwargs):
    """Log when a user logs out"""
    try:
        utils = get_logging_utils()
        if 'log_user_logout' in utils:
            utils['log_user_logout'](user, request)
    except Exception as e:
        print(f"Failed to log user logout: {e}")

# Booking signals
@receiver(post_save, sender=None)
def log_booking_changes(sender, instance, created, **kwargs):
    """Log booking creation and status changes"""
    try:
        # Check if this is a Booking model
        if hasattr(instance, '_meta') and instance._meta.model_name == 'booking':
            utils = get_logging_utils()
            if created and 'log_booking_created' in utils:
                # New booking created
                utils['log_booking_created'](instance, instance.user)
            elif hasattr(instance, '_old_status') and instance._old_status != instance.status:
                # Status changed
                if 'log_booking_status_change' in utils:
                    utils['log_booking_status_change'](
                        instance, 
                        instance.user, 
                        instance._old_status, 
                        instance.status
                    )
    except Exception as e:
        print(f"Failed to log booking changes: {e}")

@receiver(pre_save, sender=None)
def store_old_booking_status(sender, instance, **kwargs):
    """Store old status before saving to detect changes"""
    try:
        # Check if this is a Booking model
        if hasattr(instance, '_meta') and instance._meta.model_name == 'booking':
            if instance.pk:  # Only for existing instances
                from booking.models import Booking
                try:
                    old_instance = Booking.objects.get(pk=instance.pk)
                    instance._old_status = old_instance.status
                except Booking.DoesNotExist:
                    pass
    except Exception as e:
        print(f"Failed to store old booking status: {e}")

# Payment signals
@receiver(post_save, sender=None)
def log_payment_changes(sender, instance, created, **kwargs):
    """Log payment creation and status changes"""
    try:
        # Check if this is a Payment model
        if hasattr(instance, '_meta') and instance._meta.model_name == 'payment':
            utils = get_logging_utils()
            if created and 'log_payment_attempt' in utils:
                # New payment created
                utils['log_payment_attempt'](instance, instance.user)
            elif hasattr(instance, '_old_status') and instance._old_status != instance.status:
                # Status changed
                if instance.status == 'paid' and instance._old_status == 'pending':
                    if 'log_payment_confirmation' in utils:
                        utils['log_payment_confirmation'](instance, instance.user)
                else:
                    # Log other status changes
                    if 'log_payment_activity' in utils:
                        utils['log_payment_activity'](
                            user=instance.user,
                            payment_id=instance.id,
                            order_id=instance.order.id,
                            action='status_changed',
                            amount=instance.amount,
                            method=instance.method,
                            gateway=instance.gateway,
                            old_status=instance._old_status,
                            new_status=instance.status,
                            description=f"Payment status changed from {instance._old_status} to {instance.status}",
                            metadata={
                                'booking_id': str(instance.order.booking.id),
                                'venue_name': instance.order.booking.venue.name
                            }
                        )
    except Exception as e:
        print(f"Failed to log payment changes: {e}")

@receiver(pre_save, sender=None)
def store_old_payment_status(sender, instance, **kwargs):
    """Store old status before saving to detect changes"""
    try:
        # Check if this is a Payment model
        if hasattr(instance, '_meta') and instance._meta.model_name == 'payment':
            if instance.pk:  # Only for existing instances
                from store.models import Payment
                try:
                    old_instance = Payment.objects.get(pk=instance.pk)
                    instance._old_status = old_instance.status
                except Payment.DoesNotExist:
                    pass
    except Exception as e:
        print(f"Failed to store old payment status: {e}")

# User account signals
@receiver(post_save, sender=None)
def log_user_account_changes(sender, instance, created, **kwargs):
    """Log user account changes"""
    try:
        # Check if this is a UserAccount model
        if hasattr(instance, '_meta') and instance._meta.model_name == 'useraccount':
            utils = get_logging_utils()
            if created and 'log_user_activity' in utils:
                utils['log_user_activity'](
                    user=instance,
                    action='account_created',
                    description=f"Nueva cuenta de usuario creada: {instance.email}"
                )
            elif hasattr(instance, '_old_data'):
                # Check for important field changes
                old_data = instance._old_data
                changes = []
                
                for field in ['first_name', 'last_name', 'email', 'phone', 'is_active']:
                    if hasattr(instance, field) and hasattr(old_data, field):
                        old_value = getattr(old_data, field)
                        new_value = getattr(instance, field)
                        if old_value != new_value:
                            changes.append(f"{field}: {old_value} → {new_value}")
                
                if changes and 'log_data_change' in utils:
                    utils['log_data_change'](
                        user=instance,
                        table_name='users_useraccount',
                        record_id=instance.id,
                        field_name=', '.join([c.split(':')[0] for c in changes]),
                        old_value='; '.join([c.split(': ')[1].split(' → ')[0] for c in changes]),
                        new_value='; '.join([c.split(': ')[1].split(' → ')[1] for c in changes]),
                        description=f"Cuenta de usuario actualizada: {', '.join(changes)}"
                    )
    except Exception as e:
        print(f"Failed to log user account changes: {e}")

@receiver(pre_save, sender=None)
def store_old_user_data(sender, instance, **kwargs):
    """Store old user data before saving to detect changes"""
    try:
        # Check if this is a UserAccount model
        if hasattr(instance, '_meta') and instance._meta.model_name == 'useraccount':
            if instance.pk:  # Only for existing instances
                from users.models import UserAccount
                try:
                    old_instance = UserAccount.objects.get(pk=instance.pk)
                    instance._old_data = old_instance
                except UserAccount.DoesNotExist:
                    pass
    except Exception as e:
        print(f"Failed to store old user data: {e}")

# System startup logging
def log_system_startup():
    """Log system startup"""
    try:
        utils = get_logging_utils()
        if 'log_system_event' in utils:
            utils['log_system_event'](
                level='info',
                component='System',
                message='Sistema Terraza iniciado exitosamente',
                metadata={'startup_time': timezone.now().isoformat()}
            )
    except Exception as e:
        print(f"Failed to log system startup: {e}")

# Call startup logging when signals are imported
try:
    log_system_startup()
except Exception:
    pass
