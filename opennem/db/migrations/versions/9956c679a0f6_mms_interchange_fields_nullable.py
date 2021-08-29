# pylint: disable=no-member
"""
mms mnsp_interconnector fields nullable

Revision ID: 9956c679a0f6
Revises: 1825bf65f16a
Create Date: 2021-08-29 20:08:53.682683

"""
import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9956c679a0f6"
down_revision = "1825bf65f16a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "mnsp_interconnector",
        "from_region_tlf",
        existing_type=sa.Numeric(),
        nullable=True,
        schema="mms",
    )
    op.alter_column(
        "mnsp_interconnector",
        "to_region_tlf",
        existing_type=sa.Numeric(),
        nullable=True,
        schema="mms",
    )


def downgrade() -> None:
    op.alter_column(
        "mnsp_interconnector",
        "from_region_tlf",
        existing_type=sa.Numeric(),
        nullable=False,
        schema="mms",
    )
    op.alter_column(
        "mnsp_interconnector",
        "to_region_tlf",
        existing_type=sa.Numeric(),
        nullable=False,
        schema="mms",
    )
