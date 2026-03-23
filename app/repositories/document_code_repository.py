from app.con_sqlalchemy import DocumentCodeList, GenNumberConfig
from app.app import db


def get_all_document_code_types():
    try:
        query = db.session.query(DocumentCodeList)
        return query.all()
    except Exception:
        raise


def get_all_gen_number_configs():
    try:
        query = db.session.query(GenNumberConfig)
        return query.all()
    except Exception:
        raise


def get_gen_number_config_by_id(gen_number_id):
    try:
        query = db.session.query(GenNumberConfig).filter(
            GenNumberConfig.gen_number_id == gen_number_id
        )
        return query.first()
    except Exception:
        raise


def get_gen_number_config_by_type(gen_number_type):
    try:
        query = db.session.query(GenNumberConfig).filter(
            GenNumberConfig.gen_number_type == gen_number_type
        )
        return query.first()
    except Exception:
        raise
