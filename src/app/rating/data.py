import random

from sqlalchemy.orm import Session

from ..match.models import Clan, Hero, Player
from .models import GeneralClanRating, GeneralHeroRating, PlayerClanRating, PlayerHeroRating, PlayerOverallRating


def init_rating_test_data(db_session: Session):
    """Create and populate database with test data."""

    players = db_session.query(Player).all()
    heroes = db_session.query(Hero).all()
    clans = db_session.query(Clan).all()
    
    # Create player overall ratings
    for player in players:
        wins = random.randint(1, 30)
        losses = random.randint(1, 20)
        rating = 1000 + (wins * 25) - (losses * 20)
        
        db_session.add(PlayerOverallRating(
            player_id=player.id,
            rating=rating,
            wins=wins,
            losses=losses
        ))
    
    # Create player hero ratings
    for player in players:
        # Each player has ratings for 3-5 random heroes
        for hero in random.sample(heroes, random.randint(3, min(5, len(heroes)))):
            wins = random.randint(0, 15)
            losses = random.randint(0, 10)
            rating = 1000 + (wins * 25) - (losses * 20)
            
            db_session.add(PlayerHeroRating(
                player_id=player.id,
                hero_id=hero.id,
                rating=rating,
                wins=wins,
                losses=losses
            ))

    # Create player clan ratings
    for player in players:
        # Each player has ratings for 2-4 random clans
        for clan in random.sample(clans, random.randint(2, len(clans))):
            wins = random.randint(0, 20)
            losses = random.randint(0, 15)
            rating = 1000 + (wins * 25) - (losses * 20)

            db_session.add(PlayerClanRating(
                player_id=player.id,
                clan_id=clan.id,
                clan_name=clan.name,
                rating=rating,
                wins=wins,
                losses=losses
            ))

    # Create general hero ratings
    for hero in heroes:
        wins = random.randint(5, 50)
        losses = random.randint(5, 40)
        rating = 1000 + (wins * 10) - (losses * 8)
        
        db_session.add(GeneralHeroRating(
            hero_id=hero.id,
            rating=rating,
            wins=wins,
            losses=losses
        ))
    
    # Create general clan ratings
    for clan in clans:
        wins = random.randint(10, 100)
        losses = random.randint(10, 80)
        rating = 1000 + (wins * 10) - (losses * 8)
        
        db_session.add(GeneralClanRating(
            clan_id=clan.id,
            clan_name=clan.name,
            rating=rating,
            wins=wins,
            losses=losses
        ))
    
    db_session.commit()
    print(f"Test data created successfully!")
