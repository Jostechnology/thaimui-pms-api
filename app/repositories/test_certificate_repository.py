from app.con_sqlalchemy import QCCertification
from app.app import db

def create_test_certificate(test_certificate):
    try:
        db.session.add(test_certificate)
        return test_certificate
    except Exception as e:
        raise e