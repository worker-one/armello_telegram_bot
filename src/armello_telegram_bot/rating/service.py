import logging
from typing import Optional

from sqlalchemy.orm import Session

from ..match.models import Clan, Player
from .models import GeneralClanRating, GeneralHeroRating, PlayerClanRating, PlayerHeroRating, PlayerOverallRating


def update_ratings_after_match(db: Session, match):
    """
    Обновление рейтингов на основании результатов матча.
    Для простоты предположим, что победителю начисляется +10 очков, а проигравшим – -5 очков.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Updating ratings for match {match.id}")

    winner_points = 10
    loser_points = -5

    for participant in match.participants:
        player_id = participant.player_id
        hero_id = participant.hero_id
        clan_id = participant.hero.clan_id
        print(type(clan_id), "clan_id")
        clan = db.query(Clan).filter_by(id=clan_id).first()

        logger.info(f"Processing participant: player_id={player_id}, hero_id={hero_id}, clan_id={clan.id}")

        # Обновляем общий рейтинг игрока
        overall = db.query(PlayerOverallRating).filter_by(player_id=player_id).first()
        if not overall:
            logger.info(f"Creating new overall rating for player {player_id}")
            overall = PlayerOverallRating(player_id=player_id, rating=0, wins=0, losses=0)
            db.add(overall)

        if participant.is_winner:
            overall.rating += winner_points
            overall.wins += 1
        else:
            overall.rating += loser_points
            overall.losses += 1
        logger.info(f"Updated overall rating for player {player_id}: rating={overall.rating}")

        # Рейтинг игрока на конкретном герое
        ph = db.query(PlayerHeroRating).filter_by(player_id=player_id, hero_id=hero_id).first()
        if not ph:
            logger.info(f"Creating new hero rating for player {player_id}, hero {hero_id}")
            ph = PlayerHeroRating(player_id=player_id, hero_id=hero_id, rating=0, wins=0, losses=0)
            db.add(ph)
        if participant.is_winner:
            ph.rating += winner_points
            ph.wins += 1
        else:
            ph.rating += loser_points
            ph.losses += 1

        # Рейтинг игрока в конкретном клане
        pc = db.query(PlayerClanRating).filter_by(player_id=player_id, clan_id=clan_id).first()
        if not pc:
            logger.info(f"Creating new clan rating for player {player_id}, clan {clan.id}")
            pc = PlayerClanRating(player_id=player_id, clan_id=clan_id, clan_name=clan.name, rating=0, wins=0, losses=0)
            db.add(pc)
        if participant.is_winner:
            pc.rating += winner_points
            pc.wins += 1
        else:
            pc.rating += loser_points
            pc.losses += 1

        # Общий рейтинг героя
        gh = db.query(GeneralHeroRating).filter_by(hero_id=hero_id).first()
        if not gh:
            logger.info(f"Creating new general hero rating for hero {hero_id}")
            gh = GeneralHeroRating(hero_id=hero_id, rating=0, wins=0, losses=0)
            db.add(gh)
        if participant.is_winner:
            gh.rating += winner_points
            gh.wins += 1
        else:
            gh.rating += loser_points
            gh.losses += 1

        # Общий рейтинг клана
        gc = db.query(GeneralClanRating).filter_by(clan_id=clan_id).first()
        if not gc:
            logger.info(f"Creating new general clan rating for clan {clan.id}")
            gc = GeneralClanRating(clan_id=clan_id, clan_name=clan.name, rating=0, wins=0, losses=0)
            db.add(gc)
        if participant.is_winner:
            gc.rating += winner_points
            gc.wins += 1
        else:
            gc.rating += loser_points
            gc.losses += 1

    try:
        db.commit()
        logger.info("Successfully committed rating updates")
    except Exception as e:
        logger.error(f"Error committing rating updates: {e}")
        raise

def read_player(
    db: Session, player_id: Optional[int] = None,
    username: Optional[str] = None,
    user_id: Optional[int] = None
    
    ):
    if user_id:
        return db.query(Player).filter_by(user_id=user_id).first()
    if player_id:
        return db.query(Player).filter_by(id=player_id).first()
    if username:
        return db.query(Player).filter_by(username=username).first()

def read_clans(db: Session):
    return db.query(Clan).all()

def read_general_clan_rating(db: Session):
    return db.query(GeneralClanRating).all()

def read_clan(db: Session, clan_id: int):
    return db.query(GeneralClanRating).filter_by(clan_id=clan_id).first()

def read_heroes(db: Session):
    return db.query(GeneralHeroRating).all()

def read_general_hero_rating(db: Session, hero_id: int):
    return db.query(GeneralHeroRating).filter_by(hero_id=hero_id).first()

def get_player_overall_rating(db: Session, player_id: int):
    return db.query(PlayerOverallRating).filter_by(player_id=player_id).first()

def get_player_hero_rating(db: Session, player_id: int, hero_id: int):
    return db.query(PlayerHeroRating).filter_by(player_id=player_id, hero_id=hero_id).first()

def get_player_clan_rating(db: Session, player_id: int, clan_id: int):
    return db.query(PlayerClanRating).filter_by(player_id=player_id, clan_id=clan_id).first()

def get_general_hero_rating(db: Session, hero_id: int):
    return db.query(GeneralHeroRating).filter_by(hero_id=hero_id).first()

def get_general_clan_rating(db: Session, clan_id: int):
    return db.query(GeneralClanRating).filter_by(clan_id=clan_id).first()
