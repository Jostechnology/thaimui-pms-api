from app.con_sqlalchemy import ReportRun, ReportDefinition
from app.app import db


def get_definition_by_code(code):
    query = db.session.query(ReportDefinition).filter(ReportDefinition.code == code)
    return query.first()


def get_all_definitions():
    query = db.session.query(ReportDefinition).order_by(ReportDefinition.code)
    return query.all()


def get_run_by_id(run_id):
    query = db.session.query(ReportRun).filter(ReportRun.run_id == run_id)
    return query.first()


def list_runs(page=1, per_page=20, code=None, requested_by=None, status=None):
    query = db.session.query(ReportRun)
    if code:
        query = query.filter(ReportRun.definition_code == code)
    if requested_by:
        query = query.filter(ReportRun.requested_by == requested_by)
    if status:
        query = query.filter(ReportRun.status == status)
    query = query.order_by(ReportRun.requested_at.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return {"items": paginated.items, "total_pages": paginated.pages, "total": paginated.total}
