import asyncio
import json
import logging
import aio_pika
from aiosmtplib import send
from email.message import EmailMessage
from asgiref.sync import sync_to_async

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Transaction_monitoring.settings")
import django
django.setup()

from transaction.models import Transaction

# Настройки логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Настройки подключения к RabbitMQ
RABBITMQ_URL = "amqp://admin:admin@rabbitmq:5672/"
RABBITMQ_QUEUE = "transaction_notifications"

# Настройки для отправки email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "stepanderdichok"
SMTP_PASSWORD = "kpbhbxzmhenzyein"
FROM_EMAIL = "stepanderdichok@gmail.com"

# Настройка Django для использования моделей
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Transaction_monitoring.settings")
import django
django.setup()

from account.models import UserProfile


@sync_to_async
def get_user_email_from_transaction(transaction_id):
    try:
        transaction = Transaction.objects.get(id=transaction_id)
        sender_user_id = transaction.sender_account.user.id  # Получаем ID пользователя отправителя
        user_profile = UserProfile.objects.get(user_id=sender_user_id)
        user_email = user_profile.user.email  # Получаем email из связанного объекта User
        return user_email
    except Transaction.DoesNotExist:
        logger.error(f"Transaction not found for transaction ID {transaction_id}")
        return None
    except UserProfile.DoesNotExist:
        logger.error(f"UserProfile not found for user ID {sender_user_id}")
        return None


async def send_email(subject, body, to_email):
    try:
        message = EmailMessage()
        message["From"] = FROM_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        await send(message, hostname=SMTP_SERVER, port=SMTP_PORT, username=SMTP_USER, password=SMTP_PASSWORD)
        logger.info(f"Email sent to {to_email} with subject: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")


async def process_notification(message):
    try:
        transaction = json.loads(message.body)

        transaction_id = transaction.get("transaction_id", "Unknown")
        status = transaction.get("status", "Unknown")
        reasons = transaction.get("reasons", [])
        ip = transaction.get("ip", "Unknown")

        if transaction_id != "Unknown":
            to_email = await get_user_email_from_transaction(transaction_id)
            if not to_email:
                logger.error(f"No email found for transaction ID {transaction_id}")
                await message.ack()
                return
        else:
            logger.error(f"No transaction_id in message")
            await message.ack()
            return

        subject = f"Warning: Transaction {transaction_id} requires attention!"
        body = (f"Transaction ID: {transaction_id}\n"
                f"Status: {status}\n"
                f"IP Address: {ip}\n"
                f"Reasons:\n" + "\n".join(f"- {reason}" for reason in reasons))

        await send_email(subject, body, to_email)

        await message.ack()

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await message.nack()


async def consume_notifications():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()

    queue = await channel.declare_queue(RABBITMQ_QUEUE, durable=False)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            await process_notification(message)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(consume_notifications())
