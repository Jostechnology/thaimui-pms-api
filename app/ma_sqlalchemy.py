from app.con_sqlalchemy import BreakType, EmployeeStatus, MachineStatus, MaterialTransactionType, PhaseStatus, RolePermission, SalesOrderStatus, TestResultStatus, TestSessionStatus, WorkOrderStatus, WorkRunStatus, WorkRunTransactionType, SalesItemStatus, WorkRun, TestResultWorkRun, PickingRequestStatus, PickingRequestType
from marshmallow import Schema, fields
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


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
    salary_base = fields.Float()

class EmployeeSalaryHistorySchema(Schema):
    salary_history_id = fields.Integer()
    employee_id = fields.Integer()
    old_salary = fields.Float()
    new_salary = fields.Float()
    effective_date = fields.DateTime()
    remark = fields.String()

class MaterialListSchema(Schema):
    material_list_id = fields.Integer()
    center_material_id = fields.Integer()
    sales_item_id = fields.Integer()
    item_code = fields.String()
    item_name = fields.String()
    item_description = fields.String()
    original_num = fields.Integer()
    remaining_num = fields.Integer(dump_only=True)
    cost_price = fields.Float()
    unit_price = fields.Float()
    created_date = fields.DateTime()
    branch_id = fields.Integer(allow_none=True)
class SalesItemSchema(Schema):
    sales_item_id = fields.Integer()
    center_sales_item_id = fields.Integer()
    item_code = fields.String()
    item_num = fields.Integer()
    item_name = fields.String()
    item_description = fields.String()
    cost_price = fields.Float()
    unit_price = fields.Float()
    doc_num = fields.Int()
    branch_id = fields.Integer(allow_none=True)

class SalesItemSchemaDetail(SalesItemSchema):
    material_list = fields.List(fields.Nested(MaterialListSchema()))

    
class WorkPhaseBreakSchema(Schema):
    break_id = fields.Integer()
    work_phase_id = fields.Integer()
    break_start = fields.DateTime()
    break_end = fields.DateTime(allow_none=True)
    break_type = fields.Enum(BreakType)

class WorkPhaseSchema(Schema):
    work_phase_id = fields.Integer()
    work_run_id = fields.Integer()
    phase_name = fields.String()
    phase_status = fields.Enum(PhaseStatus)
    start_date = fields.DateTime()
    end_date = fields.DateTime()
    created_date = fields.DateTime()
    
class WorkPhaseSchemaDetailed(WorkPhaseSchema):
    employee_list = fields.Method("get_employee_list")
    breaks = fields.List(fields.Nested(WorkPhaseBreakSchema()))

    def get_employee_list(self, obj):
        return EmployeeSchema(many=True).dump([a.employee for a in obj.assignments])



class ComponentMaterialUsageSchema(Schema):
    usage_id = fields.Integer()
    item_component_id = fields.Integer()
    material_list_id = fields.Integer()
    quantity_used = fields.Integer()
    material_list = fields.Nested(MaterialListSchema())

class ComponentTemplateSectionDataSchema(Schema):
    section_data_id = fields.Integer(dump_only=True)
    section_type = fields.String()
    data = fields.Raw()
    section_key = fields.String()
    item_component_id = fields.Integer()

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

class WorkRunReworkSourceSchema(Schema):
    id                 = fields.Integer(dump_only=True)
    rework_work_run_id = fields.Integer(dump_only=True)
    source_work_run_id = fields.Integer(dump_only=True)
    qty                = fields.Integer()
    created_date       = fields.DateTime(dump_only=True)


class WorkRunTransactionSchema(Schema):
    transaction_id        = fields.Integer(dump_only=True)
    work_run_id           = fields.Integer(dump_only=True)
    quantity              = fields.Integer(dump_only=True)
    type                  = fields.Enum(WorkRunTransactionType, dump_only=True)
    related_document_code = fields.String(dump_only=True)
    created_date          = fields.DateTime(dump_only=True)
    created_by            = fields.String(dump_only=True)


class WorkRunSchema(Schema):
    work_run_id                      = fields.Integer()
    lot_number                       = fields.String(allow_none=True)
    work_order_id                    = fields.Integer()
    branch_id                        = fields.Integer()
    quantity                         = fields.Integer()
    usable_qty                       = fields.Integer(allow_none=True)
    defect_qty                       = fields.Integer(dump_only=True, allow_none=True)
    consumed_defect_qty              = fields.Integer(dump_only=True)
    outstanding_defect_qty           = fields.Integer(dump_only=True, allow_none=True)
    tested_qty                       = fields.Integer(dump_only=True)
    untested_qty                     = fields.Integer(dump_only=True, allow_none=True)
    completion_remark                = fields.String(allow_none=True)
    wms_pick_reference               = fields.String(allow_none=True)
    status                           = fields.Enum(WorkRunStatus)
    current_phase_id                 = fields.Integer(allow_none=True)
    rework_source_test_result_id     = fields.Integer(allow_none=True, dump_only=True)
    qty_from_failed                  = fields.Integer(allow_none=True, dump_only=True)
    created_date                     = fields.DateTime()

class WorkRunWithTestSchema(WorkRunSchema):
    test_result_sources = fields.List(fields.Nested(lambda: TestResultWorkRunFromRunSchema()))

class WorkOrderSchema(Schema):
    work_order_id = fields.Integer()
    doc_num = fields.Int()
    work_order_code = fields.String(allow_none=True)
    quantity = fields.Integer()
    created_date = fields.DateTime()
    status = fields.Enum(WorkOrderStatus)
    branch_id = fields.Integer(allow_none=True)
    sales_item = fields.Nested(SalesItemSchema())

class WorkOrderSchemaDetail(WorkOrderSchema):
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
    created_date = fields.String()
    branch_id = fields.Integer(allow_none=True)


class SalesItemNoMaterialSchema(Schema):
    sales_item_id                = fields.Integer()
    center_sales_item_id         = fields.Integer()
    item_code                    = fields.String()
    item_num                     = fields.Integer()
    item_name                    = fields.String()
    item_description             = fields.String()
    cost_price                   = fields.Float()
    unit_price                   = fields.Float()
    doc_num                      = fields.Integer()
    doc_entry                    = fields.Integer()
    branch_id                    = fields.Integer(allow_none=True)
    producing_qty                = fields.Integer(dump_only=True)
    produced_qty                 = fields.Integer(dump_only=True)
    unavailable_for_test_qty     = fields.Integer(dump_only=True)
    available_for_test_qty       = fields.Integer(dump_only=True)
    passed_qty                   = fields.Integer(dump_only=True)
    failed_qty                   = fields.Integer(dump_only=True)
    produce                      = fields.Boolean()
    test                         = fields.Boolean()

class SalesItemSchema(Schema):
    sales_item_id                = fields.Integer()
    center_sales_item_id         = fields.Integer()
    item_code                    = fields.String()
    item_num                     = fields.Integer()
    item_name                    = fields.String()
    item_description             = fields.String()
    cost_price                   = fields.Float()
    unit_price                   = fields.Float()
    doc_num                      = fields.Integer()
    doc_entry                    = fields.Integer()
    branch_id                    = fields.Integer(allow_none=True)
    material_list                = fields.List(fields.Nested(MaterialListSchema()))
    producing_qty                = fields.Integer(dump_only=True)
    produced_qty                 = fields.Integer(dump_only=True)
    unavailable_for_test_qty     = fields.Integer(dump_only=True)
    available_for_test_qty       = fields.Integer(dump_only=True)
    status                       = fields.Enum(SalesItemStatus, dump_only=True)
    passed_qty                   = fields.Integer(dump_only=True)
    failed_qty                   = fields.Integer(dump_only=True)
    num_qc_work_order            = fields.Integer(dump_only=True)
    num_qc_successed_work_order  = fields.Integer(dump_only=True)
    is_completable               = fields.Method("get_is_completable", dump_only=True)
    completable_reason           = fields.Method("get_completable_reason", dump_only=True)

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
    quantity = fields.Integer()
    remark = fields.String()
    created_date = fields.DateTime()
    updated_date = fields.DateTime()
    created_by = fields.String()
    updated_by = fields.String()
    sales_item = fields.Nested(SalesItemNoMaterialSchema)

class QCWorkOrderSchemaDetail(QCWorkOrderSchema):
    qc_form = fields.Nested(QCFormSchema, allow_none=True)
    qc_items = fields.List(fields.Nested(QCItemSchema))
    doc_entry       = fields.Method("get_doc_entry")
    sales_item_code = fields.Method("get_sales_item_code")
    sales_item_name = fields.Method("get_sales_item_name")

    def get_doc_entry(self, obj):
        return obj.sales_item.doc_entry if obj.sales_item else None

    def get_sales_item_code(self, obj):
        return obj.sales_item.item_code if obj.sales_item else None

    def get_sales_item_name(self, obj):
        return obj.sales_item.item_name if obj.sales_item else None


class TestResultItemSchema(Schema):
    test_result_item_id = fields.Integer(dump_only=True)
    test_result_id      = fields.Integer()
    unit_number         = fields.Integer()
    serial_no           = fields.String()
    wll_measured        = fields.Float()
    load_test_value     = fields.Float()
    description         = fields.String()
    result              = fields.Enum(TestResultStatus)
    remark              = fields.String()
    created_date        = fields.DateTime(dump_only=True)
    updated_date        = fields.DateTime(dump_only=True)
    created_by          = fields.String(dump_only=True)
    updated_by          = fields.String(dump_only=True)


class TestResultWorkRunSchema(Schema):
    """From TestResult POV — nested inside TestResultSchema."""
    id           = fields.Integer(dump_only=True)
    work_run_id  = fields.Integer(dump_only=True)
    qty_from_run = fields.Integer()
    work_run     = fields.Nested(WorkRunSchema(), dump_only=True)
    
class PickingRequestItemSchema(Schema):
    picking_request_item_id = fields.Integer()
    picking_request_id      = fields.Integer()
    item_code               = fields.String()
    item_name               = fields.String()
    quantity                = fields.Integer()
    unit                    = fields.String(allow_none=True)
    remark                  = fields.String(allow_none=True)

class PickingRequestSchema(Schema):
    picking_request_id   = fields.Integer()
    picking_request_code = fields.String(allow_none=True)
    request_type         = fields.Enum(PickingRequestType)
    work_run_id        = fields.Integer(allow_none=True)
    test_result_id     = fields.Integer(allow_none=True)
    lot_number         = fields.Method("get_lot_number")
    test_result_code   = fields.Method("get_test_result_code")
    status             = fields.Enum(PickingRequestStatus)
    wms_reference      = fields.String(allow_none=True)
    remark             = fields.String(allow_none=True)
    created_by         = fields.String()
    created_date       = fields.DateTime()
    updated_by         = fields.String(allow_none=True)
    updated_date       = fields.DateTime(allow_none=True)

    def get_lot_number(self, obj):
        return obj.work_run.lot_number if obj.work_run else None

    def get_test_result_code(self, obj):
        return obj.test_result.test_result_code if obj.test_result else None

class PickingRequestDetailSchema(PickingRequestSchema):
    items              = fields.List(fields.Nested(PickingRequestItemSchema()))

class WorkRunDisplaySchema(WorkRunSchema): #DISPLAY PHASES
    current_phase       = fields.Nested(WorkPhaseSchemaDetailed(), allow_none=True)
    work_phases         = fields.List(fields.Nested(WorkPhaseSchemaDetailed()))
    picking_requests    = fields.List(fields.Nested(PickingRequestSchema))

class WorkRunDetailSchema(WorkRunSchema):
    test_result_sources = fields.List(fields.Nested(lambda: TestResultWorkRunFromRunSchema()))
    rework_sources      = fields.List(fields.Nested(WorkRunReworkSourceSchema()), dump_only=True)
    transactions        = fields.List(fields.Nested(WorkRunTransactionSchema()), dump_only=True)
    
class TestResultWorkRunFromRunSchema(Schema):
    """From WorkRun POV — nested inside WorkRunDetailSchema/WorkRunWithTestSchema."""
    id             = fields.Integer(dump_only=True)
    test_result_id = fields.Integer(dump_only=True)
    qty_from_run   = fields.Integer()
    test_result    = fields.Nested(lambda: TestResultSchema(), dump_only=True)

class TestResultSchema(Schema):
    test_result_id          = fields.Integer(dump_only=True)
    test_result_code        = fields.String(allow_none=True, dump_only=True)
    qc_work_order_id        = fields.Integer(allow_none=True)
    claimed_qty             = fields.Integer()
    session_status          = fields.Enum(TestSessionStatus, dump_only=True)
    test_date               = fields.DateTime(allow_none=True)
    tested_by               = fields.String(allow_none=True)
    test_method             = fields.String(allow_none=True)
    standard_reference      = fields.String(allow_none=True)
    overall_status          = fields.Enum(TestResultStatus, allow_none=True)
    remark                  = fields.String(allow_none=True)
    failed_item_qty         = fields.Integer(dump_only=True)
    reworked_qty            = fields.Integer(dump_only=True)
    outstanding_failed_qty  = fields.Integer(dump_only=True)
    test_result_items       = fields.List(fields.Nested(TestResultItemSchema()), dump_only=True)
    work_run_sources        = fields.List(fields.Nested(TestResultWorkRunSchema()), dump_only=True)
    picking_requests        = fields.List(fields.Nested(PickingRequestSchema), dump_only=True)
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

class WorkPhaseSimpleSchema(Schema):
    work_phase_id = fields.Integer()
    phase_name = fields.String()
    phase_status = fields.Enum(PhaseStatus)
    start_date = fields.DateTime()
    end_date = fields.DateTime()


class TestResultSimpleSchema(Schema):
    test_result_id     = fields.Integer()
    claimed_qty        = fields.Integer()
    session_status     = fields.Enum(TestSessionStatus)
    overall_status     = fields.Enum(TestResultStatus, allow_none=True)
    test_date          = fields.DateTime(allow_none=True)
    tested_by          = fields.String(allow_none=True)
    created_date       = fields.DateTime()


class WorkOrderTrackingSchema(Schema):
    work_order_id = fields.Integer()
    work_order_code = fields.String()
    status = fields.Enum(WorkOrderStatus)
    quantity = fields.Integer()
    work_runs = fields.List(fields.Nested(WorkRunSchema()))


class QCWorkOrderTrackingSchema(Schema):
    qc_work_order_id = fields.Integer()
    qc_date = fields.DateTime()
    qc_by = fields.String()
    quantity = fields.Integer()
    remark = fields.String()
    test_results = fields.List(fields.Nested(TestResultSimpleSchema()))
    created_by = fields.String()
    created_at = fields.String()


class SalesItemTrackingSchema(Schema):
    sales_item_id = fields.Integer()
    item_code = fields.String()
    item_num = fields.Integer()
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
    amount = fields.Integer(required=True)  # positive = in, negative = out
    type = fields.Enum(MaterialTransactionType, dump_only=True)
    related_document_code = fields.String(required=True)
    created_date = fields.DateTime(dump_only=True)
    created_by = fields.String(dump_only=True)

class MachineSchema(Schema):
    machine_id = fields.Integer()
    machine_code = fields.String()
    machine_name = fields.String()
    machine_description = fields.String(allow_none=True)
    manufacturer = fields.String(allow_none=True)
    purchase_date = fields.Date(allow_none=True)
    status = fields.Enum(MachineStatus)
    is_active = fields.Boolean()
    created_date = fields.DateTime()
    updated_date = fields.DateTime()
    created_by = fields.String(allow_none=True)
    updated_by = fields.String(allow_none=True)

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
