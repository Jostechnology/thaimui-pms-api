from dotenv import load_dotenv
import os

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

connectdb = os.getenv('connection_string')
JWT_SECRET_KEY= os.getenv("JWT_SECRET_KEY")
CENTER_ACCESS_KEY = os.getenv("CENTER_ACCESS_KEY")
CENTER_URL = os.getenv("CENTER_URL")
DOCUMENT_GENERATOR_URL = os.getenv("DOCUMENT_GENERATOR_URL")