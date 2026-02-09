import base64
from copy import deepcopy
import json
from app.app import db
from app.exception import NotFoundError
from app.repositories import ModuleRepository, RoleRepository, UserRepository
from app.ma_sqlalchemy import GetPermissionSchema, GetRolePremissionSchema, ModuleSchema, RolePermissionSchema, RoleSchema
from app.utils import encode_jwt , hash_bcrypt, verify_bcrypt

def get_all_roles():
    try:
        roles = RoleRepository.get_all_roles()
        sche = RoleSchema(many=True)
        return sche.dump(roles)
    except Exception as e:
        raise e

def get_module_tree():
    try:
        modules = ModuleRepository.get_all_modules()
        module_dict = {}
        for mod in modules:
            if mod.level == 1:
                perm_query = ModuleRepository.get_permissions_of_module(mod)
                perm_res = GetPermissionSchema(many=True).dump(perm_query)
                perm_ls = []
                for perm in perm_res:
                    perm_ls.append(perm.get("method"))

                module_dict[mod.module_id] = {
                    "module_id": mod.module_id,
                    "module_name": mod.module_name,
                    "module_code": mod.module_code,
                    "sub_modules": [],
                    "permission": perm_ls,
                    "sort_order": mod.sort_order,
                }
            elif mod.level == 2 and mod.parent_id in module_dict:
                perm_query = ModuleRepository.get_permissions_of_module(mod)
                perm_res = GetPermissionSchema(many=True).dump(perm_query)
                perm_ls = []
                for perm in perm_res:
                    perm_ls.append(perm.get("method"))
                module_dict[mod.parent_id]["sub_modules"].append(
                    {
                        "module_id": mod.module_id,
                        "module_name": mod.module_name,
                        "module_code": mod.module_code,
                        "permission": perm_ls,
                        "sort_order": mod.sort_order,
                    }
                )
        return list(module_dict.values())
    except Exception as e:
        raise e

def get_role_permission(username, role_id):
    try:
        if username:
            user = UserRepository.get_user_by_username(username)
            if not user:
                raise NotFoundError("ไม่พบผู้ใข้งาน")

            role_id = user.role_id
            role = RoleRepository.get_role_by_id(role_id)
            if not role:
                raise NotFoundError("ไม่พบ Role")

        role_permission = RoleRepository.get_active_permissions_by_role(role_id)
        if not role_permission:
            role_permission = []

        schema = GetRolePremissionSchema(many=True)
        result = schema.dump(role_permission)
        module_tree = get_module_tree()
        for m in module_tree:
            if len(m.get("permission")) > 0:
                rs = [
                    item for item in result if item["module_id"] == m.get("module_id")
                ]
                if rs:
                    md_dict = {}
                    for r in rs:
                        if r.get("method") in m.get("permission"):
                            m["permission"].remove(r.get("method"))
                            md_dict["method"] = r.get("method")
                            md_dict["check"] = True
                            m["permission"].append(md_dict)
                        # else:
                        #     m['permission'].remove(r.get('method'))
                        #     md_dict['method'] = r.get('method')
                        #     md_dict['check'] = False
                        #     m['permission'].append(md_dict)
                m_permission = deepcopy(m.get("permission"))
                for mp in m_permission:
                    md_dict = {}
                    if isinstance(mp, str):
                        m["permission"].remove(mp)
                        md_dict["method"] = mp
                        md_dict["check"] = False
                        m["permission"].append(md_dict)
            for sm in m.get("sub_modules"):
                rs = [
                    item for item in result if item["module_id"] == sm.get("module_id")
                ]
                if rs:
                    for r in rs:
                        md_dict = {}
                        if r.get("method") in sm.get("permission"):
                            sm["permission"].remove(r.get("method"))
                            md_dict["method"] = r.get("method")
                            md_dict["check"] = True
                            sm["permission"].append(md_dict)
                        # else:
                        #     sm['permission'].remove(r.get('method'))
                        #     md_dict['method'] = r.get('method')
                        #     md_dict['check'] = False
                        #     sm['permission'].append(md_dict)
                sub_permission = deepcopy(sm.get("permission"))
                for msp in sub_permission:
                    md_dict = {}
                    if isinstance(msp, str):
                        sm["permission"].remove(msp)
                        md_dict["method"] = msp
                        md_dict["check"] = False
                        sm["permission"].append(md_dict)

        # with open("private_key.pem", "rb") as key_file:
        #     private_key = serialization.load_pem_private_key(key_file.read(), password=None)

        data_bytes = json.dumps(module_tree).encode("utf-8")
        permission_tree_b64 = base64.b64encode(data_bytes).decode("utf-8")

        payload = {
            "signed_permission_tree": permission_tree_b64
        }

        token = encode_jwt(payload)

        # signature = private_key.sign(
        #     data_bytes,
        #     asym_padding.PSS(mgf=asym_padding.MGF1(hashes.SHA256()), salt_length=asym_padding.PSS.MAX_LENGTH),
        #     hashes.SHA256()
        # )
        return (
            base64.b64encode(data_bytes).decode("utf-8"),
            token
        )

            
    except Exception as e:
        raise e
    
def create_module(data):
    try:
        module_name = data.get("module_name")
        module_code = data.get("module_code")
        sort_order = data.get("sort_order", 0)
        parent_id = data.get("parent_id")  # เพิ่ม parent_id สำหรับ sub-module
        level = data.get("level", 1)  # default เป็น main module
        permssion_list = data.get("permission_list", [])
        create_permission_list = []

        if level == 1 and sort_order == 0:
            sort_order = ModuleRepository.get_module_highest_order()
            sort_order = sort_order.sort_order + 1 if sort_order else 1

        if not module_name or not module_code:
            return {"error": "Missing module_name or module_code"}, 400

        existing = ModuleRepository.get_module_by_code(module_code)
        if existing:
            return {"error": "Module code already exists"}, 400

        if parent_id:
            parent = ModuleRepository.get_module_by_id(parent_id)
            if not parent:
                return {"error": "Parent module not found"}, 400

        create_obj = {
            "module_name" : module_name,
            "module_code" : module_code,
            "sort_order" : sort_order,
            "parent_id" : parent_id,
            "level" : level,
        }

        new_module = ModuleRepository.create_module(create_obj)
        db.session.add(new_module)
        db.session.flush()
        per_view = "view."
        dec_view = "View "
        if not permssion_list:
            permission_code = per_view+ data.get("module_code")
            description = dec_view+ data.get("module_name")
            permiss_dict = {
                "permission_code": permission_code,
                "description": description,
                "module_id": new_module.module_id,
                "method": "view",
            }
            create_permission_list.append(permiss_dict)
        else:
            for pl in permssion_list:
                if pl == "view":
                    permission_code = per_view+ data.get("module_code")
                    description = dec_view+ data.get("module_name")
                    permiss_dict = {
                        "permission_code": permission_code,
                        "description": description,
                        "module_id": new_module.module_id,
                        "method": "view",
                    }
                    create_permission_list.append(permiss_dict)
                elif pl == "create":
                    permission_code = "create." + data.get("module_code")
                    description = "Create " + data.get("module_name")
                    permiss_dict = {
                        "permission_code": permission_code,
                        "description": description,
                        "module_id": new_module.module_id,
                        "method": "create",
                    }
                    create_permission_list.append(permiss_dict)
                elif pl == "edit":
                    permission_code = "edit." + data.get("module_code")
                    description = "Edit " + data.get("module_name")
                    permiss_dict = {
                        "permission_code": permission_code,
                        "description": description,
                        "module_id": new_module.module_id,
                        "method": "edit",
                    }
                    create_permission_list.append(permiss_dict)
                elif pl == "delete":
                    permission_code = "delete." + data.get("module_code")
                    description = "Delete " + data.get("module_name")
                    permiss_dict = {
                        "permission_code": permission_code,
                        "description": description,
                        "module_id": new_module.module_id,
                        "method": "delete",
                    }
                    create_permission_list.append(permiss_dict)
                elif pl == "export":
                    permission_code = "export." + data.get("module_code")
                    description = "Export " + data.get("module_name")
                    permiss_dict = {
                        "permission_code": permission_code,
                        "description": description,
                        "module_id": new_module.module_id,
                        "method": "export",
                    }
                    create_permission_list.append(permiss_dict)

        for perm in create_permission_list:
            permission = ModuleRepository.create_permission(perm)
            db.session.add(permission)

        db.session.commit()

        return ModuleSchema().dump(new_module)
    except Exception as e:
        db.session.rollback()
        raise e

def get_modules_main():
    try:
        modules = ModuleRepository.get_main_modules()
        return ModuleSchema(many=True).dump(modules)
    except Exception as e:
        raise e
    
def get_module_sorted(module_id):
    try:
        module = ModuleRepository.get_sub_module_hightest(module_id)
        if not module:
            return 0
        return module.sort_order
    except Exception as e:
        raise e

def update_role_permissions(role_id, permission_ids):
    try:
        ModuleRepository.deactivate_role_permission_of_role()

        for pid in permission_ids:
            rp = ModuleRepository.get_role_permission_of_role_and_permission(role_id, pid)
            if rp:
                rp.active_flag = True
            else:
                create_obj = {
                    "role_id" : role_id,
                    "permission_id" : pid
                }
                new_rp = ModuleRepository.create_role_permission(create_obj)
                db.session.add(new_rp)

        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        raise e
    
def upsert_role_permission(data):
    try:
        role_id = data.get("role_id")
        module_list = data.get("module_list")

        if not role_id or not isinstance(module_list, list):
            return {"error": "Missing role_id or module_list"}, 400

        permission_id_list = []
        for module in module_list:
            module_id = module.get("module_id")
            method = module.get("method")
            if not module_id or not method:
                continue
            mr = ModuleRepository.get_permission_by_module(module_id, method)
            if mr and mr.permission_id is not None:
                permission_id_list.append(mr.permission_id)

        ModuleRepository.deactivate_role_permission_of_role(role_id)


        for pid in permission_id_list:
            existing = ModuleRepository.get_role_permission_of_role_and_permission(role_id, pid)
            if existing:
                existing.active_flag = True
            else:
                create_obj = {
                    "role_id" : role_id,
                    "permission_id" : pid
                }
                new_rp = ModuleRepository.create_role_permission(create_obj)
                db.session.add(new_rp)

        db.session.commit()

        updated = ModuleRepository.get_all_modules()
        return RolePermissionSchema(many=True).dump(updated)

    except Exception as e:
        db.session.rollback()
        raise

def create_user(data):
    try:
        username = data.get("username")
        password = data.get("password")
        role_id = data.get("role_id")
        if not username or not password:
            return {"error": "Missing username, password, or role_id"}, 400

        if UserRepository.check_username_exist(username):
            return {"error": "Username already exists"}, 400

        hashed_password = hash_bcrypt(password)

        create_obj = {
            "username" : username,
            "password" : hashed_password,
            "role_id" :  role_id
        }

        new_user = UserRepository.create_user(create_obj)
        db.session.add(new_user)
        db.session.commit()

        return UserRepository.get_user_by_id(new_user.user_id).username
    except Exception as e:
        db.session.rollback()
        raise e


def get_user_list(data):
    try:
        page = int(data.get("page", 1))
        limit = int(data.get("pageConfig", 10))
        username = data.get("search", "")
        role_id = data.get("filter") 

        result = UserRepository.get_user_list_paginated(
            page=page, 
            limit=limit, 
            username=username, 
            role_id=role_id
        )
        items = []
        for user in result['items']:
            items.append({
                "username": user.username,
                "role_id": user.role_id,
                "role_name": user.role.role_name if user.role else "-",
                "created_date": user.created_date.strftime("%Y-%m-%d %H:%M:%S") if user.created_date else "-"
            })
        return {
            "items": items,
            "total_pages": result['total_pages']
        }

    except Exception as e:
        raise e
    
def change_user_role(data):
    try:
        username = data.get("username")
        role_id = data.get("role_id")
        update_by = data.get("update_by")

        user = UserRepository.get_user_by_username(username)
        if not user:
            return {"error": "User not found"}, 404
        
        role_update = UserRepository.change_user_role(username, role_id)
        db.session.add(role_update)
        db.session.commit()
        return UserRepository.get_user_by_id(user.user_id).username
    except Exception as e:
        db.session.rollback()
        raise e

def change_user_password(data):
    try:
        username = data.get("username", "").strip()
        new_password_raw = data.get("new_password")
        old_password_raw = data.get("old_password")

        user = UserRepository.get_user_by_username(username)
        if not user:
            return {"error": "User not found", "success": False}, 404
        
        if not username or not new_password_raw or not old_password_raw:
            return {"error": "Missing required fields (username, new_password, old_password)", "success": False}, 400
        
        if not verify_bcrypt(old_password_raw, user.password):
            return {"error": "รหัสผ่านเดิมไม่ถูกต้อง", "success": False}, 400
        
        if old_password_raw == new_password_raw:
            return {"error": "รหัสผ่านใหม่ต้องไม่ซ้ำกับรหัสผ่านเดิม", "success": False}, 400

        hashed_new_password = hash_bcrypt(new_password_raw)

        UserRepository.update_user_password(username, hashed_new_password)
        
        db.session.commit()
        return {"message": "เปลี่ยนรหัสผ่านสำเร็จ", "success": True}, 200

    except Exception as e:
        db.session.rollback()
        print(f"Error Change Password: {str(e)}")
        raise e


