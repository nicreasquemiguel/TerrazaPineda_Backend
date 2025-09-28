from django.dispatch import receiver
from djoser.signals import user_activated

@receiver(user_activated)
def mark_email_verified(sender, user, **kwargs):
    user.email_verified = True
    user.save(update_fields=['email_verified'])