# RabbitMQ topology constants — kept in sync with sap-center/app/messaging/messaging.go
#
# Topology shape: domain-based.
#   - One topic exchange per business domain (sales_order, picking, ...)
#   - Routing keys are past-tense events: "<domain>.<event>"
#   - Queues are named "<consumer>.<domain>.<event>"
#   - Any service that wants to react to an event declares its own queue and
#     binds it to (exchange, routing_key). One publish, many consumers.

# Domain exchanges
EXCHANGE_SALES_ORDER = "thaimui.sales_order"
EXCHANGE_PICKING     = "thaimui.picking"

# Internal-only: dead letter routing for failed consumer messages
EXCHANGE_DLX = "thaimui.dlx"

# Routing keys (past-tense events)
RK_SALES_ORDER_CREATED = "sales_order.created"

RK_PICKING_REQUESTED = "picking.requested"  # we → WMS
RK_PICKING_PICKING   = "picking.picking"    # WMS → us
RK_PICKING_SENT      = "picking.sent"       # WMS → us
RK_PICKING_RECEIVED  = "picking.received"   # we → WMS (and any internal listener)

# Consumer queues — naming: <consumer>.<domain>.<event>
Q_THAIMUI_SALES_ORDER_CREATED = "thaimui.sales_order.created"
Q_THAIMUI_PICKING_PICKING     = "thaimui.picking.picking"
Q_THAIMUI_PICKING_SENT        = "thaimui.picking.sent"

# Park queue — final destination for poison messages across all domains
Q_PARKED = "thaimui.parked"

# Header used to track delivery attempts for bounded retries
HDR_RETRY_COUNT = "x-retry-count"
