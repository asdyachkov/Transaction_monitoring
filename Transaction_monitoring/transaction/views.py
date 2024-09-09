from rest_framework import viewsets
from rest_framework.response import Response
from django.core.cache import cache

from clickhouse.clickhouse_client import save_transaction
from transaction.kafka_producer import publish_transaction
from transaction.models import Transaction
from transaction.serializers import TransactionSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()

    def get_queryset(self):
        cache_key = 'all_transactions'
        cached_data = cache.get(cache_key)

        if cached_data:
            return cached_data

        queryset = super().get_queryset()
        serialized_data = list(queryset.values())  # Преобразование QuerySet в список словарей
        cache.set(cache_key, serialized_data, timeout=3600)
        return queryset

    async def perform_create(self, serializer):
        transaction = serializer.save()
        transaction_data = {
            'id': transaction.id,
            'sender_account': transaction.sender_account.id,
            'receiver_account': transaction.receiver_account.id,
            'amount': str(transaction.amount),
            'currency': transaction.sender_account.currency.code,
            'description': transaction.description,
            'timestamp': transaction.timestamp.isoformat(),
            'status': transaction.status,
            'type': transaction.type,
            'ip': self.request.META.get('REMOTE_ADDR')
        }
        await publish_transaction(transaction_data)
        await save_transaction(transaction_data)

    async def retrieve(self, request, *args, **kwargs):
        transaction_id = kwargs.get('pk')
        cache_key = f'transaction_{transaction_id}'
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        cache.set(cache_key, data, timeout=3600)
        return Response(data)

    async def perform_update(self, serializer):
        instance = serializer.save()
        cache.delete('all_transactions')
        cache.delete(f'transaction_{instance.id}')

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete('all_transactions')
        cache.delete(f'transaction_{instance.id}')

