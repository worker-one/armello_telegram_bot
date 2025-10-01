from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table

from sqlalchemy.orm import relationship
from ..models import Base


class Title(Base):
    """Title model for storing custom titles for top players and clans"""
    __tablename__ = 'titles'
    id = Column(Integer, primary_key=True)
    category = Column(String, nullable=False)  # 'overall', 'clan', 'custom'
    clan_id = Column(Integer, ForeignKey('clans.id'), nullable=True)
    title = Column(String, nullable=False, default="Best Player")  # The custom title text
    default = Column(Boolean, nullable=False, default=True)  # Whether this is a default title
    player_id = Column(Integer, ForeignKey('players.id'))

    player = relationship("Player", back_populates="titles")
