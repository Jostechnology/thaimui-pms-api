from app.con_sqlalchemy import CertificationStatus, QCCertification, QCCheckItem
from app.ma_sqlalchemy import QCCertificateSchema
from app.repositories import test_certificate_repository
from app.app import db
import datetime
from app.exception import NotFoundError

def create_test_certificate(data):
    try:
        wo_id = data.get("qc_work_order_id")
        from app.con_sqlalchemy import QCWorkOrder
        # changed code: query only the id to avoid selecting missing columns
        exists = db.session.query(QCWorkOrder.qc_work_order_id).filter(QCWorkOrder.qc_work_order_id == wo_id).first()
        if not exists:
            raise Exception("ไม่พบ QC work order ที่ระบุ")
        
        status_map = {"acceptable": CertificationStatus.PASSED, "not_acceptable": CertificationStatus.FAILED}
        
        # 🌟 1. ดักจับและสร้างเลข Certificate No. (Auto Gen) จริงๆ ตรงนี้
        cert_no = data.get("certification_name")
        if not cert_no or cert_no == "TC-AUTO-GEN":
            # ตัวอย่างการสร้างเลข รันตามเวลา เช่น TC-20260225-143000 (หรือจะเปลี่ยนเป็นฟังก์ชันดึงเลขล่าสุดจาก DB ก็ได้)
            now_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            cert_no = f"TC-{now_str}"

        # 2. นำเลขที่ได้มาใส่ใน certification_number
        cert = QCCertification(
            qc_work_order_id=data["qc_work_order_id"],
            certification_number=cert_no, # 🌟 ใช้ตัวแปรที่เราดักค่าไว้
            certification_date=data.get("certification_date"),
            certification_status=status_map.get(data.get("certification_status"), CertificationStatus.PASSED),
            remark=data.get("remark"),
            standard_reference=data.get("standard_ref"),
            test_method=data.get("test_method"),
        )
        
        # 3. วนลูป Items
        for it in data.get("items", []):
            
            test_no = it.get("test_no")
            if test_no == "[Auto Gen]":
                # 🌟 ใช้ cert_no ตัวใหม่มาต่อท้ายด้วย Item No (เช่น TC-20260225-143000-01)
                test_no = f"{cert_no}-{it.get('item_no')}"

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