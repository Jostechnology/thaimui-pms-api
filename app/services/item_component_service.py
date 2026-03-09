from app.con_sqlalchemy import ComponentOption, ComponentSpec, ItemComponent
from app.ma_sqlalchemy import (
    ItemComponentSchema,
    ComponentSpecTypeSchema,
    ComponentOptionTypeSchema,
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


def get_component_spec_types():
    try:
        items = item_component_repository.get_all_component_spec_types()
        return ComponentSpecTypeSchema(many=True).dump(items)
    except Exception:
        raise


def get_component_option_types():
    try:
        items = item_component_repository.get_all_component_option_types()
        return ComponentOptionTypeSchema(many=True).dump(items)
    except Exception:
        raise


def update_item_component_detail(item_component_id, data):
    try:
        item = item_component_repository.get_item_component_by_id(item_component_id)
        if not item:
            raise NotFoundError("ไม่พบข้อมูล Item Component")

        # Update remark
        if "remark" in data:
            item.remark = data["remark"]

        # Update specs — upsert logic
        if "specs" in data:
            incoming_specs = data["specs"]
            # Build map of existing specs keyed by (spec_type_id, end_side)
            existing_map = {}
            for spec in item.component_specs:
                key = (spec.component_spec_type_id, spec.end_side)
                existing_map[key] = spec

            incoming_keys = set()
            for spec_data in incoming_specs:
                spec_type_id = spec_data.get("component_spec_type_id")
                end_side = spec_data.get("end_side")
                key = (spec_type_id, end_side)
                incoming_keys.add(key)

                if key in existing_map:
                    # Update existing
                    existing = existing_map[key]
                    existing.bool_value = spec_data.get("bool_value")
                    existing.decimal_value = spec_data.get("decimal_value")
                    existing.text_value = spec_data.get("text_value")
                else:
                    # Create new
                    new_spec = ComponentSpec(
                        item_component_id=item_component_id,
                        component_spec_type_id=spec_type_id,
                        end_side=end_side,
                        bool_value=spec_data.get("bool_value"),
                        decimal_value=spec_data.get("decimal_value"),
                        text_value=spec_data.get("text_value"),
                    )
                    db.session.add(new_spec)

            # Delete specs no longer present
            for key, spec in existing_map.items():
                if key not in incoming_keys:
                    db.session.delete(spec)

        # Update options — delete all + re-create
        if "options" in data:
            incoming_option_type_ids = data["options"]  # list of component_option_type_id
            # Delete existing
            for opt in list(item.component_options):
                db.session.delete(opt)
            # Create new
            for opt_type_id in incoming_option_type_ids:
                new_opt = ComponentOption(
                    item_component_id=item_component_id,
                    component_option_type_id=opt_type_id,
                )
                db.session.add(new_opt)

        db.session.commit()

        # Refresh to get updated relations
        db.session.refresh(item)
        return ItemComponentSchema().dump(item)
    except Exception:
        db.session.rollback()
        raise
