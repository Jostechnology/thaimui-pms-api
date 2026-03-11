from app.con_sqlalchemy import  MachineMaintenance , Machine
from app.app import db
from sqlalchemy.orm import joinedload

def get_all_pm_machines(search, page, per_page,status):
    try:
        query = MachineMaintenance.query.options(joinedload(MachineMaintenance.machine)).join(MachineMaintenance.machine)
        if search:
            query = query.filter(
                (MachineMaintenance.maintenance_type.ilike(f"%{search}%")) |
                (MachineMaintenance.description.ilike(f"%{search}%")) |
                (Machine.machine_name.ilike(f"%{search}%"))
            )
        if status:
            query = query.filter(MachineMaintenance.maintenance_type == status)
        result = query.paginate(page=page, per_page=per_page, error_out=False)
        return {"items": result.items, "total_pages": result.pages}
    except Exception:
        raise

def create_pm_machine(pm_machine):
    try:
        db.session.add(pm_machine)
        return pm_machine
    except Exception:
        db.session.rollback()
        raise