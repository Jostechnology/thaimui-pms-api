from app.con_sqlalchemy import QCCertification, QCCheckItem, SalesItem, TestResultItem
from app.app import db
from sqlalchemy import or_
from sqlalchemy.orm import selectinload


def _certificate_options():
    """Eager-load what QCCertificateSchema needs."""
    return [
        selectinload(QCCertification.check_items)
            .selectinload(QCCheckItem.sales_item),
        selectinload(QCCertification.check_items)
            .selectinload(QCCheckItem.test_result_item),
    ]


def create_test_certificate(test_certificate):
    try:
        db.session.add(test_certificate)
        return test_certificate
    except Exception as e:
        raise e

def get_test_certificate_list(page, per_page, search=""):
    try:
        query = db.session.query(QCCertification) #.options(*_certificate_options())

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

        result = query.order_by(QCCertification.qc_certification_id.desc()).paginate(page=page, per_page=per_page, error_out=False)
        return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}
    except Exception:
        raise

def get_test_certificate_by_id(qc_certification_id):
    try:
        return (
            db.session.query(QCCertification)
            .options(*_certificate_options())
            .filter(QCCertification.qc_certification_id == qc_certification_id)
            .first()
        )
    except Exception:
        raise

def update_test_certificate(test_certificate):
    try:
        db.session.flush()
        db.session.refresh(test_certificate)
        return test_certificate
    except Exception:
        raise
