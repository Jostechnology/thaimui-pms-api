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

def create_user(data):
    try:
        new_user = User(
            username = data.get("username"),
            password = data.get("password")
        )
        return new_user
    except Exception:
        raise
