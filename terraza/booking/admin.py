from django.contrib import admin
from .models import Package, ExtraService, Rule, Venue, Coupon, Booking, VenueFeatures, BookingWish, Notification, BookingLineItem, VenueConfiguration

@admin.register(VenueConfiguration)
class VenueConfigurationAdmin(admin.ModelAdmin):
    list_display = ['open_time', 'close_time']

    def has_add_permission(self, request):
        return not VenueConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ['title', 'n_people', 'price']
    list_filter = ['n_people']
    search_fields = ['title', 'description']
    ordering = ['n_people']

@admin.register(ExtraService)
class ExtraServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_active', 'icon']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['name']

@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'desciption']
    search_fields = ['title', 'desciption']

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'active', 'slug']
    list_filter = ['active']
    search_fields = ['name', 'address']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_percent', 'max_uses', 'current_uses', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code']
    readonly_fields = ['current_uses']

class BookingLineItemInline(admin.TabularInline):
    model = BookingLineItem
    extra = 0
    readonly_fields = ['item_type', 'description', 'unit_price', 'quantity', 'subtotal']
    can_delete = False

    def subtotal(self, obj):
        return obj.subtotal
    subtotal.short_description = 'Subtotal'

    def has_add_permission(self, _request, _obj=None):
        return False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'venue', 'package', 'start_datetime', 'end_datetime', 'total_price', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'venue', 'package']
    search_fields = ['id', 'user__email', 'user__first_name', 'user__last_name', 'venue__name']
    readonly_fields = ['id', 'created_at', 'total_price']
    filter_horizontal = ['extra_services', 'visible_to_users']
    date_hierarchy = 'start_datetime'
    inlines = [BookingLineItemInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.create_line_items()
        form.instance.total_price = form.instance.calculate_total()
        form.instance.save(update_fields=['total_price'])

@admin.register(VenueFeatures)
class VenueFeaturesAdmin(admin.ModelAdmin):
    list_display = ['hotel', 'icon_type', 'icon', 'name']
    list_filter = ['icon_type', 'hotel']
    search_fields = ['name', 'hotel__name']

admin.site.register(BookingWish)
admin.site.register(Notification)
