import json
import traceback
import pika

from app.messaging.connection import build_connection
from app.messaging.topology import declare_topology

# Process-local connection/channel. Lazily created.
_connection = None
_channel = None


def _get_channel():
    global _connection, _channel
    if _connection is None or _connection.is_closed:
        _connection = build_connection()
        _channel = _connection.channel()
        declare_topology(_channel)
    elif _channel is None or _channel.is_closed:
        _channel = _connection.channel()
        declare_topology(_channel)
    return _channel


def publish(exchange, routing_key, payload):
    """
    Publish a JSON payload to a domain exchange. MUST be called AFTER
    db.session.commit() — never before, otherwise a rolled-back transaction
    can still emit events.
    """
    body = json.dumps(payload, default=str).encode("utf-8")
    props = pika.BasicProperties(
        content_type="application/json",
        delivery_mode=2,  # persistent
    )
    try:
        ch = _get_channel()
        ch.basic_publish(exchange=exchange, routing_key=routing_key, body=body, properties=props)
    except Exception:
        # Force reconnect on next call; bubble up so the caller knows.
        global _connection, _channel
        _connection = None
        _channel = None
        traceback.print_exc()
        raise


def publish_safely(exchange, routing_key, payload):
    """Fire-and-forget publish. Logs on failure, never raises."""
    try:
        publish(exchange, routing_key, payload)
    except Exception:
        traceback.print_exc()
        # system log for admin inspection / retry publish
