from app.con_sqlalchemy import ItemComponent, ComponentSpecType, ComponentOptionType
from app.app import db


def get_item_component_by_id(item_component_id):
    try:
        return ItemComponent.query.get(item_component_id)
    except Exception:
        raise


def get_all_component_spec_types():
    try:
        return ComponentSpecType.query.order_by(ComponentSpecType.component_spec_type_id).all()
    except Exception:
        raise


def get_all_component_option_types():
    try:
        return ComponentOptionType.query.order_by(ComponentOptionType.component_option_type_id).all()
    except Exception:
        raise
