"""bridge fix untuk id hantu

Revision ID: 4ed0c7d2bb05
Revises: None
Create Date: 2026-05-19

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '4ed0c7d2bb05'
down_revision = None  # Menandakan ini jembatan paling awal menuju file pull Anda

branch_labels = None
depends_on = None

def upgrade() -> None:
    # Sengaja dikosongkan karena tujuannya hanya menyambung rantai urutan file
    pass

def downgrade() -> None:
    pass