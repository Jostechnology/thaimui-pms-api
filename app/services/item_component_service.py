from app.con_sqlalchemy import ItemComponent
from app.ma_sqlalchemy import (
    ItemComponentSchema,
)
from app.repositories import item_component_repository
from app.app import db
from app.exception import NotFoundError


def get_item_component_detail(item_component_id):
    try:
        item = item_component_repository.get_item_component_by_id(item_component_id)
        if not item:
            raise NotFoundError("ไม่พบข้อมูล Item Component")
        return ItemComponentSchema().dump(item)
    except Exception:
        raise