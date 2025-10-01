from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship


from ..models import Base, TimeStampMixin


class HeroStats(Base, TimeStampMixin):
    __tablename__ = 'hero_stats'
    
    id = Column(Integer, primary_key=True)
    hero_id = Column(Integer, ForeignKey('heroes.id'), unique=True)
    score = Column(Integer, default=0)
    total_matches = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    prestige_wins = Column(Integer, default=0)
    murder_wins = Column(Integer, default=0)
    decay_wins = Column(Integer, default=0)
    stones_wins = Column(Integer, default=0)
    
    # Relationship to Hero
    hero = relationship("Hero", back_populates="stats")
