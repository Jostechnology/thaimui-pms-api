
from app.transport.send_request import CenterService

center_service = None


def init_center_service(CENTER_ACCESS_KEY, CENTER_URL):
    global center_service

    center_service = CenterService(
        base_url=CENTER_URL,
        token=CENTER_ACCESS_KEY
    )
