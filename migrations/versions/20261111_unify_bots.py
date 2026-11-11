"""Add ticketing and support without changing existing tables or importing legacy records.

Revision ID: 20261111_unify_bots
Revises: 6dc1e0d1c9de
"""
from alembic import op
import sqlalchemy as sa
from app.features.ticketing.schema import NEW_TABLE_NAMES, metadata

revision = "20261111_unify_bots"
down_revision = "6dc1e0d1c9de"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not op.get_context().as_sql:
        target_schema=bind.get_execution_options().get("schema_translate_map",{}).get(None,"public")
        if bind.execute(sa.text("SELECT current_schema()")).scalar_one()!=target_schema:
            raise RuntimeError("Schema/search_path mismatch; refusing to create tables")
        existing = set(sa.inspect(bind).get_table_names(schema=target_schema))
        collisions = existing.intersection(NEW_TABLE_NAMES)
        if collisions:
            raise RuntimeError("Integration tables already exist; inspect before migrating: " + ", ".join(sorted(collisions)))
    for name in NEW_TABLE_NAMES:
        metadata.tables[name].create(bind, checkfirst=False)


def downgrade():
    bind = op.get_bind()
    for name in NEW_TABLE_NAMES:
        if bind.execute(sa.select(sa.func.count()).select_from(metadata.tables[name])).scalar():
            raise RuntimeError("Refusing to delete integration data. Export it and plan rollback explicitly.")
    for name in reversed(NEW_TABLE_NAMES):
        metadata.tables[name].drop(bind)
