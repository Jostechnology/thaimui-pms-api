from app.con_sqlalchemy import QCWorkOrder, QCWorkOrderStatus, WorkOrder, WorkOrderStatus
from app.ma_sqlalchemy import QCWorkOrderSchema
from app.repositories import qc_work_order_repository
from app.app import db

# สถานะที่อนุญาตให้สร้างใบสั่งเทส QC ได้
_ALLOWED_STATUSES_FOR_QC = {WorkOrderStatus.WAIT_TEST, WorkOrderStatus.TESTING}


def get_all_qc_work_orders(data):
    try:
        page = data.get("page", 1)
        limit = data.get("limit", 10)
        search = data.get("search", "")
        result = qc_work_order_repository.get_all_qc_work_orders(page, limit, search)
        return {
            "items": QCWorkOrderSchema(many=True).dump(result["items"]),
            "total_pages": result["total_pages"],
        }
    except Exception:
        raise


def get_qc_work_order_by_id(qc_work_order_id):
    try:
        qc = qc_work_order_repository.get_qc_work_order_by_id(qc_work_order_id)
        return QCWorkOrderSchema().dump(qc)
    except Exception:
        raise


def create_qc_work_order(data):
    try:
        work_order_id = data.get("work_order_id")
        
        if not work_order_id and data.get("donEntry"):
            work_order = db.session.query(WorkOrder).filter_by(doc_entry=data.get("donEntry")).first()
            if work_order:
                work_order_id = work_order.work_order_id
            else:
                raise Exception(f"ไม่พบ Work Order สำหรับ Sales Order (doc_entry: {data.get('donEntry')})")
                
        if not work_order_id:
            raise Exception("กรุณาระบุ Work Order หรือ Sales Order")

        # ตรวจสอบ status ของ Work Order ว่าพร้อมสร้างใบสั่งเทสหรือไม่
        work_order_obj = db.session.query(WorkOrder).filter_by(work_order_id=work_order_id).first()
        if not work_order_obj:
            raise Exception(f"ไม่พบ Work Order ID: {work_order_id}")
        if work_order_obj.status not in _ALLOWED_STATUSES_FOR_QC:
            allowed_labels = ", ".join([s.value for s in _ALLOWED_STATUSES_FOR_QC])
            raise Exception(
                f"ไม่สามารถสร้างใบสั่งเทสได้ เนื่องจาก Work Order มีสถานะ '{work_order_obj.status.value}' "
                f"(ต้องเป็น {allowed_labels} เท่านั้น)"
            )

        existing_qc = db.session.query(QCWorkOrder).filter_by(work_order_id=work_order_id).first()
        if existing_qc:
            raise Exception("Work Order นี้มีเอกสาร QC อยู่แล้ว ไม่สามารถสร้างเพิ่มได้")

        qc = QCWorkOrder(
            work_order_id=work_order_id,
            qc_status=QCWorkOrderStatus.PENDING,
            qc_date=data.get("qc_date"),
            qc_by=data.get("qc_by"),
            remark=data.get("remark"),
            form_data=data,
        )
        qc = qc_work_order_repository.create_qc_work_order(qc)
        db.session.commit()
        return QCWorkOrderSchema().dump(qc)
    except Exception as e:
        db.session.rollback()
        raise Exception(str(e))


def _to_qc_status(val):
    if val is None:
        return None
    if isinstance(val, QCWorkOrderStatus):
        return val
    if isinstance(val, str):
        try:
            return QCWorkOrderStatus[val.strip().upper()]
        except KeyError:
            pass
    raise ValueError(f"Invalid QC status: {val}")


def update_qc_work_order(qc_work_order_id, data):
    try:
        qc = qc_work_order_repository.get_qc_work_order_by_id(qc_work_order_id)

        if "qc_status" in data:
            qc.qc_status = _to_qc_status(data.get("qc_status"))
        if "qc_date" in data:
            qc.qc_date = data.get("qc_date")
        if "qc_by" in data:
            qc.qc_by = data.get("qc_by")
        if "remark" in data:
            qc.remark = data.get("remark")
            
        qc.form_data = data

        db.session.commit()
        return QCWorkOrderSchema().dump(qc)
    except Exception:
        db.session.rollback()
        raise


def delete_qc_work_order(qc_work_order_id):
    try:
        qc_work_order_repository.delete_qc_work_order(qc_work_order_id)
        db.session.commit()
        return {"message": f"ลบ QC Work Order ID {qc_work_order_id} สำเร็จ"}
    except Exception:
        db.session.rollback()
        raise
