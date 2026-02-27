from app.con_sqlalchemy import QCCertification, QCCheckItem
from app.app import db
from sqlalchemy import or_

def create_test_certificate(test_certificate):
    try:
        db.session.add(test_certificate)
        return test_certificate
    except Exception as e:
        raise e

def get_test_certificate_list(search=""):
    try:
        query = db.session.query(QCCertification)
        
        if search:
            query = query.outerjoin(QCCheckItem).filter(
                or_(
                    QCCertification.certification_number.ilike(f"%{search}%"),
                    QCCertification.remark.ilike(f"%{search}%"),
                    QCCheckItem.description.ilike(f"%{search}%"),
                    QCCheckItem.test_number.ilike(f"%{search}%"),
                    QCCheckItem.ref_number.ilike(f"%{search}%"),
                )
            ).distinct()
            
        return query.order_by(QCCertification.qc_certification_id.desc()).all()
    except Exception:
        raise

def get_test_certificate_by_id(qc_certification_id):
    try:
        query = db.session.query(QCCertification).filter(QCCertification.qc_certification_id == qc_certification_id)
        return query.first()
    except Exception:
        raise