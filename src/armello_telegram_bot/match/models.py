from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..models import Base


class WinTypeEnum(str, Enum):
    prestige = "prestige"
    murder = "murder"
    decay = "decay"
    stones = "stones"


class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    username = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=True)

    # Связь игрока с пользователем бота
    user = relationship("User", back_populates="player")
    # Связь с участием в матчах
    matches = relationship("MatchParticipant", back_populates="player")
    # Связь с титулами
    titles = relationship("Title", back_populates="player")
    # Связь с кастомными титулами
    custom_titles = relationship("CustomTitle", back_populates="player")


class Clan(Base):
    __tablename__ = 'clans'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    alias = Column(String, unique=True, nullable=True)
    # Каждый клан имеет 4 героя
    heroes = relationship("Hero", back_populates="clan")

    # Каждый клан имеет статистику
    clan_stats = relationship("ClanStats", back_populates="clan")


class Hero(Base):
    __tablename__ = 'heroes'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    alias = Column(String, unique=True, nullable=True)
    clan_id = Column(Integer, ForeignKey('clans.id'))
    clan = relationship("Clan", back_populates="heroes")
    participants = relationship("MatchParticipant", back_populates="hero")

    # Каждый герой имеет статистику
    stats = relationship("HeroStats", back_populates="hero")


class Match(Base):
    __tablename__ = 'matches'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    screenshot = Column(String)  # путь к файлу или URL скриншота
    win_type = Column(SQLEnum(WinTypeEnum), nullable=False)
    # Каждый матч состоит из 4 участников
    participants = relationship("MatchParticipant", back_populates="match", cascade="all, delete-orphan")


class MatchParticipant(Base):
    __tablename__ = 'match_participants'
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey('matches.id'))
    player_id = Column(Integer, ForeignKey('players.id'))
    hero_id = Column(Integer, ForeignKey('heroes.id'))
    is_winner = Column(Boolean, default=False)
    win_type = Column(SQLEnum(WinTypeEnum), nullable=True)
    score = Column(Integer, default=0)

    match = relationship("Match", back_populates="participants")
    player = relationship("Player", back_populates="matches")
    hero = relationship("Hero", back_populates="participants")
