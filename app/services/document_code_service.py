import re
from datetime import datetime
from app.con_sqlalchemy import DocumentCodeList, GenNumberConfig
from app.repositories import document_code_repository
from app.app import db
from app.exception import NotFoundError, UniqueError


def get_document_code_list():
    try:
        all_types = document_code_repository.get_all_document_code_types()
        own_configs = document_code_repository.get_all_gen_number_configs()

        all_obj = [
            {
                "document_code_id": t.document_code_id,
                "gen_number_type": t.gen_number_type,
                "description": t.description,
            }
            for t in all_types
        ]

        from app.ma_sqlalchemy import GenNumberConfigSchema
        own_obj = GenNumberConfigSchema(many=True).dump(own_configs)

        return {"own": own_obj, "all": all_obj}
    except Exception:
        raise


def create_document_code(data):
    try:
        gen_number_type = data.get("gen_number_type")
        existing = document_code_repository.get_gen_number_config_by_type(gen_number_type)
        if existing:
            raise UniqueError(f"Document code type '{gen_number_type}' already exists")

        config = GenNumberConfig(
            gen_number_type=gen_number_type,
            gen_number_prefix=data.get("gen_number_prefix"),
            gen_number_format=data.get("gen_number_format"),
            gen_number_current=data.get("gen_number_current", 0),
            year_buddhist=data.get("year_buddhist", True),
            document_code_id=data.get("document_code_id"),
        )
        db.session.add(config)
        db.session.commit()
        return config
    except Exception:
        db.session.rollback()
        raise


def edit_document_code(gen_number_id, data):
    try:
        config = document_code_repository.get_gen_number_config_by_id(gen_number_id)
        if not config:
            raise NotFoundError(f"Gen number config {gen_number_id} not found")

        for field in ("gen_number_type", "gen_number_prefix", "gen_number_format", "gen_number_current", "year_buddhist"):
            if field in data:
                setattr(config, field, data[field])

        db.session.commit()
        return config
    except Exception:
        db.session.rollback()
        raise


# ──────────────────────────────────────────────
# Number Generation
# ──────────────────────────────────────────────

def generate_number(gen_number_type, count=1):
    """
    Generate `count` running numbers for the given gen_number_type.
    Returns a single string when count=1, or a list when count>1.
    """
    try:
        config = document_code_repository.get_gen_number_config_by_type(gen_number_type)
        if not config:
            raise NotFoundError(f"ไม่พบการตั้งแค่เลขเอกสารสำหรับ '{gen_number_type}' กรุณาติดต่อผู้ดูแลให้กำหนด format เอกสารประเภทนี้ก่อน")

        gen_numbers = []
        for _ in range(count):
            config.gen_number_current += 1
            current_number = config.gen_number_current

            now = datetime.now()
            year = now.year + 543 if config.year_buddhist else now.year
            fmt = config.gen_number_format or ""

            fmt = re.sub(r'(?<!\*)YYYY', str(year), fmt)
            fmt = re.sub(r'(?<!\*)YY', str(year)[-2:], fmt)
            fmt = re.sub(r'(?<!\*)MM', f"{now.month:02d}", fmt)
            fmt = re.sub(r'(?<!\*)DD', f"{now.day:02d}", fmt)
            fmt = re.sub(r'(?<!\*)PREFIX', config.gen_number_prefix or "", fmt)

            match = re.search(r'(?<!\*)X+', fmt)
            if match:
                x_count = len(match.group(0))
                running = str(current_number).zfill(x_count)
                fmt = re.sub(r'(?<!\*)X+', running, fmt, count=1)

            fmt = fmt.replace("*", "")
            gen_numbers.append(fmt)

        db.session.commit()

        if count == 1:
            return gen_numbers[0]
        return gen_numbers
    except Exception:
        db.session.rollback()
        raise
