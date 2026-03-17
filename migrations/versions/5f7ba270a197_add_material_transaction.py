"""add material transaction

Revision ID: 5f7ba270a197
Revises: ad561750863e
Create Date: 2026-03-05 09:46:16.409770

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '5f7ba270a197'
down_revision = 'ad561750863e'
branch_labels = None
depends_on = None


def upgrade():
    pass
    # op.drop_table('t_pbi_transaction')                 # 1. ทุบตารางหลาน
    # op.drop_table('t_product_backoffice_inventory')    # 2. ทุบตารางลูก
    # op.drop_table('m_product')                         # 3. ทุบตารางแม่

    # op.create_table('t_material_transaction',
    #     sa.Column('transaction_id', sa.Integer(), autoincrement=True, nullable=False),
    #     sa.Column('material_list_id', sa.Integer(), nullable=False),
    #     sa.Column('amount', sa.Integer(), nullable=False),
    #     sa.Column('type', sa.String(length=24), nullable=False),
    #     sa.Column('related_document_code', sa.String(length=128), nullable=False),
        
    #     # ฟิลด์จาก AuditMixin
    #     sa.Column('created_by', sa.String(length=80), nullable=True),
    #     sa.Column('updated_by', sa.String(length=80), nullable=True),
    #     sa.Column('created_date', sa.DateTime(), nullable=True),
    #     sa.Column('updated_date', sa.DateTime(), nullable=True),
        
    #     # ผูก Foreign Key ไปหาตารางแม่
    #     sa.ForeignKeyConstraint(['material_list_id'], ['t_material_list.material_list_id'], ondelete='CASCADE'),
    #     sa.PrimaryKeyConstraint('transaction_id')
    # )


def downgrade():
    # 🌟 เวลาถอยหลัง ก็ให้ลบตารางใหม่ทิ้ง
    op.drop_table('t_material_transaction')
    
    # และสร้างตารางเก่ากลับมา (ตามที่ Alembic เจนมาให้เลย)
    op.create_table('m_product',
        sa.Column('product_id', mysql.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('product_code', mysql.VARCHAR(length=128), nullable=False),
        sa.Column('product_name', mysql.VARCHAR(length=255), nullable=False),
        sa.Column('description', mysql.TEXT(), nullable=True),
        sa.Column('created_by', mysql.VARCHAR(length=80), nullable=True),
        sa.Column('updated_by', mysql.VARCHAR(length=80), nullable=True),
        sa.Column('created_date', mysql.DATETIME(), nullable=True),
        sa.Column('updated_date', mysql.DATETIME(), nullable=True),
        sa.PrimaryKeyConstraint('product_id'),
        mysql_collate='utf8mb4_0900_ai_ci',
        mysql_default_charset='utf8mb4',
        mysql_engine='InnoDB'
    )
