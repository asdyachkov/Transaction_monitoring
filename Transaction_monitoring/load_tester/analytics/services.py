import logging
from .models import AnalyticsRepository

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        self.repo = AnalyticsRepository()
        logger.info("AnalyticsService initialized.")

    def log_request(self, endpoint, request_data, status, response_time, error=None):
        logger.info(f"Logging request to {endpoint}: status={status}, response_time={response_time:.2f}s, error={error}")
        self.repo.log_request(endpoint, request_data, status, response_time, error)

    def get_analytics_data(self):
        logger.info("Fetching analytics data.")
        return self.repo.get_analytics()

