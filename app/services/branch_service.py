import base64
from copy import deepcopy
import json
from app.app import db
from app.exception import AppException, MissingFieldsError, NotFoundError, UniqueError
from app.con_sqlalchemy import Branch
from app.repositories import branch_repository
from app.ma_sqlalchemy import BranchSchema
from app.utils import encode_jwt , hash_bcrypt, verify_bcrypt


def get_all_branchs():
    try:
        branchs = branch_repository.get_all_branchs()
        sche = BranchSchema(many=True)
        return sche.dump(branchs)
    except Exception as e:
        raise e

def create_branch(data):
    try:
        branch = Branch(
            branch_code=data.get("branch_code"),
            branch_name=data.get("branch_name")
        )
        branch = branch_repository.create_branch(branch)
        db.session.commit()
        return BranchSchema().dump(branch)
    except Exception as e:
        db.session.rollback()
        raise e

def update_branch(branch_id, data):
    try:
        branch = Branch.query.get(branch_id)
        if not branch:
            raise Exception(f"Branch id {branch_id} not found")
        branch.branch_code = data.get("branch_code", branch.branch_code)
        branch.branch_name = data.get("branch_name", branch.branch_name)
        db.session.flush()
        db.session.refresh(branch)
        db.session.commit()
        return BranchSchema().dump(branch)
    except Exception:
        db.session.rollback()
        raise

def delete_branch(branch_id, is_active):
    try:
        branch = Branch.query.get(branch_id)
        if not branch:
            raise Exception(f"Branch id {branch_id} not found")

        branch.is_active = is_active
        db.session.commit()

        status_text = "เปิดการใช้งาน" if is_active else "ปิดการใช้งาน"
        return {"message": f"{status_text}สาขา {branch.branch_name} สำเร็จ"}
    except Exception:
        db.session.rollback()
        raise