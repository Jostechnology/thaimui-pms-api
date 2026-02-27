from app.con_sqlalchemy import BreakType, EmployeeStatus, PhaseStatus, QCWorkOrderStatus, RolePermission, WorkOrderStatus
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
    sales_item_id = fields.Integer()
    item_code = fields.String()
    item_name = fields.String()
    item_description = fields.String()
    item_num = fields.Integer()
    cost_price = fields.Float()
    unit_price = fields.Float()
    created_date = fields.DateTime()
class SalesItemSchema(Schema):
    sales_item_id = fields.Integer()
    item_code = fields.String()
    item_num = fields.Integer()
    item_name = fields.String()
    item_description = fields.String()
    cost_price = fields.Float()
    unit_price = fields.Float()
    doc_num = fields.Int()
    material_list = fields.List(fields.Nested(MaterialListSchema()))
    
class WorkPhaseBreakSchema(Schema):
    break_id = fields.Integer()
    work_phase_id = fields.Integer()
    break_start = fields.DateTime()
    break_end = fields.DateTime(allow_none=True)
    break_type = fields.Enum(BreakType)

class WorkPhaseSchema(Schema):
    work_phase_id = fields.Integer()
    work_order_id = fields.Integer()
    phase_name = fields.String()
    phase_status = fields.Enum(PhaseStatus)
    start_date = fields.DateTime()
    end_date = fields.DateTime()
    created_date = fields.DateTime()
    employee_list = fields.List(fields.Nested(EmployeeSchema()))
    breaks = fields.List(fields.Nested(WorkPhaseBreakSchema()))
class WorkOrderSchema(Schema):
    work_order_id = fields.Integer()
    doc_num = fields.Int()
    created_date = fields.DateTime()
    status = fields.Enum(WorkOrderStatus)
    current_phase = fields.Nested(WorkPhaseSchema())
    work_phases = fields.List(fields.Nested(WorkPhaseSchema()))
    sales_item = fields.Nested(SalesItemSchema())



class SalesOrderSearchSchema(Schema):
    doc_num = fields.Int()
    doc_entry = fields.Int()

class SalesOrderSchema(Schema):
    doc_num = fields.Int()
    doc_entry = fields.Int()
    card_code = fields.String()
    card_name = fields.String()
    slp_code = fields.String()
    slp_name = fields.String()
    bpl_code = fields.String()
    bpl_name = fields.String()
    group_code = fields.String()
    group_name = fields.String()

class SalesItemSchema(Schema):
    sales_item_id    = fields.Integer()
    item_code        = fields.String()
    item_num         = fields.Integer()
    item_name        = fields.String()
    item_description = fields.String()
    doc_num          = fields.Integer()
    doc_entry        = fields.Integer()
    work_order_id    = fields.Integer()

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


class QCWorkOrderSchema(Schema):
    qc_work_order_id = fields.Integer()
    sales_item_id = fields.Integer()
    qc_status = fields.Enum(QCWorkOrderStatus)
    qc_date = fields.DateTime()
    qc_by = fields.String()
    remark = fields.String()
    created_date = fields.DateTime()
    updated_date = fields.DateTime()
    created_by = fields.String()
    updated_by = fields.String()
    qc_form = fields.Nested(QCFormSchema, allow_none=True)
    qc_items = fields.List(fields.Nested(QCItemSchema))
    doc_entry = fields.Method("get_doc_entry")
    sales_item_code = fields.Method("get_sales_item_code")
    sales_item_name = fields.Method("get_sales_item_name")

    def get_doc_entry(self, obj):
        return obj.sales_item.doc_entry if obj.sales_item else None

    def get_sales_item_code(self, obj):
        return obj.sales_item.item_code if obj.sales_item else None

    def get_sales_item_name(self, obj):
        return obj.sales_item.item_name if obj.sales_item else None


# 1. Schema สำหรับตารางลูก (รายการสินค้า/รายการเทส)
class QCCheckItemSchema(Schema):
    test_id = fields.Integer(dump_only=True)
    qc_certification_id = fields.Integer()
    
    item_no = fields.String()
    test_number = fields.String()
    ref_number = fields.String()
    description = fields.String()
    wll = fields.Float()
    load_test = fields.Float()
    
    # AuditMixin Fields
    created_date = fields.DateTime(dump_only=True)
    updated_date = fields.DateTime(dump_only=True)
    created_by = fields.String(dump_only=True)
    updated_by = fields.String(dump_only=True)

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
   
    # 3. สิ่งสำคัญ: เชื่อม Schema ลูกเข้ากับ Schema แม่แบบ One-to-Many
    check_items = fields.Nested(QCCheckItemSchema, many=True, dump_only=True)
    
    # AuditMixin Fields
    created_date = fields.DateTime(dump_only=True)
    updated_date = fields.DateTime(dump_only=True)
    created_by = fields.String(dump_only=True)
    updated_by = fields.String(dump_only=True)