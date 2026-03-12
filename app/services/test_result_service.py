from app.con_sqlalchemy import QCWorkOrder, QCWorkOrderStatus, TestResult, TestResultItem, TestResultStatus, SalesItemTransactionType
from app.ma_sqlalchemy import TestResultSchema
from app.repositories import test_result_repository
from app.app import db
from app.exception import NotFoundError
from app.services import transaction_service


def _resolve_status(val):
    if not val:
        return TestResultStatus.PASSED
    if isinstance(val, TestResultStatus):
        return val
    try:
        return TestResultStatus[val.strip().upper()]
    except KeyError:
        return TestResultStatus.PASSED


def create_test_result(qc_work_order_id, data):
    try:
        qc = db.session.query(QCWorkOrder).filter(QCWorkOrder.qc_work_order_id == qc_work_order_id).first()
        if not qc:
            raise NotFoundError("ไม่พบ QC Work Order ที่ระบุ")

        test_result = TestResult(
            qc_work_order_id=qc_work_order_id,
            test_date=data.get("test_date"),
            tested_by=data.get("tested_by"),
            test_method=data.get("test_method"),
            standard_reference=data.get("standard_reference"),
            overall_status=_resolve_status(data.get("overall_status")),
            remark=data.get("remark"),
        )

        for it in data.get("items", []):
            item = TestResultItem(
                unit_number=it.get("unit_number"),
                serial_no=it.get("serial_no"),
                wll_measured=float(it.get("wll_measured")) if it.get("wll_measured") is not None else None,
                load_test_value=float(it.get("load_test_value")) if it.get("load_test_value") is not None else None,
                description=it.get("description"),
                result=_resolve_status(it.get("result")),
                remark=it.get("remark"),
            )
            test_result.test_result_items.append(item)

        test_result_repository.create_test_result(test_result)
        db.session.flush()

        # Sync QCWorkOrder status to this test result
        qc.qc_status = QCWorkOrderStatus.PASSED if test_result.overall_status == TestResultStatus.PASSED else QCWorkOrderStatus.FAILED

        # Track tested quantity when result is PASSED
        if test_result.overall_status == TestResultStatus.PASSED:
            tested_qty = len(test_result.test_result_items)
            if tested_qty > 0:
                transaction_service.create_sales_item_transaction(
                    qc.sales_item, test_result, SalesItemTransactionType.TESTED, tested_qty
                )

        db.session.commit()
        return TestResultSchema().dump(test_result)
    except Exception as e:
        db.session.rollback()
        raise Exception(str(e))


def get_test_results_by_qc_work_order(qc_work_order_id):
    try:
        results = test_result_repository.get_test_results_by_qc_work_order(qc_work_order_id)
        return TestResultSchema(many=True).dump(results)
    except Exception:
        raise


def get_test_result_by_id(test_result_id):
    try:
        result = test_result_repository.get_test_result_by_id(test_result_id)
        if not result:
            raise NotFoundError("ไม่พบ Test Result ที่ระบุ")
        return TestResultSchema().dump(result)
    except Exception:
        raise


def update_test_result(test_result_id, data):
    try:
        test_result = test_result_repository.get_test_result_by_id(test_result_id)
        if not test_result:
            raise NotFoundError("ไม่พบ Test Result ที่ระบุ")

        prev_status = test_result.overall_status

        if "test_date" in data:
            test_result.test_date = data["test_date"]
        if "tested_by" in data:
            test_result.tested_by = data["tested_by"]
        if "test_method" in data:
            test_result.test_method = data["test_method"]
        if "standard_reference" in data:
            test_result.standard_reference = data["standard_reference"]
        if "overall_status" in data:
            test_result.overall_status = _resolve_status(data["overall_status"])
        if "remark" in data:
            test_result.remark = data["remark"]

        if "items" in data:
            test_result.test_result_items.clear()
            for it in data["items"]:
                item = TestResultItem(
                    unit_number=it.get("unit_number"),
                    serial_no=it.get("serial_no"),
                    wll_measured=float(it.get("wll_measured")) if it.get("wll_measured") is not None else None,
                    load_test_value=float(it.get("load_test_value")) if it.get("load_test_value") is not None else None,
                    description=it.get("description"),
                    result=_resolve_status(it.get("result")),
                    remark=it.get("remark"),
                )
                test_result.test_result_items.append(item)

        test_result_repository.update_test_result(test_result)
        db.session.flush()

        # Sync QCWorkOrder status to this test result
        test_result.qc_work_order.qc_status = QCWorkOrderStatus.PASSED if test_result.overall_status == TestResultStatus.PASSED else QCWorkOrderStatus.FAILED

        # Create TESTED transaction only when status transitions to PASSED
        if prev_status != TestResultStatus.PASSED and test_result.overall_status == TestResultStatus.PASSED:
            tested_qty = len(test_result.test_result_items)
            if tested_qty > 0:
                transaction_service.create_sales_item_transaction(
                    test_result.qc_work_order.sales_item,
                    test_result,
                    SalesItemTransactionType.TESTED,
                    tested_qty,
                )

        db.session.commit()
        return TestResultSchema().dump(test_result)
    except Exception as e:
        db.session.rollback()
        raise Exception(str(e))


def get_test_results_by_doc_entry(doc_entry):
    try:
        results = test_result_repository.get_test_results_by_doc_entry(doc_entry)
        return TestResultSchema(many=True).dump(results)
    except Exception:
        raise


def delete_test_result(test_result_id):
    try:
        test_result = test_result_repository.get_test_result_by_id(test_result_id)
        if not test_result:
            raise NotFoundError("ไม่พบ Test Result ที่ระบุ")
        test_result_repository.delete_test_result(test_result_id)
        db.session.commit()
        return {"message": f"ลบ Test Result ID {test_result_id} สำเร็จ"}
    except Exception as e:
        db.session.rollback()
        raise Exception(str(e))
