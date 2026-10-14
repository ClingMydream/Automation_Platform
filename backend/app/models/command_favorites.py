from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class PersonalCommandFavorite(Base):
    """Per-user favorites; leave legacy shared snippet flags untouched."""
    __tablename__ = "personal_command_favorites"
    __table_args__ = (UniqueConstraint("owner_user_id", "command_id", name="uq_personal_command_favorite"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), index=True)
    command_id: Mapped[int] = mapped_column(ForeignKey("command_snippets.id", ondelete="CASCADE"), index=True)
