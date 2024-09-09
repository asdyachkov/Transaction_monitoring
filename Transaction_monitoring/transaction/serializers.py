from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'sender_account', 'receiver_account', 'amount', 'timestamp', 'status', 'type', 'description']
