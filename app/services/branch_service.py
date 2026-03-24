from app.app import db
from app.exception import NotFoundError
from app.con_sqlalchemy import Branch
from app.repositories import branch_repository


def get_all_branchs():
    return branch_repository.get_all_branchs()


def create_branch(data):
    try:
        branch = Branch(
            branch_code=data.get("branch_code"),
            branch_name=data.get("branch_name")
        )
        branch_repository.create_branch(branch)
        db.session.commit()
        return branch
    except Exception:
        db.session.rollback()
        raise


def get_branch_by_id(branch_id):
    branch = db.session.query(Branch).filter(Branch.branch_id == branch_id).first()
    if not branch:
        raise NotFoundError(f"Branch id {branch_id} not found")
    return branch


def update_branch(branch_id, data):
    try:
        branch = get_branch_by_id(branch_id)
        branch.branch_code = data.get("branch_code", branch.branch_code)
        branch.branch_name = data.get("branch_name", branch.branch_name)
        db.session.commit()
        return branch
    except Exception:
        db.session.rollback()
        raise


def delete_branch(branch_id, is_active):
    try:
        branch = get_branch_by_id(branch_id)
        branch.is_active = is_active
        db.session.commit()
        return branch
    except Exception:
        db.session.rollback()
        raise
