
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey

from ..models import Base


class Role(Base):
    """ System roles : user or admin """
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)


class User(Base):
    """User model"""

    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    first_message_timestamp = Column(DateTime)
    last_message_timestamp = Column(DateTime)
    username = Column(String)
    player_id = Column(Integer, ForeignKey("players.id"))
    first_name = Column(String)
    last_name = Column(String)
    phone_number = Column(String)
    lang = Column(String, default="ru")
    role_id = Column(Integer, ForeignKey("roles.id"), default=2)
    is_blocked = Column(Boolean, default=False)

    role = relationship("Role", backref="users", lazy="joined", foreign_keys=[role_id])
    player = relationship("Player", back_populates="user")


