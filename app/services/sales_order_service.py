from app.exception import MissingFieldsError
from app.repositories import material_repository, sales_item_repository, sales_order_repository
from app.extensions import center_service
from app.app import db
from app.services import branch_service, work_order_service, transaction_service
from app.con_sqlalchemy import SalesOrder, SalesItem, MaterialList


def search_sales_order(data, show_unassigned=False, branch_id=None):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        result = sales_order_repository.search_sales_order(page, per_page, search, show_unassigned=show_unassigned, branch_id=branch_id)
        return {"items": result["items"], "total": result["total"], "page": result["page"], "pages": result["pages"]}
    except Exception:
        raise


def assign_branch_to_sales_order(doc_entry, branch_id):
    try:
        sales_order = sales_order_repository.assign_branch(doc_entry, branch_id)
        db.session.commit()
        return sales_order
    except Exception:
        db.session.rollback()
        raise


def get_all_sales_orders(data, show_unassigned=False, branch_id=None):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        result = sales_order_repository.get_all_sales_orders(page, per_page, search, show_unassigned=show_unassigned, branch_id=branch_id)

        items_data = []
        for row in result.items:
            so = row.SalesOrder
            branch = row.Branch if row.Branch else None
            items_data.append({
                "doc_entry": so.doc_entry,
                "doc_num": so.doc_num,
                "card_code": so.card_code,
                "card_name": so.card_name,
                "slp_code": so.slp_code,
                "slp_name": so.slp_name,
                "bpl_code": so.bpl_code,
                "bpl_name": so.bpl_name,
                "group_code": so.group_code,
                "group_name": so.group_name,
                "created_date": so.created_date.strftime("%Y-%m-%d %H:%M:%S") if so.created_date else None,
                "items_total": row.items_total,
                "quantity_to_produce": row.quantity_to_produce,
                "produced_qty": row.produced_qty,
                "qc_count": row.qc_count,
                "qc_passed": row.qc_passed,
                "qc_failed": row.qc_failed,
                "produce_total": row.produce_total,
                "produce_has_workorder": row.produce_has_workorder,
                "test_total": row.test_total,
                "test_has_qcworkorder": row.test_has_qcworkorder,
                "status" : so.status.name,
                "branch_code" : branch.branch_code if branch else None,
                "branch_name" : branch.branch_name if branch else None
            })

        return {
            "items": items_data,
            "total": result.total,
            "page": result.page,
            "pages": result.pages,
        }
    except Exception:
        raise

def get_sales_items_from_sales_order(doc_entry):
    try:
        return sales_item_repository.get_sales_items_by_doc_entry(doc_entry)
    except Exception:
        raise

def get_material_list_from_sales_order(doc_entry):
    try:
        return material_repository.get_material_list_from_doc_entry(doc_entry)
    except Exception:
        raise


def get_sales_order_detail(doc_entry, show_unassigned=False, branch_id=None):
    try:
        result, branch = sales_order_repository.get_sales_order_detail(doc_entry, show_unassigned=show_unassigned, branch_id=branch_id)
        items = result.sales_items
        
        materials = []
        for i in items:
            materials.extend(i.material_list)
        return result, items, materials, branch
    except Exception:
        db.session.rollback()
        raise

def get_test_sales_order():
    try:
        response = center_service.request(
            method="POST",
            endpoint="/api/ORDR/get_test_quick",
        )
        data = response["json"]
        print(data)
        for so in data:  
            create_sales_order(so)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    
def create_sales_order_routine(data):
    try:
        for so in data:  
            create_sales_order(so)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise    

def create_sales_order(data):
    try:
        branch = branch_service.get_branch_by_code(data.get("pms_branch_code", None))
        sales_order = SalesOrder(
            doc_entry = data.get("doc_entry"),
            doc_num = data.get("doc_num"),
            card_code = data.get("card_code"),
            card_name = data.get("card_name"),
            slp_code = data.get("slp_code"),
            slp_name = data.get("slp_name"),
            bpl_code = data.get("bpl_code"),
            bpl_name = data.get("bpl_name"),
            group_code = data.get("group_code"),
            group_name = data.get("group_name"),
            branch_id = branch.branch_id
        )

        for item in data.get("sales_item_list", []):
            sales_item = SalesItem(
                item_code=item.get("item_code"),
                item_name=item.get("item_name"),
                quantity=item.get("quantity"),
                order_line_num=item.get("order_line_num"),
                unit_name=item.get("unit_name", "Piece"),
                unit_id=item.get("unit_id"),
                unit_price=item.get("unit_price"),
                cost_price=item.get("cost_price"),
                doc_num=item.get("doc_num"),
                doc_entry=item.get("doc_entry"),
                center_sales_item_id=item.get("sales_item_id"),
                produce=item.get("produce", False),
                test=item.get("test", False),
                item_group=item.get("item_group"),
                branch_id = branch.branch_id
            )
            sales_order.sales_items.append(sales_item)

            for mat in item.get("material_list", []):
                if mat.get("order_line_num") is None:
                    raise MissingFieldsError("ไม่พบ order_line_num")
                material_list = MaterialList(
                    item_code=mat.get("item_code"),
                    item_name=mat.get("item_name"),
                    item_description=mat.get("item_description"),
                    quantity=mat.get("quantity"),
                    unit_name=mat.get("unit_name", "Piece"),
                    unit_id=mat.get("unit_id", 0),
                    unit_price=mat.get("unit_price"),
                    cost_price=mat.get("cost_price"),
                    item_group=mat.get("item_group"),
                    branch_id = branch.branch_id,
                    order_line_num = mat.get("order_line_num")
                )
                transaction_service.create_init_material_transaction(material_list, "INIT")
                sales_item.material_list.append(material_list)

        db.session.add(sales_order)
        return sales_order
    except Exception:
        db.session.rollback()
        raise