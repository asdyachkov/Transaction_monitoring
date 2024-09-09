import httpx
from uuid import uuid4
from datetime import datetime

CLICKHOUSE_HOST = 'http://clickhouse:8123'  # HTTP API endpoint
CLICKHOUSE_USER = 'admin'
CLICKHOUSE_PASSWORD = 'admin'

async def query_clickhouse(query: str, params=None):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            CLICKHOUSE_HOST,
            params={'user': CLICKHOUSE_USER, 'password': CLICKHOUSE_PASSWORD},
            data=query
        )
        response.raise_for_status()
        return response.json()

async def create_table():
    query = """
    CREATE TABLE IF NOT EXISTS transactions (
        id String,
        sender_account String,
        receiver_account String,
        amount Decimal(20, 2),
        timestamp DateTime,
        transaction_type String,
        status String,
        description String,
        PRIMARY KEY (id)
    ) ENGINE = MergeTree()
    ORDER BY id;
    """
    await query_clickhouse(query)

def format_timestamp(timestamp_str):
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError as e:
        print(f"Error formatting timestamp: {e}")
        raise

async def save_transaction(transaction_data):
    await create_table()

    transaction_data['id'] = str(uuid4())
    transaction_data['timestamp'] = format_timestamp(transaction_data['timestamp'])

    query = """
    INSERT INTO transactions (id, sender_account, receiver_account, amount, timestamp, transaction_type, status, description)
    VALUES ('{id}', '{sender_account}', '{receiver_account}', {amount}, '{timestamp}', '{type}', '{status}', '{description}')
    """.format(**transaction_data)

    await query_clickhouse(query)
