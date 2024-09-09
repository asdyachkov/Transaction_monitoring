import logging
from django.utils.deprecation import MiddlewareMixin
import time
from pymongo import MongoClient

logger = logging.getLogger(__name__)


class LogTokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("Authorization Header:", request.META.get('HTTP_AUTHORIZATION', 'No token'))
        response = self.get_response(request)
        return response


class UserActionLoggingMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        self.client = MongoClient('mongodb://admin:admin@mongodb:27017/', authSource='admin', authMechanism='SCRAM-SHA-256')
        self.db = self.client['transaction_monitoring']
        self.collection = self.db['user_logs']

    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):
        duration = time.time() - request.start_time
        log_data = {
            "user_id": request.user.id if request.user.is_authenticated else None,
            "path": request.path,
            "method": request.method,
            "status_code": response.status_code,
            "execution_time": duration,
            "ip_address": request.META.get('REMOTE_ADDR'),
            "user_agent": request.META.get('HTTP_USER_AGENT'),
            "timestamp": time.time(),
        }

        self.collection.insert_one(log_data)

        return response


class IPMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
