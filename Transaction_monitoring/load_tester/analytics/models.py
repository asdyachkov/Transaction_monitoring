from pymongo import MongoClient
from datetime import datetime

from pymongo import MongoClient

client = MongoClient('mongodb://admin:admin@mongodb:27017/', authSource='admin', authMechanism='SCRAM-SHA-256')
db = client['load_testing']


class TestStatus:
    def __init__(self):
        self.client = MongoClient('mongodb://admin:admin@mongodb:27017/', authSource='admin', authMechanism='SCRAM-SHA-256')
        self.db = self.client["load_test_db"]
        self.collection = self.db["test_status"]

    def get_status(self):
        status_doc = self.collection.find_one({"_id": "test_status"})
        if status_doc:
            return status_doc.get("running", False)
        return False

    def set_status(self, running: bool):
        self.collection.update_one(
            {"_id": "test_status"},
            {"$set": {"running": running}},
            upsert=True
        )


class AnalyticsRepository:
    def __init__(self):
        self.collection = db['analytics']

    def log_request(self, endpoint, request_data, status, response_time, error=None):
        self.collection.insert_one({
            "endpoint": endpoint,
            "request_data": request_data,
            "status": status,
            "response_time": response_time,
            "timestamp": datetime.utcnow(),
            "error": error
        })

    def get_analytics(self):
        total_requests = self.collection.count_documents({})
        successful_requests = self.collection.count_documents({"status": "success"})
        failed_requests = self.collection.count_documents({"status": {"$ne": "success"}})
        average_response_time = self.collection.aggregate([
            {"$group": {"_id": None, "avgResponseTime": {"$avg": "$response_time"}}}
        ]).next().get("avgResponseTime", 0)

        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        failure_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "average_response_time": round(average_response_time, 2),
            "success_rate": f"{round(success_rate, 2)}%",  # Corrected format
            "failure_rate": f"{round(failure_rate, 2)}%"   # Corrected format
        }
