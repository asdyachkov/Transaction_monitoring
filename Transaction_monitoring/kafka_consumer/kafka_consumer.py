import asyncio
import json
import logging
import datetime
import os
import aiohttp
import pika
from aiokafka import AIOKafkaConsumer
from asgiref.sync import sync_to_async
from decimal import Decimal
import coloredlogs

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Transaction_monitoring.settings")
import django
django.setup()

from account.models import UserProfile, Account
from transaction.models import Transaction

# Настройка логирования с цветами
logger = logging.getLogger(__name__)
coloredlogs.install(level='INFO', logger=logger,
                    fmt='%(asctime)s - %(levelname)s - %(message)s',
                    level_styles={
                        'info': {'color': 'green'},
                        'debug': {'color': 'blue'},
                        'warning': {'color': 'yellow'},
                        'error': {'color': 'red'},
                        'critical': {'color': 'red', 'bold': True}
                    },
                    field_styles={
                        'asctime': {'color': 'cyan'},
                        'levelname': {'bold': True}
                    })

# Конфигурация RabbitMQ
RABBITMQ_HOST = 'rabbitmq'
RABBITMQ_PORT = 5672
RABBITMQ_USER = 'admin'
RABBITMQ_PASSWORD = 'admin'
RABBITMQ_QUEUE = 'suspicious_transactions'
RABBITMQ_NOTIFICATIONS_QUEUE = 'transaction_notifications'
RABBITMQ_PROCESSING_QUEUE = 'transaction_processing'

# API для получения информации о местоположении по IP
IPINFO_API_URL = 'https://ipinfo.io/{}/json'


async def get_country_from_ip(ip):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(IPINFO_API_URL.format(ip)) as response:
                data = await response.json()
                logger.info(f"Fetched country data for IP {ip}: {data}")
                return data.get('country', 'Unknown')
    except Exception as e:
        logger.error(f"Failed to get country from IP {ip}: {e}")
        return 'Unknown'

async def analyze_transaction(transaction, user_profile, transaction_history):
    suspicious_reasons = []
    risk_level = 'all_ok'

    # Пороговые значения для пользователя
    max_transaction_amount = user_profile.max_transaction_amount
    unusual_time_hour_start = user_profile.unusual_time_hour_start
    unusual_time_hour_end = user_profile.unusual_time_hour_end
    max_transactions_per_hour = user_profile.max_transactions_per_hour
    suspicious_countries = set(user_profile.suspicious_countries)

    # Проверка времени транзакции
    transaction_time = datetime.datetime.strptime(str(transaction['timestamp']), "%Y-%m-%dT%H:%M:%S.%f%z")
    if unusual_time_hour_start <= transaction_time.hour <= unusual_time_hour_end:
        suspicious_reasons.append(f"Transaction occurred during unusual time: {transaction_time.hour}:00")
        risk_level = 'notify'

    # Получение IP из транзакции и проверка географического местоположения
    ip = transaction.get('ip')
    country = ip
    if ip:
        country = await get_country_from_ip(ip)
        if country and country not in user_profile.frequent_countries:
            suspicious_reasons.append(f"Transaction from an unusual country: {country}")
            risk_level = 'notify'

        # Проверка блокированных стран
        if country and country in user_profile.suspicious_countries:
            suspicious_reasons.append(f"Transaction from a blocked country: {country}")
            risk_level = 'cancel'

    # Проверка частоты транзакций
    recent_transactions = [tx for tx in transaction_history if (
                transaction_time - datetime.datetime.strptime(str(tx['timestamp']),
                                                              "%Y-%m-%d %H:%M:%S.%f%z")).total_seconds() < 3600]
    if len(recent_transactions) > max_transactions_per_hour:
        suspicious_reasons.append(f"More than {max_transactions_per_hour} transactions in the past hour")
        risk_level = 'notify'

    # Проверка на аномальное поведение (сравнение с историей транзакций)
    if user_profile.average_transaction_amount and Decimal(transaction['amount']) > user_profile.average_transaction_amount * 2:
        suspicious_reasons.append(f"Transaction amount {transaction['amount']} significantly deviates from average")
        risk_level = 'notify'

    # Проверка суммы транзакции
    if Decimal(transaction['amount']) > max_transaction_amount:
        suspicious_reasons.append(f"Transaction amount {transaction['amount']} exceeds the maximum allowed limit")
        risk_level = 'cancel'

    # Проверка текущего баланса
    sender_account = await get_account(transaction['sender_account'])
    if sender_account.balance < Decimal(transaction['amount']):
        suspicious_reasons.append(f"Insufficient funds: {sender_account.balance} < {transaction['amount']}")
        risk_level = 'cancel'

    return risk_level, suspicious_reasons, country

@sync_to_async
def get_user_profile(user_id):
    try:
        return UserProfile.objects.get(user_id=user_id)
    except UserProfile.DoesNotExist:
        return None

@sync_to_async
def get_transaction_history(user_id):
    return list(Transaction.objects.filter(sender_account__user_id=user_id).values())

@sync_to_async
def get_account(account_id):
    try:
        return Account.objects.get(id=account_id)
    except Account.DoesNotExist:
        return None

@sync_to_async
def update_transaction_status(transaction_id, status):
    try:
        transaction = Transaction.objects.get(id=transaction_id)
        transaction.status = status
        transaction.save()
    except Transaction.DoesNotExist:
        logger.error(f"Transaction with ID {transaction_id} does not exist for status update")

async def process_transaction(transaction):
    transaction['status'] = 'pending'
    user_profile = await get_user_profile(transaction['sender_account'])
    if user_profile is None:
        logger.error(f"UserProfile not found for user ID {transaction['sender_account']}")
        return

    transaction_history = await get_transaction_history(transaction['sender_account'])
    risk_level, reasons, country = await analyze_transaction(transaction, user_profile, transaction_history)

    if risk_level == 'all_ok':
        await send_to_processing_queue(transaction)
        logger.info(f"Transaction {transaction['id']} processed successfully.")
    elif risk_level == 'notify':
        await notify_rabbitmq(transaction, reasons)
        await send_to_processing_queue(transaction)
        logger.info(f"Transaction {transaction['id']} flagged for notification.")
    elif risk_level == 'cancel':
        transaction['status'] = 'canceled'
        await notify_rabbitmq(transaction, reasons)
        await update_transaction_status(transaction['id'], 'cancelled')
        logger.warning(f"Transaction {transaction['id']} cancelled and flagged as suspicious.")

async def send_to_processing_queue(transaction):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_PROCESSING_QUEUE)

    channel.basic_publish(exchange='', routing_key=RABBITMQ_PROCESSING_QUEUE, body=json.dumps(transaction))
    logger.info(f"Transaction {transaction['id']} sent to processing queue")
    connection.close()

async def notify_rabbitmq(transaction, reasons):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_NOTIFICATIONS_QUEUE)

    message = {
        'transaction_id': transaction.get('id'),
        'status': transaction.get('status', 'pending'),
        'reasons': reasons,
        'message': f"Transaction from {transaction.get('ip', 'unknown')} needs attention"
    }
    channel.basic_publish(exchange='', routing_key=RABBITMQ_NOTIFICATIONS_QUEUE, body=json.dumps(message))
    logger.info(f"Notification sent for transaction {transaction.get('id')}")
    connection.close()

async def consume_transactions():
    consumer = AIOKafkaConsumer(
        'transactions',
        bootstrap_servers='kafka:9092',
        group_id='transaction-consumer-group',
        auto_offset_reset='earliest'
    )
    await consumer.start()
    try:
        async for msg in consumer:
            transaction = json.loads(msg.value)
            await process_transaction(transaction)
    finally:
        await consumer.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(consume_transactions())
