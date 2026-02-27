from sqlalchemy import inspect
from alembic import op


def column_exists(table_name, column_name):
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def constraint_exists(table_name, constraint_name):
    conn = op.get_bind()
    inspector = inspect(conn)
    constraints = [fk["name"] for fk in inspector.get_foreign_keys(table_name)]
    return constraint_name in constraints