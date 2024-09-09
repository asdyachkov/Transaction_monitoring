import asyncio
import json
import logging
import os
from decimal import Decimal
import datetime
import aio_pika
from asgiref.sync import sync_to_async
from django.db import transaction as db_transaction

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Transaction_monitoring.settings")
import django
django.setup()

from transaction.models import Transaction
from account.models import Account, UserProfile

# Настройка логирования
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Конфигурация RabbitMQ
RABBITMQ_URL = "amqp://admin:admin@rabbitmq:5672/"
RABBITMQ_QUEUE = "transaction_notifications"
RABBITMQ_PROCESSING_QUEUE = 'transaction_processing'

@sync_to_async
def update_transaction_status(transaction_id, status):
    try:
        with db_transaction.atomic():
            Transaction.objects.filter(id=transaction_id).update(status=status)
            logger.info(f"Transaction {transaction_id} status updated to {status}.")
    except Exception as e:
        logger.error(f"Error updating status for transaction {transaction_id}: {e}")

@sync_to_async
def get_account(account_id):
    try:
        return Account.objects.filter(id=account_id).first()
    except Exception as e:
        logger.error(f"Error retrieving account {account_id}: {e}")
        return None

@sync_to_async
def get_user_profile(user_id):
    try:
        return UserProfile.objects.filter(user_id=user_id).first()
    except Exception as e:
        logger.error(f"Error retrieving user profile for user ID {user_id}: {e}")
        return None

@sync_to_async
def get_transaction_history(user_id):
    try:
        return list(Transaction.objects.filter(sender_account__user_id=user_id).values('timestamp', 'amount'))
    except Exception as e:
        logger.error(f"Error retrieving transaction history for user ID {user_id}: {e}")
        return []


@sync_to_async
def update_user_profile(user_profile, transaction, transaction_history):
    try:
        # Добавляем страну в список часто используемых
        country = transaction.get('country')
        if country and country not in user_profile.frequent_countries:
            user_profile.frequent_countries.append(country)

        # Добавляем тип транзакции в список часто используемых
        tx_type = transaction.get('type')
        if tx_type and tx_type not in user_profile.frequent_transaction_types:
            user_profile.frequent_transaction_types.append(tx_type)

        # Пересчитываем среднюю сумму транзакций
        all_amounts = [Decimal(tx['amount']) for tx in transaction_history if tx.get('amount')] + [
            Decimal(transaction['amount'])]
        if all_amounts:
            user_profile.average_transaction_amount = sum(all_amounts) / len(all_amounts)

        # Обновляем максимальную сумму транзакции, если текущая больше
        max_amount = Decimal(transaction['amount'])
        if max_amount > user_profile.max_transaction_amount:
            user_profile.max_transaction_amount = max_amount

        # Обновляем время необычных транзакций
        transaction_time = transaction['timestamp']
        if isinstance(transaction_time, str):
            transaction_time = datetime.datetime.strptime(transaction_time, "%Y-%m-%dT%H:%M:%S.%f%z")

        if transaction_time.hour < user_profile.unusual_time_hour_start or transaction_time.hour > user_profile.unusual_time_hour_end:
            user_profile.unusual_time_hour_start = min(user_profile.unusual_time_hour_start, transaction_time.hour)
            user_profile.unusual_time_hour_end = max(user_profile.unusual_time_hour_end, transaction_time.hour)

        # Обновляем максимальное количество транзакций в час
        recent_transactions = [
            tx for tx in transaction_history
            if (transaction_time - tx['timestamp']).total_seconds() < 3600
        ]
        if len(recent_transactions) > user_profile.max_transactions_per_hour:
            user_profile.max_transactions_per_hour = len(recent_transactions)

        # Обновляем список подозрительных стран
        if country and country not in user_profile.suspicious_countries:
            user_profile.suspicious_countries.append(country)

        # Сохраняем изменения
        user_profile.save()
    except Exception as e:
        logger.error(f"Error updating user profile for user ID {user_profile.user_id}: {e}")


async def process_transaction(transaction):
    try:
        sender_account = await get_account(transaction['sender_account'])
        if sender_account is None:
            await update_transaction_status(transaction['id'], 'failed')
            return

        receiver_account = await get_account(transaction['receiver_account'])
        if receiver_account is None:
            await update_transaction_status(transaction['id'], 'failed')
            return

        amount = Decimal(transaction['amount'])
        if sender_account.balance < amount:
            logger.error(f"Insufficient funds in sender account {transaction['sender_account']}.")
            await update_transaction_status(transaction['id'], 'failed')
            return

        # Выполнение обновления балансов
        sender_account.balance -= amount
        receiver_account.balance += amount

        await sync_to_async(sender_account.save)()
        await sync_to_async(receiver_account.save)()

        # Обновление статуса транзакции
        await update_transaction_status(transaction['id'], 'success')

        # Обновление профиля пользователя
        user_profile = await get_user_profile(sender_account.user_id)
        if user_profile:
            transaction_history = await get_transaction_history(sender_account.user_id)
            await update_user_profile(user_profile, transaction, transaction_history)

        logger.info(f"Transaction {transaction['id']} processed successfully.")

    except Exception as e:
        logger.error(f"Error processing transaction {transaction['id']}: {e}")
        await update_transaction_status(transaction['id'], 'failed')


async def consume_transactions():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)

    async with connection:
        async with connection.channel() as channel:
            queue = await channel.declare_queue(RABBITMQ_PROCESSING_QUEUE, durable=False)
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    try:
                        transaction = json.loads(message.body)
                        logger.info(f"Processing transaction {transaction['id']}")
                        await process_transaction(transaction)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decoding message body: {e}")
                    except Exception as e:
                        logger.error(f"Error handling message: {e}")


async def main():
    await consume_transactions()

if __name__ == "__main__":
    asyncio.run(main())
