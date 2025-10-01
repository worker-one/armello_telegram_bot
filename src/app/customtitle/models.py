from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from ..database.core import Base


class CustomTitle(Base):
    """Model for custom titles assigned by channel owners"""
    __tablename__ = "custom_titles"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    title = Column(String(50), nullable=False)

    # Relationships
    player = relationship("Player", back_populates="custom_titles")
