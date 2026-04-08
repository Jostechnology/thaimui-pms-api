import json
import traceback
from flask import g
from app.app import db
from app.config import RABBITMQ_MAX_RETRIES
from app.exception import AppException
from app.messaging import (
    EXCHANGE_DLX, HDR_RETRY_COUNT,
    Q_THAIMUI_PICKING_PICKING, Q_THAIMUI_PICKING_SENT,
    Q_THAIMUI_SALES_ORDER_CREATED,
)
from app.messaging.connection import build_connection
from app.messaging.topology import declare_topology
from app.messaging.handlers import (picking_handler, sales_order_handler)
import pika



class RabbitConsumer:
    def __init__(self, flask_app):
        self.app = flask_app
        self.handlers = {}  # queue_name -> handler_fn(payload)

    def register(self, queue, handler):
        self.handlers[queue] = handler

    def _retry_count(self, properties):
        headers = properties.headers or {}
        return int(headers.get(HDR_RETRY_COUNT, 0))

    def _park(self, channel, method, properties, body):
        """Republish to DLX with a parked routing key so it lands in Q_PARKED."""
        import pika
        parked_rk = "parked." + (method.routing_key or "unknown")
        channel.basic_publish(
            exchange=EXCHANGE_DLX,
            routing_key=parked_rk,
            body=body,
            properties=pika.BasicProperties(
                content_type=properties.content_type,
                delivery_mode=2,
                headers=properties.headers or {},
            ),
        )

    def _make_callback(self, handler):
        def _cb(channel, method, properties, body):
            with self.app.app_context():
                g.username = "system:wms-worker" # ให้ AuditMixin มันบันทึกรายการได้
                try:
                    payload = json.loads(body.decode("utf-8"))
                    handler(payload)
                    db.session.commit()
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                except AppException:
                    db.session.rollback()
                    traceback.print_exc()
                    self._reject_with_retry(channel, method, properties, body)
                except Exception:
                    db.session.rollback()
                    traceback.print_exc()
                    self._reject_with_retry(channel, method, properties, body)
                finally:
                    db.session.remove()
        return _cb

    def _reject_with_retry(self, channel, method, properties, body):
        """
        Nack without requeue. The queue's DLX routes the message to a retry queue
        (TTL'd) which dead-letters back to the events exchange. We count attempts
        via the x-retry-count header and park after MAX_RETRIES.
        """
        attempts = self._retry_count(properties) + 1
        if attempts > RABBITMQ_MAX_RETRIES:
            self._park(channel, method, properties, body)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Republish with incremented header via the retry exchange path — simplest is
        # to nack(requeue=False) and let the queue-level DLX wiring carry it. The
        # attempt count header survives via RabbitMQ's x-death header chain, but we
        # also stamp our own.
        new_headers = dict(properties.headers or {})
        new_headers[HDR_RETRY_COUNT] = attempts
        channel.basic_publish(
            exchange=EXCHANGE_DLX,
            routing_key=method.routing_key,
            body=body,
            properties=pika.BasicProperties(
                content_type=properties.content_type,
                delivery_mode=2,
                headers=new_headers,
            ),
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def start(self):
        connection = build_connection()
        channel = connection.channel()
        declare_topology(channel)
        channel.basic_qos(prefetch_count=8)

        for queue, handler in self.handlers.items():
            channel.basic_consume(queue=queue, on_message_callback=self._make_callback(handler))

        print(f"[worker] consuming queues: {list(self.handlers.keys())}", flush=True)
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
        finally:
            connection.close()


def build_default_consumer(flask_app):
    c = RabbitConsumer(flask_app)
    c.register(Q_THAIMUI_PICKING_PICKING,     picking_handler.handle_status_picking)
    c.register(Q_THAIMUI_PICKING_SENT,        picking_handler.handle_status_sent)
    c.register(Q_THAIMUI_SALES_ORDER_CREATED, sales_order_handler.handle_create_sales_order)
    return c
