import base64

from app.con_sqlalchemy import ComponentTemplate
from app.repositories import component_template_repository
from app.app import db
from app.exception import MissingFieldsError, NotFoundError, ValidationError
from app.services.storage_service import upload_image
from concurrent.futures import ThreadPoolExecutor


def _decode_data_url(data_url: str):
    """Parse a data URL into (bytes, content_type). Raises ValidationError on bad format."""
    if not data_url.startswith("data:"):
        raise ValidationError("imageUrl must be a base64 data URL (data:<type>;base64,...)")
    try:
        header, encoded = data_url.split(",", 1)
        content_type = header.split(";")[0][5:]  # strip "data:"
        return base64.b64decode(encoded), content_type
    except Exception:
        raise ValidationError("imageUrl has invalid base64 data URL format")


def _upload_single_image(option):
    image_base64 = option.get("imageBase64")
    if image_base64 is None:
        raise MissingFieldsError("ไม่พบ field imageBase64")

    image_bytes, content_type = _decode_data_url(image_base64)
    key = f"/component_template/image_select/{option.get('key')}"
    object_key = upload_image(image_bytes, key, content_type=content_type)
    return option, object_key

def get_all_templates(data):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        result = component_template_repository.get_all_templates(page, per_page, search)
        return {"items": result["items"], "total": result["total"], "page": result["page"], "pages": result["pages"]}
    except Exception:
        raise


def get_template_by_id(template_id):
    try:
        template = component_template_repository.get_template_by_id(template_id)
        if not template:
            raise NotFoundError(f"Template {template_id} not found")
        return template
    except Exception:
        raise


def create_template(data):
    try:
        name = data.get("name")
        sections = data.get("sections")

        if not name:
            raise ValidationError("Template name is required")
        if not sections:
            raise ValidationError("Template sections are required")

        tasks = []

        # collect options that have a new image to upload
        for sec in sections:
            if sec.get("type") == "image_select":
                for opt in sec.get("options", []):
                    if opt.get("imageBase64"):
                        tasks.append(opt)

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(_upload_single_image, tasks))

        # assign uploaded object key and strip the raw base64
        for option, object_key in results:
            option["imageUrl"] = object_key
            option.pop("imageBase64", None)

        template = ComponentTemplate(
            name=name,
            sections=sections,
        )

        component_template_repository.create_template(template)
        db.session.commit()

        return template

    except Exception:
        db.session.rollback()
        raise


def update_template(template_id, data):
    try:
        template = component_template_repository.get_template_by_id(template_id)
        if not template:
            raise NotFoundError(f"Template {template_id} not found")

        if "name" in data:
            template.name = data["name"]

        if "sections" in data:
            sections = data["sections"]

            upload_targets = []
            for sec in sections:
                if sec.get("type") == "image_select":
                    for opt in sec.get("options", []):
                        if opt.get("imageBase64"):
                            upload_targets.append(opt)

            if upload_targets:
                with ThreadPoolExecutor(max_workers=5) as executor:
                    results = list(executor.map(_upload_single_image, upload_targets))

                # assign uploaded object key and strip the raw base64
                for option, object_key in results:
                    option["imageUrl"] = object_key
                    option.pop("imageBase64", None)

            template.sections = sections

        component_template_repository.update_template(template)
        db.session.commit()
        return template
    except Exception:
        db.session.rollback()
        raise


def delete_template(template_id):
    try:
        template = component_template_repository.get_template_by_id(template_id)
        if not template:
            raise NotFoundError(f"Template {template_id} not found")

        component_template_repository.delete_template(template_id)
        db.session.commit()
        return template
    except Exception:
        db.session.rollback()
        raise
