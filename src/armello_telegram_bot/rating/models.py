from enum import Enum

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint

from ..models import Base


class WinTypeEnum(str, Enum):
    prestige = "prestige"
    murder = "murder"
    decay = "decay"
    stones = "stones"


class PlayerOverallRating(Base):
    __tablename__ = 'player_overall_ratings'
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'), unique=True)
    rating = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    titles = Column(String, default='')
    custom_titles = Column(String, default='')

    prestige_wins = Column(Integer, default=0)
    murder_wins = Column(Integer, default=0)
    decay_wins = Column(Integer, default=0)
    stones_wins = Column(Integer, default=0)

    @property
    def win_rate(self):
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0


class PlayerHeroRating(Base):
    __tablename__ = 'player_hero_ratings'
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'))
    hero_id = Column(Integer, ForeignKey('heroes.id'))
    rating = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)

    prestige_wins = Column(Integer, default=0)
    murder_wins = Column(Integer, default=0)
    decay_wins = Column(Integer, default=0)
    stones_wins = Column(Integer, default=0)

    __table_args__ = (UniqueConstraint('player_id', 'hero_id', name='uix_player_hero'),)

    @property
    def win_rate(self):
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0


class PlayerClanRating(Base):
    __tablename__ = 'player_clan_ratings'
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'))
    clan_id = Column(Integer, ForeignKey('clans.id'))
    clan_name = Column(String, nullable=False)
    rating = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)

    prestige_wins = Column(Integer, default=0)
    murder_wins = Column(Integer, default=0)
    decay_wins = Column(Integer, default=0)
    stones_wins = Column(Integer, default=0)

    __table_args__ = (UniqueConstraint('player_id', 'clan_id', name='uix_player_clan'),)

    @property
    def win_rate(self):
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0

class GeneralHeroRating(Base):
    __tablename__ = 'general_hero_ratings'
    id = Column(Integer, primary_key=True)
    hero_id = Column(Integer, ForeignKey('heroes.id'), unique=True)
    rating = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)

    @property
    def win_rate(self):
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0

class GeneralClanRating(Base):
    __tablename__ = 'general_clan_ratings'
    id = Column(Integer, primary_key=True)
    clan_id = Column(Integer, ForeignKey('clans.id'), unique=True)
    clan_name = Column(String, nullable=False)
    rating = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    
    prestige_wins = Column(Integer, default=0)
    murder_wins = Column(Integer, default=0)
    decay_wins = Column(Integer, default=0)
    stones_wins = Column(Integer, default=0)

    @property
    def win_rate(self):
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0
