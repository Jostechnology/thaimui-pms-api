from app.con_sqlalchemy import CertificationStatus, QCCertification, QCCheckItem, SalesOrder
from app.ma_sqlalchemy import QCCertificateSchema, QCCertificateSchemaDetail
from app.repositories import test_certificate_repository
from app.app import db
import datetime
from app.exception import NotFoundError

def create_test_certificate(data):
    try:
        doc_entry = data.get("sales_order_doc_entry")

        sales_order = db.session.query(SalesOrder).filter(SalesOrder.doc_entry == doc_entry).first()
        if not sales_order:
            raise Exception("ไม่พบ Sales Order ที่ระบุ")

        status_map = {"acceptable": CertificationStatus.PASSED, "not_acceptable": CertificationStatus.FAILED}

        cert_no = data.get("certification_name")
        if not cert_no or cert_no == "TC-AUTO-GEN":
            now_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            cert_no = f"TC-{now_str}"

        cert = QCCertification(
            doc_entry=doc_entry,
            certification_number=cert_no,
            certification_date=datetime.datetime.now(),
            certification_status=status_map.get(data.get("certification_status"), CertificationStatus.PASSED),
            remark=data.get("remark"),
            standard_reference=data.get("standard_ref"),
            test_method=data.get("test_method"),
        )

        for it in data.get("items", []):
            test_no = it.get("test_no")
            if not test_no or test_no == "[Auto Gen]":
                test_no = f"{cert_no}-{it.get('item_no')}"

            item = QCCheckItem(
                sales_item_id=it.get("sales_item_id"),
                item_no=it.get("item_no"),
                description=it.get("description"),
                test_number=test_no,
                ref_number=it.get("ref_no"),
                wll=float(it.get("wll")) if it.get("wll") else None,
                load_test=float(it.get("load_test")) if it.get("load_test") else None,
            )
            cert.check_items.append(item)

        test_certificate_repository.create_test_certificate(cert)
        db.session.commit()

        return QCCertificateSchema().dump(cert)

    except Exception as e:
        db.session.rollback()
        raise e

def get_test_certificate_list(search=""):
    try:
        items = test_certificate_repository.get_test_certificate_list(search)
        return QCCertificateSchema(many=True).dump(items)
    except Exception:
        raise

def get_test_certificate_by_id(qc_certification_id):
    try:
        item = test_certificate_repository.get_test_certificate_by_id(qc_certification_id)
        if not item:
            raise NotFoundError("Test certificate not found")
        return QCCertificateSchemaDetail().dump(item)
    except Exception:
        raise

def update_test_certificate(qc_certification_id, data):

    try:
        cert = test_certificate_repository.get_test_certificate_by_id(qc_certification_id)
        if not cert:
            raise NotFoundError("Test certificate not found")

        status_map = {"acceptable": CertificationStatus.PASSED, "not_acceptable": CertificationStatus.FAILED}

        if "certification_name" in data:
            cert.certification_number = data["certification_name"]

        if "certification_status" in data:
            cert.certification_status = status_map.get(data.get("certification_status"), CertificationStatus.PASSED)

        if "remark" in data:
            cert.remark = data["remark"]

        if "standard_ref" in data:
            cert.standard_reference = data["standard_ref"]

        if "test_method" in data:
            cert.test_method = data["test_method"]

        if "items" in data:
            cert.check_items.clear()

            for it in data.get("items", []):
                test_no = it.get("test_no")
                if not test_no or test_no == "[Auto Gen]":
                    test_no = f"{cert.certification_number}-{it.get('item_no')}"

                item = QCCheckItem(
                    sales_item_id=it.get("sales_item_id"),
                    item_no=it.get("item_no"),
                    description=it.get("description"),
                    test_number=test_no,
                    ref_number=it.get("ref_no"),
                    wll=float(it.get("wll")) if it.get("wll") else None,
                    load_test=float(it.get("load_test")) if it.get("load_test") else None,
                )
                cert.check_items.append(item)

        test_certificate_repository.update_test_certificate(cert)
        db.session.commit()

        return QCCertificateSchema().dump(cert)
    except Exception as e:
        db.session.rollback()
        raise Exception(str(e))