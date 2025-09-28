from django.contrib import admin
from .models import UserAccount, Profile

# Register your models here.
@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'phone', 'is_active', 'is_staff', 'date_joined', 'email_verified']
    list_filter = ['is_active', 'is_staff', 'email_verified', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    readonly_fields = ['date_joined']
    ordering = ['-date_joined']

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'gender', 'country', 'state', 'date_created', 'pid']
    list_filter = ['gender', 'country', 'date_created']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'pid']
    readonly_fields = ['date_created', 'pid']
