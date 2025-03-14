import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models import Clan, Hero, Player, Match, MatchParticipant, WinTypeEnum

def init_clans_and_heroes(db_session: Session):
    # Define clans and their heroes with aliases
    clans_data = {
        ("Wolf Clan", "Клан Волков"): [("Thane", "Тейн"), ("River", "Ривер"), ("Fang", "Фанг"), ("Magna", "Магна")],
        ("Rabbit Clan", "Клан Кроликов"): [("Amber", "Эмбер"), ("Barnaby", "Барнаби"), ("Hargrave", "Харгрейв"), ("Elyssia", "Элиссия")],
        ("Rat Clan", "Клан Крыс"): [("Mercurio", "Меркурио"), ("Zosha", "Зоша"), ("Griotte", "Гриот"), ("Sargon", "Саргон")],
        ("Bear Clan", "Клан Медведей"): [("Sana", "Сана"), ("Brun", "Брун"), ("Ghor", "Гор"), ("Yordana", "Йордана")],
        ("Bandit Clan", "Клан Разбойников"): [("Twiss", "Твисс"), ("Horace", "Хорас"), ("Scarlet", "Скарлет"), ("Sylas", "Сайлас")],
        ("Dragon Clan", "Клан Драконов"): [("Volodar", "Володар"), ("Agniya", "Агния"), ("Oxana", "Оксана"), ("Nazar", "Назар")]
    }

    # Create and add clans and heroes
    for (clan_alias, clan_name), heroes in clans_data.items():
        # Create clan
        clan = Clan(name=clan_name, alias=clan_alias)
        db_session.add(clan)
        db_session.flush()  # Flush to get clan.id

        # Create heroes for the clan
        for hero_name, hero_alias in heroes:
            hero = Hero(name=hero_name, alias=hero_alias, clan_id=clan.id)
            db_session.add(hero)

    # Commit all changes
    db_session.commit()

def init_players(db_session: Session, count=10):
    """Initialize test players"""
    usernames = [f"player{i}" for i in range(1, count + 1)]
    
    for i, username in enumerate(usernames, 1):
        player = Player(
            user_id=i * 100,  # Fake user_id
            username=username
        )
        db_session.add(player)
    
    player = Player(
        user_id=954020212,
        username="konverner"
    )
    db_session.add(player)
        
    db_session.commit()
    return usernames


def init_matches(db_session: Session, match_count=50):
    """Initialize test matches with participants"""
    # Get all players and heroes
    players = db_session.query(Player).all()
    heroes = db_session.query(Hero).all()
    
    if not players or len(players) < 4:
        raise ValueError("Need at least 4 players to create matches")
    
    win_types = list(WinTypeEnum)
    
    # Create matches
    for i in range(match_count):
        # Random date within the last 3 months
        match_date = datetime.utcnow() - timedelta(days=random.randint(0, 90))
        
        win_type = random.choice(win_types)
        
        match = Match(
            timestamp=match_date,
            screenshot=f"screenshot_{i+1}.jpg",
            win_type=win_type
        )
        db_session.add(match)
        db_session.flush()  # Get match.id
        
        # Select 4 random players for this match
        match_players = random.sample(players, 4)
        # Select 4 random heroes for this match (no duplicates)
        match_heroes = random.sample(heroes, 4)
        
        # Randomly select a winner
        winner_index = random.randint(0, 3)
        
        # Create participants
        for j, (player, hero) in enumerate(zip(match_players, match_heroes)):
            is_winner = (j == winner_index)
            if player.id == 954020212:
                is_winner = True
            participant = MatchParticipant(
                match_id=match.id,
                player_id=player.id,
                hero_id=hero.id,
                is_winner=is_winner,
                win_type=win_type if is_winner else None
            )
            db_session.add(participant)
    
    db_session.commit()

def init_test_data(db_session: Session):
    """Initialize all test data"""
    # First check if data already exists to avoid duplicates
    clan_count = db_session.query(Clan).count()
    
    if clan_count == 0:
        print("Initializing clans and heroes...")
        init_clans_and_heroes(db_session)
    
    player_count = db_session.query(Player).count()
    if player_count == 0:
        print("Initializing players...")
        init_players(db_session, count=10)
    
    match_count = db_session.query(Match).count()
    if match_count == 0:
        print("Initializing matches...")
        init_matches(db_session, match_count=20)
    
    print("Test data initialization complete!")

# Function to clear all data (useful for testing)
def clear_all_data(db_session: Session):
    """Remove all data from all tables"""
    db_session.query(MatchParticipant).delete()
    db_session.query(Match).delete()
    db_session.query(Player).delete()
    db_session.query(Hero).delete()
    db_session.query(Clan).delete()
    db_session.commit()
    print("All data cleared!")
