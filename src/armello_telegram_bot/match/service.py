from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from difflib import get_close_matches

from .models import Player, Hero, Match, MatchParticipant
from .schemas import MatchCreate


def get_player_by_username(db: Session, username: str):
    return db.query(Player).filter(Player.username == username).first()


def create_player(db: Session, username: str):
    player = Player(username=username)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def read_match(match_id: int, db: Session) -> Match:
    """
    Получает матч по ID.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    return match

def read_player(
    db: Session, id: Optional[int] = None,
    player_id: Optional[int] = None,
    username: Optional[str]= None
    ) -> Player:
    if id:
        return db.query(Player).filter(Player.id == id).first()
    if player_id:
        return db.query(Player).filter(Player.id == player_id).first()
    if username:
        return db.query(Player).filter(Player.username == username).first()


def create_match(db: Session, match_data: MatchCreate):
    """
    Создает запись матча и участников.
    match_data содержит: скриншот, тип победы, список участников и username победителя.
    """
    # Создаем матч
    match = Match(
        screenshot=match_data.screenshot,
        win_type=match_data.win_type,
        timestamp=datetime.utcnow()
    )
    db.add(match)
    db.commit()
    db.refresh(match)

    # Создаем записи участников матча
    for participant in match_data.participants:
        # Ищем игрока по username, если нет – создаем
        player = get_player_by_username(db, participant.username)
        if not player:
            player = create_player(db, participant.username)
        # Получаем героя – предполагается, что он уже существует в БД
        hero = db.query(Hero).filter(Hero.id == participant.hero_id).first()
        match_participant = MatchParticipant(
            match_id=match.id,
            player_id=player.id,
            hero_id=hero.id,
            is_winner=(participant.username == match_data.winner_username),
            win_type=match_data.win_type if (participant.username == match_data.winner_username) else None,
            # add score 4 if winner and -1 otherwise
            score=4 if (participant.username == match_data.winner_username) else -1
        )
        db.add(match_participant)

    db.commit()
    return match


def get_match_report(db: Session, match_id: int):
    """
    Формирует отчет по матчу для дальнейшей отправки в чат.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    report = {
        "match_id": match.id,
        "timestamp": match.timestamp,
        "screenshot": match.screenshot,
        "win_type": match.win_type.value,
        "participants": []
    }
    for p in match.participants:
        report["participants"].append({
            "username": p.player.username,
            "hero": p.hero.name,
            "is_winner": p.is_winner
        })
    return report


def read_hero(db: Session, hero_name: str) -> Hero:
    # Try exact case-insensitive match first

    print(hero_name)
    hero = db.query(Hero).filter(Hero.name.ilike(hero_name)).first()
    if hero:
        return hero

    # Try alias match
    hero = db.query(Hero).filter(Hero.alias.ilike(hero_name)).first()
    if hero:
        return hero

    # If no exact match, try fuzzy matching
    all_heroes = db.query(Hero).all()
    hero_names = [h.name.lower() for h in all_heroes]
    hero_aliases = [h.alias.lower() for h in all_heroes if h.alias]

    # Try to find closest match in names or aliases
    search_term = hero_name.lower()
    matches = get_close_matches(search_term, hero_names + hero_aliases, n=1, cutoff=0.6)

    if matches:
        closest_match = matches[0]
        # Find hero with matching name or alias
        return db.query(Hero).filter(
            (Hero.name.ilike(closest_match)) | 
            (Hero.alias.ilike(closest_match))
        ).first()

    return None


def remove_match(db: Session, match_id: int):
    """
    Removes a match and all its associated participants from the database.
    
    Args:
        db: Database session
        match_id: ID of the match to remove
        
    Returns:
        bool: True if match was found and deleted, False otherwise
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    
    if not match:
        return False
    
    # The match will cascade delete all participants due to the 
    # cascade="all, delete-orphan" relationship configuration
    db.delete(match)
    db.commit()
    
    return True