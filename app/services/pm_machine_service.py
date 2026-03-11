from app.con_sqlalchemy import MachineMaintenance , Machine
from app.ma_sqlalchemy import MachineMaintenanceSchema
from app.repositories import pm_machine_repository
from app.app import db
from flask import g

def get_all_pm_machines(data):
    try:
        search = data.get("search", "")
        page = data.get("page", "")
        per_page = data.get("per_page", "")
        result = pm_machine_repository.get_all_pm_machines(search, page, per_page)
        return {
            "items": MachineMaintenanceSchema(many=True).dump(result["items"]),
            "total_pages": result["total_pages"]
        }
    except Exception:
        raise


def create_pm_machine(data):
    try:
        pm_machine = MachineMaintenance(
            machine_id=data.get("machine_id"),
            maintenance_date=data.get("maintenance_date"),
            maintenance_type=data.get("maintenance_type"),
            description=data.get("description"),
            fix_cost=data.get("fix_cost", 0),
        )
        pm_machine = pm_machine_repository.create_pm_machine(pm_machine)
        db.session.commit()
        return MachineMaintenanceSchema().dump(pm_machine)
    except Exception:
        db.session.rollback()
        raise
