from app.app import db
from app.models import User, Role
from app.schemas import RoleSchema
from con_sqlalchemy import user
def get_all_roles(username, role_id):
    try:
        user = User.query.filter(
            User.username == username, User.role_id == role_id
        ).first()
        if not user:
            return [], 200

        group_id = user.group_id
        roles = Role.query.filter(
            
        ).all()
        sche = RoleSchema(many=True)
        return sche.dump(roles), 200
    except Exception as e:
        return {"error": str(e)}, 500


