
from app.transport.send_request import CenterService
from app.transport.document_generator import DocumentGeneratorService

center_service = None
document_generator_service = None


def init_center_service(CENTER_ACCESS_KEY, CENTER_URL):
    global center_service

    center_service = CenterService(
        base_url=CENTER_URL,
        token=CENTER_ACCESS_KEY
    )


def init_document_generator_service(DOCUMENT_GENERATOR_URL):
    global document_generator_service

    if DOCUMENT_GENERATOR_URL:
        document_generator_service = DocumentGeneratorService(
            base_url=DOCUMENT_GENERATOR_URL,
        )


def init_storage_service(endpoint, access_key, secret_key, bucket, secure=False):
    from app.services import storage_service
    storage_service.init_storage(endpoint, access_key, secret_key, bucket, secure)


def init_cache_service(redis_url: str):
    from app.services import cache_service
    cache_service.init_cache(redis_url)
