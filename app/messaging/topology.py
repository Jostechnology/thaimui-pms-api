from app.config import RABBITMQ_RETRY_TTL_MS
from app.messaging import (
    EXCHANGE_SALES_ORDER, EXCHANGE_PICKING, EXCHANGE_DLX,
    Q_THAIMUI_SALES_ORDER_CREATED,
    Q_THAIMUI_PICKING_PICKING, Q_THAIMUI_PICKING_SENT,
    Q_PARKED,
    RK_SALES_ORDER_CREATED,
    RK_PICKING_PICKING, RK_PICKING_SENT,
)


# Every consumer queue this service owns. Add a new entry to wire up a new queue.
#   queue       — queue name
#   exchange    — domain exchange the queue listens on
#   routing_key — the event it cares about
CONSUMER_QUEUES = [
    (Q_THAIMUI_PICKING_PICKING,     EXCHANGE_PICKING,     RK_PICKING_PICKING),
    (Q_THAIMUI_PICKING_SENT,        EXCHANGE_PICKING,     RK_PICKING_SENT),
    (Q_THAIMUI_SALES_ORDER_CREATED, EXCHANGE_SALES_ORDER, RK_SALES_ORDER_CREATED),
]


def declare_topology(channel):
    """Declare all exchanges, queues, and bindings idempotently."""
    # Domain exchanges + internal DLX
    for ex in (EXCHANGE_SALES_ORDER, EXCHANGE_PICKING, EXCHANGE_DLX):
        channel.exchange_declare(ex, exchange_type="topic", durable=True)

    # Main consumer queues — dead-letter to DLX on nack
    consumer_args = {"x-dead-letter-exchange": EXCHANGE_DLX}
    for queue, exchange, routing_key in CONSUMER_QUEUES:
        channel.queue_declare(queue, durable=True, arguments=consumer_args)
        channel.queue_bind(queue, exchange, routing_key=routing_key)

    # Retry queues — TTL'd, then dead-letter back to the queue's original exchange.
    # Each retry queue must point at its OWN source exchange so the retried message
    # ends up in the right consumer queue, not in some other domain.
    for queue, exchange, routing_key in CONSUMER_QUEUES:
        retry_args = {
            "x-dead-letter-exchange": exchange,
            "x-message-ttl": RABBITMQ_RETRY_TTL_MS,
        }
        retry_q = f"{queue}.retry"
        channel.queue_declare(retry_q, durable=True, arguments=retry_args)
        channel.queue_bind(retry_q, EXCHANGE_DLX, routing_key=routing_key)

    # Park queue — final destination for poison messages from any domain.
    # Consumer publishes failed messages to DLX with rk "parked.<original_rk>".
    channel.queue_declare(Q_PARKED, durable=True)
    channel.queue_bind(Q_PARKED, EXCHANGE_DLX, routing_key="parked.#")
