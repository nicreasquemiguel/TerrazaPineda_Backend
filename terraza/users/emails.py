from djoser.email import ActivationEmail, PasswordResetEmail, UsernameResetEmail, ConfirmationEmail
from django.conf import settings


def _inject_contact(context):
    context['contact_email'] = getattr(settings, 'CONTACT_EMAIL', settings.DEFAULT_FROM_EMAIL)
    return context


class CustomActivationEmail(ActivationEmail):
    def get_context_data(self):
        return _inject_contact(super().get_context_data())


class CustomPasswordResetEmail(PasswordResetEmail):
    def get_context_data(self):
        return _inject_contact(super().get_context_data())


class CustomUsernameResetEmail(UsernameResetEmail):
    def get_context_data(self):
        return _inject_contact(super().get_context_data())


class CustomConfirmationEmail(ConfirmationEmail):
    def get_context_data(self):
        return _inject_contact(super().get_context_data())
