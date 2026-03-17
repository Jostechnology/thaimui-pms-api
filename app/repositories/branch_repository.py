from app.app import db
from app.con_sqlalchemy import Branch

def get_all_branchs():
    try:
        branchs = db.session.query(Branch).all()
        return branchs
    
    except Exception:
        raise

def create_branch(branch):
    try:
        db.session.add(branch)
        return branch
    except Exception:
        db.session.rollback()
        raise

def update_branch(branch):
    try:
        db.session.flush()
        db.session.refresh(branch)
        return branch
    except Exception:
        db.session.rollback()
        raise