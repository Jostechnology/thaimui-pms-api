from dotenv import load_dotenv
import os

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

connectdb = os.getenv('connection_string')
JWT_SECRET_KEY= os.getenv("JWT_SECRET_KEY")
CENTER_ACCESS_KEY = os.getenv("CENTER_ACCESS_KEY")
CENTER_URL = os.getenv("CENTER_URL")
DOCUMENT_GENERATOR_URL = os.getenv("DOCUMENT_GENERATOR_URL")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"