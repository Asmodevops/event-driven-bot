from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        default=None,
        server_default=None,
        onupdate=func.now(),
        server_onupdate=func.now(),
    )
