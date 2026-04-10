from app.con_sqlalchemy import QCWorkOrder, QCForm, QCItem, SalesItem
from app.repositories import qc_work_order_repository, sales_item_repository
from app.app import db
from app.services import sales_item_service, sales_order_service, transaction_service
from app.exception import ValidationError

def get_all_qc_work_orders(data):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        filter = data.get("filter", None)
        result = qc_work_order_repository.get_all_qc_work_orders(page, per_page, search, filter)
        return {"items": result["items"], "total": result["total"], "page": result["page"], "pages": result["pages"]}
    except Exception:
        raise


def get_qc_work_order_by_id(qc_work_order_id):
    try:
        qc = qc_work_order_repository.get_qc_work_order_by_id(qc_work_order_id)
        return qc
    except Exception:
        raise


def _build_qc_form(qc_work_order_id, data):
    return QCForm(
        qc_work_order_id=qc_work_order_id,
        std_ptt=data.get("ptt", False),
        std_chevron=data.get("chevron", False),
        std_valeur=data.get("valeur", False),
        std_ophir=data.get("ophir", False),
        std_three_spec=data.get("threeSpec", False),
        std_others=data.get("standardOthers", False),
        std_others_text=data.get("standardOthersText"),
        cert_inhouse=data.get("inHouse", False),
        cert_third_party=data.get("thirdParty", False),
        cert_ndt=data.get("ndt", False),
        cert_others=data.get("testingOthers", False),
        cert_others_text=data.get("testingOthersText"),
        serial_tag=data.get("serialTag", False),
        serial_imprint=data.get("serialImprint", False),
        serial_continue=data.get("continueSerial", False),
        serial_others=data.get("serialOthers", False),
        serial_others_text=data.get("serialOthersText"),
        general_remark=data.get("generalRemark"),
        details=data.get("details"),
        customer_receipt_number=data.get("customerReceiptNumber"),
    )


def _build_qc_items(qc_work_order_id, items_data):
    items = []
    for idx, item in enumerate(items_data or []):
        items.append(QCItem(
            qc_work_order_id=qc_work_order_id,
            item_order=idx + 1,
            item_code=item.get("code"),
            description=item.get("description"),
            wll=item.get("wll"),
            quantity=str(item.get("quantity", "")),
            serial_no=item.get("serialNo"),
            item_remark=item.get("remark"),
        ))
    return items


def generate_qc_work_order_code(sales_item, qc_work_order_id):
    sales_item_order = sales_item_repository.get_sales_item_order_in_sales_order(
        sales_item.sales_item_id, sales_item.doc_entry
    )
    qc_order = qc_work_order_repository.get_qc_work_order_order_in_sales_item(
        qc_work_order_id, sales_item.sales_item_id
    )
    return f"{sales_item.doc_num}-{sales_item_order}-{qc_order}"


def create_qc_work_order(data):
    try:
        sales_item_id = data.get("salesItemId") or data.get("sales_item_id")
        if not sales_item_id:
            raise Exception("กรุณาระบุ Sales Item")

        sales_item = sales_item_service.get_sales_item_by_id(sales_item_id)
        if not sales_item:
            raise Exception(f"ไม่พบ Sales Item ID: {sales_item_id}")

        material_usage_data = data.get("items", [])
        qc_quantity = data.get("salesItemQuantity", 1)
        
        planned_qty = sales_item.quantity
        existing_qc_qty = sum(qc.quantity for qc in sales_item.qc_work_orders)                                                                
        if existing_qc_qty + qc_quantity > planned_qty:              
            raise ValidationError(f"จำนวน QC รวม ({existing_qc_qty + qc_quantity}) เกินจำนวนที่วางแผนผลิต ({planned_qty})")      
                
        material_in_sales_order = sales_order_service.get_material_list_from_sales_order(sales_item.doc_entry)

        material_map = {m.material_list_id: m for m in material_in_sales_order}

        qc = QCWorkOrder(
            sales_item_id=sales_item_id,
            qc_date=data.get("qc_date"),
            qc_by=data.get("qc_by"),
            quantity=qc_quantity,
            remark=data.get("remark"),
            branch_id=sales_item.branch_id
        )
        qc = qc_work_order_repository.create_qc_work_order(qc)
        db.session.flush()

        qc.qc_work_order_code = generate_qc_work_order_code(sales_item, qc.qc_work_order_id)

        db.session.add(_build_qc_form(qc.qc_work_order_id, data))
        for item in _build_qc_items(qc.qc_work_order_id, data.get("items", [])):
            db.session.add(item)

        # Create MaterialTransaction(REMOVE) for each material consumed
        if material_usage_data:
            for usage in material_usage_data:
                material = material_map[usage.get("material_list_id")]
                transaction_service.create_material_transaction(
                    material, qc.qc_work_order_id, "REMOVE", int(usage.get("quantity"))
                )

        db.session.commit()
        db.session.refresh(qc)
        return qc
    except Exception as e:
        db.session.rollback()
        raise Exception(str(e))


def update_qc_work_order(qc_work_order_id, data):
    try:
        qc = qc_work_order_repository.get_qc_work_order_by_id(qc_work_order_id)

        if "qc_date" in data:
            qc.qc_date = data.get("qc_date")
        if "qc_by" in data:
            qc.qc_by = data.get("qc_by")
        print(data.get("quantity"))
        if "quantity" in data:
            qc.quantity = data.get("quantity")
        if "remark" in data:
            qc.remark = data.get("remark")

        if qc.qc_form:
            form = qc.qc_form
            form.std_ptt            = data.get("ptt", form.std_ptt)
            form.std_chevron        = data.get("chevron", form.std_chevron)
            form.std_valeur         = data.get("valeur", form.std_valeur)
            form.std_ophir          = data.get("ophir", form.std_ophir)
            form.std_three_spec     = data.get("threeSpec", form.std_three_spec)
            form.std_others         = data.get("standardOthers", form.std_others)
            form.std_others_text    = data.get("standardOthersText", form.std_others_text)
            form.cert_inhouse       = data.get("inHouse", form.cert_inhouse)
            form.cert_third_party   = data.get("thirdParty", form.cert_third_party)
            form.cert_ndt           = data.get("ndt", form.cert_ndt)
            form.cert_others        = data.get("testingOthers", form.cert_others)
            form.cert_others_text   = data.get("testingOthersText", form.cert_others_text)
            form.serial_tag         = data.get("serialTag", form.serial_tag)
            form.serial_imprint     = data.get("serialImprint", form.serial_imprint)
            form.serial_continue    = data.get("continueSerial", form.serial_continue)
            form.serial_others      = data.get("serialOthers", form.serial_others)
            form.serial_others_text = data.get("serialOthersText", form.serial_others_text)
            form.general_remark     = data.get("generalRemark", form.general_remark)
            form.details            = data.get("details", form.details)
            form.customer_receipt_number = data.get("customerReceiptNumber", form.customer_receipt_number)
        else:
            db.session.add(_build_qc_form(qc_work_order_id, data))

        if "items" in data:
            for old_item in qc.qc_items:
                db.session.delete(old_item)
            db.session.flush()
            for item in _build_qc_items(qc_work_order_id, data.get("items", [])):
                db.session.add(item)

        db.session.commit()
        db.session.refresh(qc)
        return qc
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

def search_qc_work_orders(data):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        result = qc_work_order_repository.search_qc_work_orders(page, per_page, search)
        return {"items": result["items"], "total": result["total"], "page": result["page"], "pages": result["pages"]}
    except Exception:
        raise