from app.con_sqlalchemy import CertificationStatus, QCCertification, QCCheckItem # 🌟 อย่าลืม import QCCheckItem
from app.ma_sqlalchemy import QCCertificateSchema
from app.repositories import test_certificate_repository
from app.app import db

def create_test_certificate(data):
    try:
        status_map = {"acceptable": CertificationStatus.PASSED, "not_acceptable": CertificationStatus.FAILED}
        
        cert = QCCertification(
            qc_work_order_id=data["qc_work_order_id"],
            certification_number=data.get("certification_name"),
            certification_date=data.get("certification_date"),
            certification_status=status_map.get(data.get("certification_status"), CertificationStatus.PASSED),
            remark=data.get("remark"),
            standard_reference=data.get("standard_ref"),
            test_method=data.get("test_method"),
        )
        
        for it in data.get("items", []):
            
            test_no = it.get("test_no")
            if test_no == "[Auto Gen]":
                test_no = f"{data.get('certification_name')}-{it.get('item_no')}"

            item = QCCheckItem(
                item_no=it.get("item_no"),                
                description=it.get("description"),         
                test_number=test_no,                      
                ref_number=it.get("ref_no"),
                wll=float(it.get("wll")) if it.get("wll") else None,
                load_test=float(it.get("load_test")) if it.get("load_test") else None
            )
            cert.check_items.append(item)

        test_certificate_repository.create_test_certificate(cert)
        db.session.commit()
        
        return QCCertificateSchema().dump(cert)
        
    except Exception as e:
        db.session.rollback()
        raise Exception(str(e))