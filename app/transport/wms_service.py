import requests
import logging

logger = logging.getLogger(__name__)


class WMSService:
    _instance = None

    def __new__(cls, base_url: str = None, timeout: int = 30):
        if cls._instance is None:
            if not base_url:
                raise ValueError("WMSService must be initialized with base_url")

            cls._instance = super(WMSService, cls).__new__(cls)

            cls._instance.base_url = base_url.rstrip("/")
            cls._instance.timeout = timeout

            cls._instance.session = requests.Session()
            cls._instance.session.headers.update({
                "Content-Type": "application/json",
            })

        return cls._instance

    def create_pickup_from_pms(self, picking_request_code : str, doc_entry: int, order_items: list) -> dict:
        """
        POST /api/create_pickup_from_pms

        order_items: list of dicts with keys order_line_num, quantity, purpose (optional)

        Returns the parsed JSON response dict.
        Raises requests.RequestException on network failure.
        """
        url = f"{self.base_url}/api/create_pickup_from_pms"
        payload = {
            "order_list": [doc_entry],
            "order_items": order_items,
            "pms_reference" : picking_request_code
        }
        logger.info(f"WMS create_pickup_from_pms: doc_entry={doc_entry}, items={len(order_items)}")
        response = self.session.post(url=url, json=payload, timeout=self.timeout)
        return response.json()
