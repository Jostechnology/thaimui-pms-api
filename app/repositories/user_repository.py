from app.app import db
from app.con_sqlalchemy import User
from app.exception import NotFoundError

def get_user_by_username(username):
    try:
        user = db.session.query(User).filter(User.username == username).first()
        if not user:
            raise NotFoundError("ไม่พบผู้ใช้งาน")
        return user
    
    except Exception:
        raise

def get_user_by_id(user_id):
    try:
        user = db.session.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise NotFoundError("ไม่พบผู้ใช้งาน")
        return user
    
    except Exception:
        raise

def check_username_exist(username):
    try:
        u_name = db.session.query(User.username).filter(User.username == username).first()
        if u_name:
            return True
        return False
    except Exception:
        raise 

def get_user_by_id(user_id):
    try:
        user = db.session.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise NotFoundError("ไม่พบผู้ใช้งาน")
        return user
    except Exception:
        raise

def create_user(data):
    try:
        user = User(
            username=data.get("username"),
            password=data.get("password"),
            role_id=data.get("role_id"),
            is_active=data.get("is_active", True)
        )
        return user
    except Exception:
        raise

def get_user_list_paginated(page, limit, username="", role_id=None):
    try:
        offset = (page - 1) * limit
        
        query = User.query
        
        if role_id and role_id != "": 
            query = query.filter(User.role_id == role_id)
            
        if username and username.strip() != "":
            query = query.filter(User.username.ilike(f"%{username}%"))
        total_items = query.count()
        total_pages = (total_items + limit - 1) // limit if limit > 0 else 0
        users = query.order_by(User.created_date.desc()).offset(offset).limit(limit).all()

        return {
            "items": users,
            "total_pages": total_pages
        }
        
    except Exception as e:
        raise e
    
def change_user_role(username, role_id):
    try:
        user = get_user_by_username(username)
        user.role_id = role_id
        db.session.commit()
        return user
    except Exception:
        db.session.rollback()
        raise

def update_user_password(username, new_password):
    try:
        user = get_user_by_username(username)
        user.password = new_password
        db.session.commit()
        return user
    except Exception:
        db.session.rollback()
        raise

