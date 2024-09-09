from .models import Transaction
from django.contrib import admin


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('sender_account', 'receiver_account', 'amount', 'timestamp', 'status')
    list_filter = ('status', 'timestamp')
    search_fields = ('sender_account__user__username', 'receiver_account__user__username', 'amount')
    ordering = ('-timestamp',)
