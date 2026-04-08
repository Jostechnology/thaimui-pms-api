import pika
from app.config import RABBITMQ_URL


def build_connection():
    """Return a new blocking connection. One per process."""
    if not RABBITMQ_URL:
        raise RuntimeError("RABBITMQ_URL is not configured")
    params = pika.URLParameters(RABBITMQ_URL)
    params.heartbeat = 60
    params.blocked_connection_timeout = 30
    return pika.BlockingConnection(params)
