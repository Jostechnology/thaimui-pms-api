from app.con_sqlalchemy import BreakType, ComponentEditRequestStatus, EmployeeStatus, MachineStatus, MaterialTransactionType, QCWorkOrderStatus, RolePermission, SalesOrderStatus, TestResultStatus, TestSessionStatus, UrgencyLevel, WorkOrderStatus, WorkRunStatus, WorkRunTransactionType, SalesItemStatus, WorkRun, TestResultWorkRun, PickingRequestStatus, WorkRunRequiredItem, TestResultRequiredItem, TestResultAssignment, TestResultMachine, TestResultCost, TestResultBreak, TestType, CheckStatus
from app.con_sqlalchemy import ReportRunStatus
from marshmallow import Schema, fields
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


class ReportDefinitionSchema(Schema):
    code = fields.String(dump_only=True)
    name = fields.String()
    description = fields.String(allow_none=True)
    category = fields.String(allow_none=True)
    params_schema_json = fields.Raw()
    supported_formats = fields.List(fields.String())
    definition_version = fields.Integer()


class ReportRunSchema(Schema):
    """List view — no file URLs, no inline JSON payload."""
    run_id = fields.String(dump_only=True)
    definition_code = fields.String()
    definition_version = fields.Integer()
    params_json = fields.Raw()
    requested_by = fields.String(dump_only=True)
    requested_at = fields.DateTime(dump_only=True)
    status = fields.Enum(ReportRunStatus, by_value=True)
    completed_at = fields.DateTime(dump_only=True, allow_none=True)
    row_count = fields.Integer(allow_none=True)
    runtime_ms = fields.Integer(allow_none=True)
    error_message = fields.String(allow_none=True)


class ReportRunDetailSchema(ReportRunSchema):
    """Detail — adds inline JSON and the format→object_key map.
    `file_urls` is computed in the service via storage_service.get_presigned_url."""
    file_object_keys = fields.Raw(allow_none=True)
    file_size_bytes = fields.Integer(allow_none=True)
    result_json = fields.Raw(allow_none=True)
    file_urls = fields.Raw(dump_only=True)


class UserSchema(Schema):
    username = fields.String()

class RoleSchema(Schema):
    role_id = fields.Int()
    role_code = fields.String()
    role_name = fields.String()
    description = fields.String()
    active_flag = fields.Bool()

class BranchSchema(Schema):
    branch_id = fields.Integer()
    branch_code = fields.String()
    branch_name = fields.String()
    created_date = fields.DateTime()
    updated_date = fields.DateTime()
    is_active = fields.Boolean()
    
class GetPermissionSchema(Schema):
    permission_id = fields.Integer()
    permission_code = fields.String()
    description = fields.String()
    module = fields.String()
    method = fields.String()
    module_id = fields.Integer()

class GetRolePremissionSchema(Schema):
    role_id = fields.Integer()
    permission_id = fields.Integer()
    method = fields.String()
    module_id = fields.Integer()

class ModuleSchema(Schema):
    module_id = fields.Integer()
    module_name = fields.String()
    module_code = fields.String()
    parent_id = fields.Integer()
    level = fields.Integer()
    sort_order = fields.Integer()
    permission_list = fields.Method("get_permissions")
    def get_permissions(self, obj):
        return [permission.method for permission in obj.permissions]


class RolePermissionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = RolePermission
        load_instance = True



class ShiftSchema(Schema):
    shift_id = fields.Integer()
    name = fields.String()
    start_time = fields.Time()
    end_time = fields.Time()
    work_days = fields.String()
    ot_multiplier = fields.Float()
    weekend_multiplier = fields.Float()
    holiday_multiplier = fields.Float()
    is_default = fields.Boolean()

class EmployeeShiftSchema(Schema):
    employee_shift_id = fields.Integer()
    employee_id = fields.Integer()
    start_time = fields.Time()
    end_time = fields.Time()
    work_days = fields.String()

class HolidaySchema(Schema):
    holiday_id = fields.Integer()
    holiday_date = fields.Date()
    name = fields.String()
    is_active = fields.Boolean()
    source = fields.String()

class EmployeeSchema(Schema):
    employee_id = fields.Integer()
    employee_first_name = fields.String()
    employee_last_name = fields.String()
    phone_number = fields.String()
    email = fields.String()
    citizen_id = fields.String()
    status = fields.Enum(EmployeeStatus)
    address = fields.String()
    user_id = fields.Integer()
    is_active = fields.Boolean()
    base_salary = fields.Float()
    day_rate = fields.Float()
    ot_hourly_rate = fields.Float()
    photo_url = fields.Method("get_photo_url", dump_only=True)
    shift_override = fields.Nested(EmployeeShiftSchema(), allow_none=True, dump_only=True)

    def get_photo_url(self, obj):
        if not getattr(obj, "photo_key", None):
            return None
        from app.services.storage_service import get_presigned_url
        try:
            return get_presigned_url(obj.photo_key)
        except Exception:
            return None

class EmployeeSalaryHistorySchema(Schema):
    salary_history_id = fields.Integer()
    employee_id = fields.Integer()
    old_base_salary = fields.Float()
    new_base_salary = fields.Float()
    old_day_rate = fields.Float()
    new_day_rate = fields.Float()
    old_ot_hourly_rate = fields.Float()
    new_ot_hourly_rate = fields.Float()
    effective_date = fields.DateTime()
    remark = fields.String()

class MaterialListSchema(Schema):
    material_list_id = fields.Integer()
    center_material_id = fields.Integer()
    sales_item_id = fields.Integer()
    item_code = fields.String()
    item_name = fields.String()
    item_description = fields.String()
    quantity = fields.Float()
    unit_name = fields.String()
    unit_id = fields.Integer()
    remaining_num = fields.Integer(dump_only=True)
    cost_price = fields.Float()
    cost_per_unit = fields.Float(dump_only=True)
    unit_price = fields.Float()
    created_date = fields.DateTime()
    branch_id = fields.Integer(allow_none=True)
    item_group = fields.String()
    order_line_num = fields.Integer()
    
class SalesItemForWorkOrderSchema(Schema):
    sales_item_id = fields.Integer()
    center_sales_item_id = fields.Integer()
    item_code = fields.String()
    quantity = fields.Float()
    order_line_num = fields.Integer(allow_none=True)
    unit_name = fields.String()
    unit_id = fields.Integer()
    item_name = fields.String()
    item_description = fields.String()
    cost_price = fields.Float()
    unit_price = fields.Float()
    doc_num = fields.Int()
    branch_id = fields.Integer(allow_none=True)
    item_group                   = fields.String()

class SalesItemSchemaDetail(SalesItemForWorkOrderSchema):
    material_list = fields.List(fields.Nested(MaterialListSchema()))

    
class WorkRunBreakSchema(Schema):
    break_id = fields.Integer()
    work_run_id = fields.Integer()
    break_start = fields.DateTime()
    break_end = fields.DateTime(allow_none=True)
    break_type = fields.Enum(BreakType)
    remark = fields.String(allow_none=True)

class WorkRunAssignmentSchema(Schema):
    work_run_assignment_id = fields.Integer()
    work_run_id = fields.Integer()
    employee_id = fields.Integer()
    from_time = fields.DateTime()
    to_time = fields.DateTime(allow_none=True)
    employee = fields.Nested(lambda: EmployeeSchema())

class WorkRunCostSchema(Schema):
    """Aggregated cost summary for one WorkRun."""
    cost_id = fields.Integer(dump_only=True)
    work_run_id = fields.Integer(dump_only=True)
    material_cost = fields.Float(allow_none=True)
    depreciation_cost = fields.Float(allow_none=True)
    maintenance_cost = fields.Float(allow_none=True)
    base_labor_cost = fields.Float(allow_none=True)
    day_labor_cost = fields.Float(allow_none=True)
    ot_labor_cost = fields.Float(allow_none=True)
    total_cost = fields.Float(allow_none=True)

class WorkRunMachineCostFieldsSchema(Schema):
    """Machine-level cost fields, now sourced from WorkRunMachine columns."""
    depreciation_per_second = fields.Float()
    depreciation_cost = fields.Float(allow_none=True)
    maintenance_rate_per_second = fields.Float()
    maintenance_cost = fields.Float(allow_none=True)
    total_cost = fields.Method('get_total')

    def get_total(self, obj):
        d = obj.depreciation_cost
        m = obj.maintenance_cost
        if d is None and m is None:
            return None
        return round((d or 0.0) + (m or 0.0), 6)

class WorkRunMachineSchema(Schema):
    work_run_machine_id = fields.Integer()
    work_run_id = fields.Integer()
    machine_id = fields.Integer()
    from_time = fields.DateTime()
    to_time = fields.DateTime(allow_none=True)
    allocated_maintenance_cost = fields.Float(allow_none=True)
    machine = fields.Nested(lambda: MachineSchema())
    cost = fields.Method('get_cost')

    def get_cost(self, obj):
        return WorkRunMachineCostFieldsSchema().dump(obj)



class ComponentMaterialUsageSchema(Schema):
    usage_id = fields.Integer()
    item_component_id = fields.Integer()
    material_list_id = fields.Integer()
    quantity_used = fields.Float()
    material_list = fields.Nested(MaterialListSchema())

class ComponentTemplateSectionDataSchema(Schema):
    section_data_id = fields.Integer(dump_only=True)
    section_type = fields.String()
    data = fields.Raw()
    section_key = fields.String()
    item_component_id = fields.Integer()
    is_test_section = fields.Boolean(allow_none=True)

class ItemComponentSchema(Schema):
    item_component_id = fields.Integer()
    work_order_id = fields.Integer()
    branch_id = fields.Integer(allow_none=True)
    component_name = fields.String()
    remark = fields.String(allow_none=True)
    img_url = fields.String(allow_none=True)
    doc_version = fields.Integer()
    component_template_id = fields.Integer(allow_none=True)
    material_usages = fields.List(fields.Nested(ComponentMaterialUsageSchema()))
    component_template_sections = fields.List(fields.Nested(ComponentTemplateSectionDataSchema()), dump_default=[])
    # Populated by item_component_service — not a DB column.
    is_locked = fields.Boolean(dump_only=True)
    lock_reason = fields.String(dump_only=True, allow_none=True)
    active_edit_request = fields.Nested(lambda: ComponentEditRequestSchema(), dump_only=True, allow_none=True)
    has_test_section = fields.Boolean(dump_only=True)
    test_section_keys = fields.List(fields.String(), dump_only=True)


class ItemComponentVersionSchema(Schema):
    version_id = fields.Integer(dump_only=True)
    item_component_id = fields.Integer(dump_only=True)
    version_no = fields.Integer(dump_only=True)
    component_name = fields.String(dump_only=True)
    remark = fields.String(dump_only=True, allow_none=True)
    img_url = fields.String(dump_only=True, allow_none=True)
    component_template_id = fields.Integer(dump_only=True, allow_none=True)
    template_name = fields.String(dump_only=True, allow_none=True)
    sections_snapshot = fields.Raw(dump_only=True)
    section_data_snapshot = fields.Raw(dump_only=True)
    material_usage_snapshot = fields.Raw(dump_only=True)
    doc_ref_no = fields.String(dump_only=True, allow_none=True)
    doc_path = fields.String(dump_only=True, allow_none=True)
    change_reason = fields.String(dump_only=True, allow_none=True)
    edit_request_id = fields.Integer(dump_only=True, allow_none=True)
    created_by = fields.String(dump_only=True, allow_none=True)
    created_date = fields.DateTime(dump_only=True)


class ItemComponentVersionListSchema(ItemComponentVersionSchema):
    """History listing — drops the heavy snapshot blobs."""
    class Meta:
        exclude = ("sections_snapshot", "section_data_snapshot", "material_usage_snapshot")


class ComponentEditRequestSchema(Schema):
    edit_request_id = fields.Integer(dump_only=True)
    item_component_id = fields.Integer(dump_only=True)
    work_order_id = fields.Integer(dump_only=True)
    base_version_no = fields.Integer(dump_only=True, allow_none=True)
    reason = fields.String()
    status = fields.Enum(ComponentEditRequestStatus, dump_only=True)
    reviewed_by = fields.String(dump_only=True, allow_none=True)
    reviewed_date = fields.DateTime(dump_only=True, allow_none=True)
    review_remark = fields.String(dump_only=True, allow_none=True)
    consumed_version_id = fields.Integer(dump_only=True, allow_none=True)
    branch_id = fields.Integer(dump_only=True, allow_none=True)
    created_by = fields.String(dump_only=True, allow_none=True)
    created_date = fields.DateTime(dump_only=True)


class ComponentEditRequestListSchema(ComponentEditRequestSchema):
    """Inbox row — carries enough context that Production doesn't have to open the WO."""
    component_name = fields.String(dump_only=True, allow_none=True, attribute="item_component.component_name")
    work_order_code = fields.String(dump_only=True, allow_none=True, attribute="work_order.work_order_code")


class WorkRunComponentPinSchema(Schema):
    pin_id = fields.Integer(dump_only=True)
    work_run_id = fields.Integer(dump_only=True)
    item_component_id = fields.Integer(dump_only=True)
    version_id = fields.Integer(dump_only=True)
    version_no = fields.Integer(dump_only=True)
    superseded_date = fields.DateTime(dump_only=True, allow_none=True)
    reason = fields.String(dump_only=True, allow_none=True)
    created_by = fields.String(dump_only=True, allow_none=True)
    created_date = fields.DateTime(dump_only=True)
    component_name = fields.String(dump_only=True, allow_none=True, attribute="item_component.component_name")
    doc_ref_no = fields.String(dump_only=True, allow_none=True, attribute="version.doc_ref_no")
    doc_path = fields.String(dump_only=True, allow_none=True, attribute="version.doc_path")


class WorkRunReworkSourceSchema(Schema):
    id                 = fields.Integer(dump_only=True)
    rework_work_run_id = fields.Integer(dump_only=True)
    source_work_run_id = fields.Integer(dump_only=True)
    qty                = fields.Integer()
    created_date       = fields.DateTime(dump_only=True)


class WorkRunTransactionSchema(Schema):
    transaction_id        = fields.Integer(dump_only=True)
    work_run_id           = fields.Integer(dump_only=True)
    quantity              = fields.Float(dump_only=True)
    type                  = fields.Enum(WorkRunTransactionType, dump_only=True)
    related_document_code = fields.String(dump_only=True)
    created_date          = fields.DateTime(dump_only=True)
    created_by            = fields.String(dump_only=True)


class WorkRunSchema(Schema):
    work_run_id                      = fields.Integer()
    lot_number                       = fields.String(allow_none=True)
    work_order_id                    = fields.Integer()
    branch_id                        = fields.Integer()
    quantity                         = fields.Float()
    usable_qty                       = fields.Float(allow_none=True)
    defect_qty                       = fields.Float(dump_only=True, allow_none=True)
    consumed_defect_qty              = fields.Float(dump_only=True)
    outstanding_defect_qty           = fields.Float(dump_only=True, allow_none=True)
    tested_qty                       = fields.Float(dump_only=True)
    untested_qty                     = fields.Float(dump_only=True, allow_none=True)
    completion_remark                = fields.String(allow_none=True)
    wms_pick_reference               = fields.String(allow_none=True)
    status                           = fields.Enum(WorkRunStatus)
    start_date                       = fields.DateTime(allow_none=True)
    end_date                         = fields.DateTime(allow_none=True)
    rework_source_test_result_id     = fields.Integer(allow_none=True, dump_only=True)
    qty_from_failed                  = fields.Float(allow_none=True, dump_only=True)
    created_date                     = fields.DateTime()

class WorkRunWithTestSchema(WorkRunSchema):
    test_result_sources = fields.List(fields.Nested(lambda: TestResultWorkRunFromRunSchema()))

class WorkOrderSchema(Schema):
    work_order_id = fields.Integer()
    doc_num = fields.Int()
    work_order_code = fields.String(allow_none=True)
    quantity = fields.Float()
    created_date = fields.DateTime()
    status = fields.Enum(WorkOrderStatus)
    branch_id = fields.Integer(allow_none=True)
    sales_item = fields.Nested(SalesItemForWorkOrderSchema())

class WorkOrderSchemaDetail(WorkOrderSchema):
    # Overrides WorkOrderSchema's sales_item (SalesItemForWorkOrderSchema,
    # which has no material_list) with the detail schema that carries the
    # full material_list — the component editor needs every material on the
    # SalesItem, not just ones already assigned to some component.
    sales_item = fields.Nested(SalesItemSchemaDetail())
    item_components = fields.List(fields.Nested(ItemComponentSchema()))
    work_runs = fields.List(fields.Nested(WorkRunSchema()))

class SalesOrderSearchSchema(Schema):
    doc_num = fields.Int()
    doc_entry = fields.Int()

class SalesOrderSchema(Schema):
    doc_num = fields.Int()
    doc_entry = fields.Int()
    center_sales_order_id = fields.Integer()
    card_code = fields.String()
    card_name = fields.String()
    po_number = fields.String()
    slp_code = fields.String()
    slp_name = fields.String()
    bpl_code = fields.String()
    bpl_name = fields.String()
    group_code = fields.String()
    group_name = fields.String()
    status = fields.Enum(SalesOrderStatus)
    urgency_level = fields.Enum(UrgencyLevel, allow_none=True)
    created_date = fields.String()
    branch_id = fields.Integer(allow_none=True)


class SalesItemNoMaterialSchema(Schema):
    sales_item_id                = fields.Integer()
    center_sales_item_id         = fields.Integer()
    item_code                    = fields.String()
    quantity                     = fields.Float()
    order_line_num               = fields.Integer(allow_none=True)
    unit_name                    = fields.String()
    unit_id = fields.Integer()
    item_name                    = fields.String()
    item_description             = fields.String()
    cost_price                   = fields.Float()
    unit_price                   = fields.Float()
    doc_num                      = fields.Integer()
    doc_entry                    = fields.Integer()
    branch_id                    = fields.Integer(allow_none=True)
    producing_qty                = fields.Float(dump_only=True)
    produced_qty                 = fields.Float(dump_only=True)
    unavailable_for_test_qty     = fields.Float(dump_only=True)
    available_for_test_qty       = fields.Float(dump_only=True)
    passed_qty                   = fields.Float(dump_only=True)
    failed_qty                   = fields.Float(dump_only=True)
    produce                      = fields.Boolean()
    test                         = fields.Boolean()
    item_group                   = fields.String()

class SalesItemSchema(Schema):
    sales_item_id                = fields.Integer()
    center_sales_item_id         = fields.Integer()
    item_code                    = fields.String()
    quantity                     = fields.Float()
    order_line_num               = fields.Integer(allow_none=True)
    unit_name                    = fields.String()
    unit_id = fields.Integer()
    item_name                    = fields.String()
    item_description             = fields.String()
    cost_price                   = fields.Float()
    unit_price                   = fields.Float()
    doc_num                      = fields.Integer()
    doc_entry                    = fields.Integer()
    branch_id                    = fields.Integer(allow_none=True)
    material_list                = fields.List(fields.Nested(MaterialListSchema()))
    producing_qty                = fields.Float(dump_only=True)
    produced_qty                 = fields.Float(dump_only=True)
    unavailable_for_test_qty     = fields.Float(dump_only=True)
    available_for_test_qty       = fields.Float(dump_only=True)
    status                       = fields.Enum(SalesItemStatus, dump_only=True)
    passed_qty                   = fields.Float(dump_only=True)
    failed_qty                   = fields.Float(dump_only=True)
    num_qc_work_order            = fields.Integer(dump_only=True)
    num_qc_successed_work_order  = fields.Integer(dump_only=True)
    is_completable               = fields.Method("get_is_completable", dump_only=True)
    completable_reason           = fields.Method("get_completable_reason", dump_only=True)
    item_group                   = fields.String()

    def get_is_completable(self, obj):
        return obj.is_completable[0]

    def get_completable_reason(self, obj):
        return obj.is_completable[1]
    produce                      = fields.Boolean()
    test                         = fields.Boolean()
    work_order                   = fields.Nested(WorkOrderSchema)

class QCFormSchema(Schema):
    qc_form_id              = fields.Integer()
    qc_work_order_id        = fields.Integer()
    std_ptt                 = fields.Boolean()
    std_chevron             = fields.Boolean()
    std_valeur              = fields.Boolean()
    std_ophir               = fields.Boolean()
    std_three_spec          = fields.Boolean()
    std_others              = fields.Boolean()
    std_others_text         = fields.String()
    cert_inhouse            = fields.Boolean()
    cert_third_party        = fields.Boolean()
    cert_ndt                = fields.Boolean()
    cert_others             = fields.Boolean()
    cert_others_text        = fields.String()
    serial_tag              = fields.Boolean()
    serial_imprint          = fields.Boolean()
    serial_continue         = fields.Boolean()
    serial_others           = fields.Boolean()
    serial_others_text      = fields.String()
    general_remark          = fields.String()
    details                 = fields.String()
    customer_receipt_number = fields.String()
    transfer_date           = fields.Date()
    delivery_date           = fields.Date()


class QCItemSchema(Schema):
    qc_item_id       = fields.Integer()
    qc_work_order_id = fields.Integer()
    item_order       = fields.Integer()
    item_code        = fields.String()
    description      = fields.String()
    wll              = fields.String()
    quantity         = fields.String()
    serial_no        = fields.String()
    item_remark      = fields.String()
    material_list_id = fields.Integer(allow_none=True)
    required_qty     = fields.Float(allow_none=True)
    material_list         = fields.Nested(MaterialListSchema)

class search_qc_work_order_schema(Schema):
    qc_work_order_id = fields.Integer()
    qc_by = fields.String()

class QCWorkOrderSchema(Schema):
    qc_work_order_id = fields.Integer()
    qc_work_order_code = fields.String(allow_none=True)
    sales_item_id = fields.Integer()
    branch_id = fields.Integer(allow_none=True)
    qc_date = fields.DateTime()
    qc_by = fields.String()
    quantity = fields.Float()
    remark = fields.String()
    created_date = fields.DateTime()
    updated_date = fields.DateTime()
    created_by = fields.String()
    updated_by = fields.String()
    sales_item = fields.Nested(SalesItemNoMaterialSchema)
    status = fields.Method("get_status")
    source_work_order_id = fields.Integer(allow_none=True)
    is_component_declared = fields.Boolean(dump_only=True)

    def get_status(self, obj):
        if obj.status is None:
            return None
        return obj.status.value if hasattr(obj.status, "value") else obj.status

class QCWorkOrderSchemaDetail(QCWorkOrderSchema):
    qc_form = fields.Nested(QCFormSchema, allow_none=True)
    qc_items = fields.List(fields.Nested(QCItemSchema))
    test_results = fields.List(fields.Nested(lambda: TestResultSchema()), dump_only=True)
    sales_order     = fields.Method("get_sales_order")
    doc_entry       = fields.Method("get_doc_entry")
    sales_item_code = fields.Method("get_sales_item_code")
    sales_item_name = fields.Method("get_sales_item_name")
    source_work_order_code = fields.Method("get_source_work_order_code")

    def get_sales_order(self, obj):
        if obj.sales_item and obj.sales_item.sales_order:
            return SalesOrderSchema().dump(obj.sales_item.sales_order)
        return None

    def get_doc_entry(self, obj):
        return obj.sales_item.doc_entry if obj.sales_item else None

    def get_sales_item_code(self, obj):
        return obj.sales_item.item_code if obj.sales_item else None

    def get_sales_item_name(self, obj):
        return obj.sales_item.item_name if obj.sales_item else None

    def get_source_work_order_code(self, obj):
        return obj.source_work_order.work_order_code if obj.source_work_order else None


class TestResultCheckSchema(Schema):
    check_id            = fields.Integer(dump_only=True)
    test_result_item_id = fields.Integer(dump_only=True)
    check_name          = fields.String()
    status              = fields.Enum(CheckStatus)
    note                = fields.String(allow_none=True)
    sequence            = fields.Integer()
    created_date        = fields.DateTime(dump_only=True)
    updated_date        = fields.DateTime(dump_only=True)
    created_by          = fields.String(dump_only=True)
    updated_by          = fields.String(dump_only=True)


class TestResultPhotoSchema(Schema):
    photo_id     = fields.Integer(dump_only=True)
    caption      = fields.String(allow_none=True)
    sequence     = fields.Integer()
    url          = fields.Method("get_url", dump_only=True)
    created_date = fields.DateTime(dump_only=True)
    created_by   = fields.String(dump_only=True)

    def get_url(self, obj):
        from app.services.storage_service import get_presigned_url
        try:
            return get_presigned_url(obj.object_key)
        except Exception:
            return None


class TestResultSpecSchema(Schema):
    spec_id          = fields.Integer(dump_only=True)
    construction     = fields.String(allow_none=True)
    grade            = fields.String(allow_none=True)
    coating          = fields.String(allow_none=True)
    diameter         = fields.Float(allow_none=True)
    nominal_length   = fields.Float(allow_none=True)
    tensile_strength = fields.Float(allow_none=True)
    manufacturer     = fields.String(allow_none=True)
    batch_no         = fields.String(allow_none=True)
    termination      = fields.String(allow_none=True)


class TestResultItemSchema(Schema):
    test_result_item_id = fields.Integer(dump_only=True)
    test_result_id      = fields.Integer()
    unit_number         = fields.Integer()
    serial_no           = fields.String()
    wll_measured        = fields.Float(allow_none=True)
    load_test_value     = fields.Float(allow_none=True)
    description         = fields.String()
    result              = fields.Enum(TestResultStatus)
    remark              = fields.String()
    # Proof load
    required_load       = fields.Float(allow_none=True)
    hold_time_sec       = fields.Integer(allow_none=True)
    length_before       = fields.Float(allow_none=True)
    length_after        = fields.Float(allow_none=True)
    permanent_set       = fields.Float(dump_only=True)
    # Breaking
    breaking_force      = fields.Float(allow_none=True)
    min_breaking_load   = fields.Float(allow_none=True)
    efficiency          = fields.Float(dump_only=True)
    # Verdict
    fail_reason         = fields.String(allow_none=True)
    load_curve          = fields.Raw(allow_none=True)   # JSON array [{t, load}, ...]
    checks              = fields.List(fields.Nested(lambda: TestResultCheckSchema()), dump_only=True)
    created_date        = fields.DateTime(dump_only=True)
    updated_date        = fields.DateTime(dump_only=True)
    created_by          = fields.String(dump_only=True)
    updated_by          = fields.String(dump_only=True)


class TestResultWorkRunSchema(Schema):
    """From TestResult POV — nested inside TestResultSchema."""
    id           = fields.Integer(dump_only=True)
    work_run_id  = fields.Integer(dump_only=True)
    qty_from_run = fields.Float()
    work_run     = fields.Nested(WorkRunSchema(), dump_only=True)
    
class PickingRequestItemSchema(Schema):
    picking_request_item_id = fields.Integer()
    picking_request_id      = fields.Integer()
    sales_item_id           = fields.Integer(allow_none=True)
    material_list_id        = fields.Integer(allow_none=True)
    order_line_num          = fields.Integer(allow_none=True)
    item_code               = fields.String()
    item_name               = fields.String()
    quantity                = fields.Float()
    unit                    = fields.String(allow_none=True)
    remark                  = fields.String(allow_none=True)
    picking_request_code    = fields.Method("get_picking_request_code", dump_only=True)
    so_order_line_num       = fields.Method("get_so_order_line_num", dump_only=True)

    def get_picking_request_code(self, obj):
        pr = obj.picking_request
        return pr.picking_request_code if pr else None

    def get_so_order_line_num(self, obj):
        if obj.sales_item_id and obj.sales_item:
            return obj.sales_item.order_line_num
        if obj.material_list_id and obj.material_list:
            return obj.material_list.order_line_num
        return None

class PickingRequestSchema(Schema):
    picking_request_id   = fields.Integer()
    picking_request_code = fields.String(allow_none=True)
    doc_entry            = fields.Integer(allow_none=True)
    status               = fields.Enum(PickingRequestStatus)
    wms_reference        = fields.String(allow_none=True)
    remark               = fields.String(allow_none=True)
    created_by           = fields.String()
    created_date         = fields.DateTime()
    updated_by           = fields.String(allow_none=True)
    updated_date         = fields.DateTime(allow_none=True)
    
    
class PickingRequestItemDetailedSchema(PickingRequestItemSchema):
    picking_request = fields.Nested(PickingRequestSchema)

class WorkRunRequiredItemSchema(Schema):
    """BOM requirement for a WorkRun."""
    id                  = fields.Integer(dump_only=True)
    work_run_id         = fields.Integer(dump_only=True)
    material_list_id    = fields.Integer(allow_none=True)
    item_code           = fields.String()
    item_name           = fields.String()
    quantity            = fields.Float()
    unit                = fields.String(allow_none=True)
    qty_consumed_actual = fields.Float(allow_none=True)
    created_by          = fields.String(dump_only=True)
    created_date        = fields.DateTime(dump_only=True)
    material_list       = fields.Nested(MaterialListSchema)


class TestResultRequiredItemSchema(Schema):
    """Material requirement for a TestResult, seeded from QCItem."""
    id                  = fields.Integer(dump_only=True)
    test_result_id      = fields.Integer(dump_only=True)
    qc_item_id          = fields.Integer(allow_none=True, dump_only=True)
    material_list_id    = fields.Integer(allow_none=True)
    item_code           = fields.String()
    item_name           = fields.String()
    required_qty        = fields.Float()
    unit                = fields.String(allow_none=True)
    qty_consumed_actual = fields.Float(allow_none=True)
    material_list       = fields.Nested(MaterialListSchema, allow_none=True)
    created_by          = fields.String(dump_only=True)
    created_date        = fields.DateTime(dump_only=True)

class PickingRequestDetailSchema(PickingRequestSchema):
    items              = fields.List(fields.Nested(PickingRequestItemSchema()))
    sales_order        = fields.Nested(SalesOrderSearchSchema)

class TestResultSummarySchema(Schema):
    test_result_id   = fields.Integer(dump_only=True)
    test_result_code = fields.String(allow_none=True, dump_only=True)
    session_status   = fields.Enum(TestSessionStatus, dump_only=True)
    overall_status   = fields.Enum(TestResultStatus, allow_none=True, dump_only=True)


class WorkRunSummarySchema(Schema):
    work_run_id   = fields.Integer(dump_only=True)
    lot_number    = fields.String(allow_none=True, dump_only=True)
    work_order_id = fields.Integer(dump_only=True)
    status        = fields.Enum(WorkRunStatus, dump_only=True)


class PickingRequestFullDetailSchema(PickingRequestSchema):
    """PickingRequest with sales_order + items."""
    items       = fields.List(fields.Nested(PickingRequestItemSchema()), dump_only=True)
    sales_order = fields.Nested(SalesOrderSearchSchema, dump_only=True)

class WorkRunDisplaySchema(WorkRunSchema):
    assignments      = fields.List(fields.Nested(WorkRunAssignmentSchema()))
    machines         = fields.List(fields.Nested(WorkRunMachineSchema()))
    breaks           = fields.List(fields.Nested(WorkRunBreakSchema()))
    required_items   = fields.List(fields.Nested(WorkRunRequiredItemSchema()), dump_only=True)
    work_order       = fields.Nested(WorkOrderSchema(), allow_none=True)
    cost             = fields.Nested(WorkRunCostSchema(), allow_none=True)

class WorkRunCostDisplaySchema(WorkRunSchema):
    assignments = fields.List(fields.Nested(WorkRunAssignmentSchema()))
    machines = fields.List(fields.Nested(WorkRunMachineSchema()))
    breaks = fields.List(fields.Nested(WorkRunBreakSchema())) 
    required_items = fields.List(fields.Nested(WorkRunRequiredItemSchema()), dump_only=True)
    cost = fields.Nested(WorkRunCostSchema(), allow_none=True)

class WorkRunDetailSchema(WorkRunSchema):
    test_result_sources = fields.List(fields.Nested(lambda: TestResultWorkRunFromRunSchema()))
    rework_sources      = fields.List(fields.Nested(WorkRunReworkSourceSchema()), dump_only=True)
    transactions        = fields.List(fields.Nested(WorkRunTransactionSchema()), dump_only=True)
    
class TestResultWorkRunFromRunSchema(Schema):
    """From WorkRun POV — nested inside WorkRunDetailSchema/WorkRunWithTestSchema."""
    id             = fields.Integer(dump_only=True)
    test_result_id = fields.Integer(dump_only=True)
    qty_from_run   = fields.Float()
    test_result    = fields.Nested(lambda: TestResultSchema(), dump_only=True)

class TestResultBreakSchema(Schema):
    break_id    = fields.Integer(dump_only=True)
    break_start = fields.DateTime(dump_only=True)
    break_end   = fields.DateTime(allow_none=True, dump_only=True)
    break_type  = fields.Enum(BreakType, dump_only=True)
    remark      = fields.String(allow_none=True, dump_only=True)

class TestResultAssignmentSchema(Schema):
    test_result_assignment_id = fields.Integer(dump_only=True)
    test_result_id = fields.Integer(dump_only=True)
    employee_id = fields.Integer()
    from_time = fields.DateTime()
    to_time = fields.DateTime(allow_none=True)
    employee = fields.Nested(lambda: EmployeeSchema())

class TestResultMachineCostFieldSchema(Schema):
    depreciation_per_second = fields.Float()
    depreciation_cost = fields.Float(allow_none=True)
    maintenance_rate_per_second = fields.Float()
    maintenance_cost = fields.Float(allow_none=True)
    total_cost = fields.Method('get_total')

    def get_total(self, obj):
        d = obj.depreciation_cost
        m = obj.maintenance_cost
        if d is None and m is None:
            return None
        return round((d or 0.0) + (m or 0.0), 6)

class TestResultMachineSchema(Schema):
    test_result_machine_id = fields.Integer(dump_only=True)
    test_result_id = fields.Integer(dump_only=True)
    machine_id = fields.Integer()
    from_time = fields.DateTime()
    to_time = fields.DateTime(allow_none=True)
    allocated_maintenance_cost = fields.Float(allow_none=True)
    machine = fields.Nested(lambda: MachineSchema())
    cost = fields.Method('get_cost')

    def get_cost(self, obj):
        return TestResultMachineCostFieldSchema().dump(obj)
    
class TestResultCostSchema(Schema):
    cost_id = fields.Integer(dump_only=True)
    test_result_id = fields.Integer(dump_only=True)
    material_cost = fields.Float(allow_none=True)
    depreciation_cost = fields.Float(allow_none=True)
    maintenance_cost = fields.Float(allow_none=True)
    base_labor_cost = fields.Float(allow_none=True)
    day_labor_cost = fields.Float(allow_none=True)
    ot_labor_cost = fields.Float(allow_none=True)
    total_cost = fields.Float(allow_none=True)

class TestResultSchema(Schema):
    test_result_id          = fields.Integer(dump_only=True)
    test_result_code        = fields.String(allow_none=True, dump_only=True)
    qc_work_order_id        = fields.Integer(allow_none=True)
    claimed_qty             = fields.Float()
    session_status          = fields.Enum(TestSessionStatus, dump_only=True)
    started_at              = fields.DateTime(allow_none=True, dump_only=True)
    test_method             = fields.String(allow_none=True)
    test_type               = fields.Enum(TestType, allow_none=True)
    standard_reference      = fields.String(allow_none=True)
    overall_status          = fields.Enum(TestResultStatus, allow_none=True)
    remark                  = fields.String(allow_none=True)
    failed_item_qty         = fields.Integer(dump_only=True)
    reworked_qty            = fields.Float(dump_only=True)
    outstanding_failed_qty  = fields.Float(dump_only=True)
    test_result_items       = fields.List(fields.Nested(TestResultItemSchema()), dump_only=True)
    photos                  = fields.List(fields.Nested(TestResultPhotoSchema()), dump_only=True)
    spec                    = fields.Nested(TestResultSpecSchema(), allow_none=True)
    work_run_sources        = fields.List(fields.Nested(TestResultWorkRunSchema()), dump_only=True)
    required_items          = fields.List(fields.Nested(TestResultRequiredItemSchema()), dump_only=True)
    assignments             = fields.List(fields.Nested(TestResultAssignmentSchema()), dump_only=True)
    machines                = fields.List(fields.Nested(TestResultMachineSchema()), dump_only=True)
    breaks                  = fields.List(fields.Nested(TestResultBreakSchema()), dump_only=True)
    cost                    = fields.Nested(TestResultCostSchema(), allow_none=True, dump_only=True)
    created_date            = fields.DateTime(dump_only=True)
    updated_date            = fields.DateTime(dump_only=True)
    created_by              = fields.String(dump_only=True)
    updated_by              = fields.String(dump_only=True)


class QCCheckItemSchema(Schema):
    test_id             = fields.Integer(dump_only=True)
    qc_certification_id = fields.Integer()
    sales_item_id       = fields.Integer()
    test_result_item_id = fields.Integer()
    test_result_item    = fields.Nested(TestResultItemSchema(), dump_only=True)

    item_no     = fields.String()
    test_number = fields.String()
    ref_number  = fields.String()
    description = fields.String()
    wll         = fields.Float()
    load_test   = fields.Float()

    created_date = fields.DateTime(dump_only=True)
    updated_date = fields.DateTime(dump_only=True)
    created_by   = fields.String(dump_only=True)
    updated_by   = fields.String(dump_only=True)

# 2. Schema สำหรับตารางแม่ (ใบรับรอง)
class QCCertificateSchema(Schema):
    qc_certification_id = fields.Integer(dump_only=True)
    qc_work_order_id = fields.Integer()
    
    # อิงตาม Model ล่าสุดของพี่ที่ใช้คำว่า certification_number และมี standard_reference
    certification_number = fields.String() 
    certification_date = fields.DateTime()
    standard_reference = fields.String()
    test_method = fields.String()
    certification_status = fields.String() # Enum จะถูกแปลงเป็น Text (String) ให้ Frontend
    remark = fields.String()    
    
    # AuditMixin Fields
    created_date = fields.DateTime(dump_only=True)
    updated_date = fields.DateTime(dump_only=True)
    created_by = fields.String(dump_only=True)
    updated_by = fields.String(dump_only=True)

class OperationCostMonthlySchema(Schema):
    operation_cost_monthly_id = fields.Integer()
    operation_cost_date = fields.Date()
    depreciation_building_cost = fields.Float()
    depreciation_building_period = fields.Integer()
    depreciation_util_cost = fields.Float()
    depreciation_util_period = fields.Integer()
    office_rent_cost = fields.Float()
    office_supplies_cost = fields.Float()
    water_cost = fields.Float()
    electricity_cost = fields.Float()
    utility_cost = fields.Float()
    created_date = fields.DateTime()
    updated_date = fields.DateTime()
    created_by = fields.String()
    updated_by = fields.String()
class QCCertificateSchemaDetail(QCCertificateSchema):
    check_items = fields.Nested(QCCheckItemSchema, many=True, dump_only=True)


class TestResultSimpleSchema(Schema):
    test_result_id     = fields.Integer()
    claimed_qty        = fields.Float()
    session_status     = fields.Enum(TestSessionStatus)
    overall_status     = fields.Enum(TestResultStatus, allow_none=True)
    created_date       = fields.DateTime()


class WorkOrderTrackingSchema(Schema):
    work_order_id = fields.Integer()
    work_order_code = fields.String()
    status = fields.Enum(WorkOrderStatus)
    quantity = fields.Float()
    work_runs = fields.List(fields.Nested(WorkRunSchema()))


class QCWorkOrderTrackingSchema(Schema):
    qc_work_order_id = fields.Integer()
    qc_work_order_code = fields.String()
    qc_date = fields.DateTime()
    qc_by = fields.String()
    quantity = fields.Float()
    remark = fields.String()
    test_results = fields.List(fields.Nested(TestResultSimpleSchema()))
    created_by = fields.String()
    created_at = fields.String()


class SalesItemTrackingSchema(Schema):
    sales_item_id = fields.Integer()
    item_code = fields.String()
    quantity = fields.Float()
    order_line_num = fields.Integer(allow_none=True)
    unit_name = fields.String()
    unit_id = fields.Integer()
    item_name = fields.String()
    item_description = fields.String()
    doc_num = fields.Integer()
    doc_entry = fields.Integer()
    status = fields.Enum(SalesItemStatus)
    work_order = fields.Nested(WorkOrderTrackingSchema(), allow_none=True)
    qc_work_orders = fields.List(fields.Nested(QCWorkOrderTrackingSchema(), allow_none=True))

class MaterialTransactionSchema(Schema):
    transaction_id = fields.Integer(dump_only=True)
    material_list_id = fields.Integer(required=True)
    amount = fields.Float(required=True)  # positive = in, negative = out
    type = fields.Enum(MaterialTransactionType, dump_only=True)
    related_document_code = fields.String(required=True)
    created_date = fields.DateTime(dump_only=True)
    created_by = fields.String(dump_only=True)

class MachineTypeSchema(Schema):
    machine_type_id = fields.Integer(dump_only=True)
    type_name = fields.String()
    type_description = fields.String(allow_none=True)
    is_active = fields.Boolean()
    created_date = fields.DateTime(dump_only=True)
    updated_date = fields.DateTime(dump_only=True)
    created_by = fields.String(dump_only=True)
    updated_by = fields.String(dump_only=True)

class MachineSchema(Schema):
    machine_id = fields.Integer()
    machine_code = fields.String()
    machine_name = fields.String()
    machine_description = fields.String(allow_none=True)
    manufacturer = fields.String(allow_none=True)
    purchase_date = fields.Date(allow_none=True)
    purchase_price = fields.Float()
    useful_life_years = fields.Integer()
    working_hours_per_day = fields.Integer()
    remaining_maintenance_cost = fields.Float(allow_none=True)
    status = fields.Enum(MachineStatus)
    is_active = fields.Boolean()
    is_second_hand = fields.Boolean()
    accumulated_hours = fields.Float(allow_none=True)
    photo_url = fields.Method("get_photo_url", dump_only=True)
    machine_type_id = fields.Integer(allow_none=True)
    machine_type = fields.Nested(MachineTypeSchema, allow_none=True)
    created_date = fields.DateTime()
    updated_date = fields.DateTime()
    created_by = fields.String(allow_none=True)
    updated_by = fields.String(allow_none=True)

    def get_photo_url(self, obj):
        if not getattr(obj, "photo_key", None):
            return None
        from app.services.storage_service import get_presigned_url
        try:
            return get_presigned_url(obj.photo_key)
        except Exception:
            return None

class MachineMaintenanceSchema(Schema):
    maintenance_id = fields.Integer()
    machine_id = fields.Integer()
    maintenance_date = fields.DateTime()
    maintenance_type = fields.String() # Preventive, Corrective
    description = fields.String(allow_none=True)
    fix_cost = fields.Float(allow_none=True)
    machine = fields.Nested(MachineSchema, dump_default=None)
    created_date = fields.DateTime()

class GenNumberConfigSchema(Schema):
    gen_number_id = fields.Integer()
    gen_number_type = fields.String()
    gen_number_prefix = fields.String(allow_none=True)
    gen_number_format = fields.String()
    gen_number_current = fields.Integer()
    year_buddhist = fields.Boolean()
    document_code_id = fields.Integer(allow_none=True)
    created_date = fields.DateTime()
    updated_date = fields.DateTime()


class DocumentCodeListSchema(Schema):
    document_code_id = fields.Integer()
    gen_number_type = fields.String()
    description = fields.String(allow_none=True)
    created_date = fields.DateTime()
    updated_date = fields.DateTime()


class ComponentTemplateSchema(Schema):
    component_template_id = fields.Integer(dump_only=True)
    name = fields.String()
    sections = fields.Raw()
    created_date = fields.DateTime(dump_only=True)
    updated_date = fields.DateTime(dump_only=True)
    created_by = fields.String(dump_only=True)
    updated_by = fields.String(dump_only=True)

class PhaseTemplateItemSchema(Schema):
    phase_template_item_id = fields.Integer(dump_only=True)
    phase_template_id = fields.Integer()
    phase_name = fields.String()
    sort_order = fields.Integer()
    machine_type_id = fields.Integer(allow_none=True)
    machine_type = fields.Nested(MachineTypeSchema, allow_none=True, dump_only=True)

class PhaseTemplateSchema(Schema):
    phase_template_id = fields.Integer(dump_only=True)
    template_name = fields.String()
    is_active = fields.Boolean()
    items = fields.List(fields.Nested(PhaseTemplateItemSchema), dump_only=True)
    item_count = fields.Method("get_item_count")
    created_date = fields.DateTime(dump_only=True)
    updated_date = fields.DateTime(dump_only=True)
    created_by = fields.String(dump_only=True)
    updated_by = fields.String(dump_only=True)

    def get_item_count(self, obj):
        return len(obj.items) if obj.items else 0
