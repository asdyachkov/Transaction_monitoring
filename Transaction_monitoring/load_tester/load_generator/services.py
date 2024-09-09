import asyncio
import aiohttp
import time
import random
import logging

from analytics.models import TestStatus
from analytics.services import AnalyticsService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class LoadGeneratorService:
    def __init__(self):
        self.analytics_service = AnalyticsService()
        self.generated_users = []
        self.generated_accounts = []
        self.test_status = TestStatus()

    async def send_request(self, session, endpoint, data, method='POST'):
        start_time = time.time()
        try:
            if method == 'POST':
                async with session.post(f"http://django:8000/api/{endpoint}/", json=data) as response:
                    response_time = time.time() - start_time
                    status = "success" if response.status in (200, 201) else "failure"
                    response_data = await response.json()
                    self.analytics_service.log_request(endpoint, data, status, response_time)
                    logger.info(f"Request to {endpoint} completed with status: {status} in {response_time:.2f} seconds.")
                    return response_data if status == "success" else None

            elif method == 'DELETE':
                async with session.delete(f"http://django:8000/api/{endpoint}/", json=data) as response:
                    response_time = time.time() - start_time
                    status = "success" if response.status in (200, 204) else "failure"
                    self.analytics_service.log_request(endpoint, data, status, response_time)
                    logger.info(f"Request to {endpoint} completed with status: {status} in {response_time:.2f} seconds.")
                    return response.status == 204

        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Error sending request to {endpoint}: {str(e)}")
            self.analytics_service.log_request(endpoint, data, "error", response_time, error=str(e))
            return None

    async def generate_load(self, users, transactions_per_second):
        semaphore = asyncio.Semaphore(10000)
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0)) as session:
            for i in range(users):
                user_data = {
                    "username": f"user_{int(time.time())}_{i}",
                    "password": "password",
                    "email": f"user_{int(time.time())}_{i}@example.com",
                    "phone_number": i
                }
                response = await self.send_request(session, "users", user_data)
                if response:
                    self.generated_users.append(response.get("id"))

            for user_id in self.generated_users:
                if not self.generated_users:
                    break

                profile_data = {
                    "user": user_id,
                    "bio": "Test Bio",
                    "language_preference": "eng"
                }
                await self.send_request(session, "account-profiles", profile_data)

                account_data = {
                    "user": user_id,
                    "currency": 1,
                    "balance": random.randint(10, 1000000),
                }
                response = await self.send_request(session, "accounts", account_data)
                if response:
                    self.generated_accounts.append(response.get("id"))

            while self.test_status.get_status():
                start_time = time.time()

                tasks = []
                for _ in range(transactions_per_second):  # Увеличьте количество создаваемых задач в два раза
                    if len(self.generated_accounts) < 2:
                        break
                    sender = random.choice(self.generated_accounts)
                    receiver = random.choice([user for user in self.generated_accounts if user != sender])
                    transaction_data = {
                        "sender_account": sender,
                        "receiver_account": receiver,
                        "amount": random.randint(10, 100000),
                        "type": "transfer"
                    }
                    tasks.append(self.create_task(semaphore, session, transaction_data))

                await asyncio.gather(*tasks)

                elapsed_time = time.time() - start_time
                wait_time = max(0.0, 1.0 - elapsed_time)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

    async def create_task(self, semaphore, session, data, method='POST'):
        async with semaphore:
            if method == 'POST':
                return await self.send_request(session, "transactions", data)
            elif method == 'DELETE':
                user_id = data['id']
                logger.info(f"Sending DELETE request for user {user_id}...")
                return await self.send_request(session, f"users/{user_id}", {}, method='DELETE')

    async def stop(self):
        logger.info("Stopping test and attempting to delete generated users...")

        semaphore = asyncio.Semaphore(10000)
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0)) as session:
            tasks = []
            for user_id in self.generated_users:
                logger.info(f"Attempting to delete user {user_id}...")
                tasks.append(self.create_task(semaphore, session, {"id": user_id}, method='DELETE'))
            await asyncio.gather(*tasks)

        self.generated_users.clear()
        self.generated_accounts.clear()

        self.test_status.set_status(False)
        logger.info("Test stopped and users deleted.")
