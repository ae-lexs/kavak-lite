"""Fix mileage_km typo

Revision ID: a8d7f2f9f521
Revises: 28f544bafddd
Create Date: 2026-01-07 23:13:52.985804

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a8d7f2f9f521"
down_revision: Union[str, Sequence[str], None] = "28f544bafddd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename column from milleage_km to mileage_km
    op.alter_column("cars", "milleage_km", new_column_name="mileage_km")


def downgrade() -> None:
    """Downgrade schema."""
    # Rename column back from mileage_km to milleage_km
    op.alter_column("cars", "mileage_km", new_column_name="milleage_km")
