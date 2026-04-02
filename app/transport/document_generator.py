import requests
import logging

logger = logging.getLogger(__name__)


class DocumentGeneratorService:
    _instance = None

    def __new__(cls, base_url: str = None, timeout: int = 30):
        if cls._instance is None:
            if not base_url:
                raise ValueError("DocumentGeneratorService must be initialized with base_url")

            cls._instance = super(DocumentGeneratorService, cls).__new__(cls)

            cls._instance.base_url = base_url.rstrip("/")
            cls._instance.timeout = timeout

            cls._instance.session = requests.Session()
            cls._instance.session.headers.update({
                "Content-Type": "application/json",
            })

        return cls._instance

    def generate_document(self, service_source, template, ref_no, data, path=None):
        url = f"{self.base_url}/document_generate"
        print(f"Generating Document : {url}")
        payload = {
            "service_source": service_source,
            "template": template,
            "ref_no": ref_no,
            "data": data,
        }
        if path:
            payload["path"] = path

        try:
            self.session.post(
                url=url,
                json=payload,
                timeout=self.timeout,
            )
        except Exception as e:
            logger.error(f"Document generation request failed for {ref_no}: {e}")
