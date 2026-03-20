from app.con_sqlalchemy import ItemComponent
from app.app import db


def get_item_component_by_id(item_component_id):
    try:
        return ItemComponent.query.get(item_component_id)
    except Exception:
        raise