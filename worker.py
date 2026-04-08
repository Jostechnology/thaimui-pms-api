"""
RabbitMQ worker entrypoint.

Runs in a separate container from Gunicorn. Loads the Flask app the same way
wsgi.py does, then starts the blocking consume loop.

Run locally:
    python worker.py
"""
from app.app import app
from app.messaging.consumer import build_default_consumer


if __name__ == "__main__":
    consumer = build_default_consumer(app)
    consumer.start()
