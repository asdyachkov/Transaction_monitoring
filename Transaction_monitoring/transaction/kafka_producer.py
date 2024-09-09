from aiokafka import AIOKafkaProducer
import json
from django.conf import settings


async def kafka_producer():
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BROKER_URL
    )
    await producer.start()
    return producer


async def publish_transaction(transaction_data):
    producer = await kafka_producer()
    try:
        await producer.send_and_wait(
            settings.KAFKA_TOPIC,
            json.dumps(transaction_data).encode('utf-8')
        )
    finally:
        await producer.stop()
