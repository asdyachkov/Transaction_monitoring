from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, Account


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профили'
    fk_name = 'user'


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ('id', 'username', 'email', 'phone_number', 'is_staff', 'is_active', 'is_verified')
    list_filter = ('is_staff', 'is_active', 'is_verified')
    search_fields = ('username', 'email', 'phone_number')
    ordering = ('-date_joined',)
    filter_horizontal = ()
    list_per_page = 25


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'bio', 'language_preference', 'average_transaction_amount')
    search_fields = ('user__username', 'bio')
    list_filter = ('language_preference',)
    ordering = ('user',)
    list_per_page = 25


class AccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'balance', 'currency', 'created_at')
    list_filter = ('currency', 'created_at')
    search_fields = ('user__username', 'currency__code')
    ordering = ('-created_at',)
    list_per_page = 25


admin.site.register(User, UserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Account, AccountAdmin)
