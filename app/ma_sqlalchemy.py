from app.con_sqlalchemy import RolePermission
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
    status = fields.String()
    address = fields.String()
    user_id = fields.Integer()
    is_active = fields.Boolean()

class SalesItemSchema(Schema):
    sales_item_id = fields.Integer()
    item_code = fields.String()
    item_num = fields.Integer()
    item_name = fields.String()
    item_description = fields.String()
    cost_price = fields.Float()
    unit_price = fields.Float()
    doc_num = fields.Int()
    
class WorkPhaseBreakSchema(Schema):
    break_id = fields.Integer()
    work_phase_id = fields.Integer()
    break_start = fields.DateTime()
    break_end = fields.DateTime(allow_none=True)
    break_type = fields.Method("get_break_type")

    def get_break_type(self, obj):
        if obj.break_type:
            return obj.break_type.value
        return "Other"

class WorkPhaseSchema(Schema):
    work_phase_id = fields.Integer()
    work_order_id = fields.Integer()
    phase_name = fields.String()
    phase_status = fields.String()
    start_date = fields.DateTime()
    end_date = fields.DateTime()
    created_date = fields.DateTime()
    employee_list = fields.List(fields.Nested(EmployeeSchema()))
    breaks = fields.List(fields.Nested(WorkPhaseBreakSchema()))
class WorkOrderSchema(Schema):
    work_order_id = fields.Integer()
    doc_num = fields.Int()
    created_date = fields.DateTime()
    status = fields.String()
    current_phase = fields.Nested(WorkPhaseSchema())
    work_phases = fields.List(fields.Nested(WorkPhaseSchema()))
    sales_item = fields.Nested(SalesItemSchema())

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
