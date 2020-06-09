"""scada_dispatch

Revision ID: 01d74b813948
Revises: 
Create Date: 2020-06-09 17:47:32.424246

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "01d74b813948"
down_revision = None
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()


def upgrade_opennem():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "nem_dispatch_unit_scada",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("SETTLEMENTDATE", sa.DateTime(), nullable=True),
        sa.Column("DUID", sa.Text(), nullable=True),
        sa.Column(
            "SCADAVALUE", sa.NUMERIC(precision=10, scale=6), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_nem_dispatch_unit_scada_DUID"),
        "nem_dispatch_unit_scada",
        ["DUID"],
        unique=False,
    )
    op.create_index(
        op.f("ix_nem_dispatch_unit_scada_SETTLEMENTDATE"),
        "nem_dispatch_unit_scada",
        ["SETTLEMENTDATE"],
        unique=False,
    )
    op.create_index(
        "nem_dispatch_unit_scada_uniq",
        "nem_dispatch_unit_scada",
        ["SETTLEMENTDATE", "DUID"],
        unique=True,
    )
    # ### end Alembic commands ###


def downgrade_opennem():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        "nem_dispatch_unit_scada_uniq", table_name="nem_dispatch_unit_scada"
    )
    op.drop_index(
        op.f("ix_nem_dispatch_unit_scada_SETTLEMENTDATE"),
        table_name="nem_dispatch_unit_scada",
    )
    op.drop_index(
        op.f("ix_nem_dispatch_unit_scada_DUID"),
        table_name="nem_dispatch_unit_scada",
    )
    op.drop_table("nem_dispatch_unit_scada")
    # ### end Alembic commands ###
