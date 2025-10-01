from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


from ..models import Base, TimeStampMixin


class ClanStats(Base, TimeStampMixin):
    __tablename__ = 'clan_stats'

    id = Column(Integer, primary_key=True)
    clan_name = Column(String, nullable=False, index=True)
    total_games = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)

    # Win types
    prestige_wins = Column(Integer, default=0)
    king_slayer_wins = Column(Integer, default=0)
    rot_wins = Column(Integer, default=0)
    spirit_stone_wins = Column(Integer, default=0)

    # Top one player
    best_player_id = Column(Integer, ForeignKey('players.id'))
    best_player_username = Column(String)
    best_player_title = Column(String)

    # Relationships
    clan_id = Column(Integer, ForeignKey('clans.id'))
    clan = relationship('Clan', back_populates='clan_stats')

    def __repr__(self):
        return f"<ClanStats(clan_name='{self.clan_name}', wins={self.wins}, losses={self.losses})>"
