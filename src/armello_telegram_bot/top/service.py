import logging
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..match.models import Clan, Hero, Player
from ..rating.models import (
    GeneralClanRating,
    GeneralHeroRating,
    PlayerClanRating,
    PlayerHeroRating,
    PlayerOverallRating,
)
from .schemas import ClanRatingModel, ClanTopPlayerModel, HeroRatingModel, PlayerRatingModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_top_players_overall(db: Session, limit: int = 10) -> List[PlayerRatingModel]:
    """Get top players by overall rating"""
    query = (
        db.query(
            Player.username,
            PlayerOverallRating.rating,
            PlayerOverallRating.wins,
            PlayerOverallRating.losses
        )
        .join(PlayerOverallRating, Player.id == PlayerOverallRating.player_id)
        .order_by(desc(PlayerOverallRating.rating))
        .limit(limit)
    )
    
    results = query.all()

    return [
        PlayerRatingModel(
            username=result.username,
            rating=result.rating,
            wins=result.wins,
            losses=result.losses,
            win_rate=result.wins / (result.wins + result.losses) if (result.wins + result.losses) > 0 else 0
        )
        for result in results
    ]


def get_top_players_by_hero(db: Session, hero_id: int, limit: int = 10) -> List[PlayerRatingModel]:
    """Get top players for a specific hero"""
    query = (
        db.query(
            Player.username,
            PlayerHeroRating.rating,
            PlayerHeroRating.wins,
            PlayerHeroRating.losses
        )
        .join(PlayerHeroRating, Player.id == PlayerHeroRating.player_id)
        .filter(PlayerHeroRating.hero_id == hero_id)
        .order_by(desc(PlayerHeroRating.rating))
        .limit(limit)
    )
    
    results = query.all()
    
    return [
        PlayerRatingModel(
            username=result.username,
            rating=result.rating,
            wins=result.wins,
            losses=result.losses,
            win_rate=result.wins / (result.wins + result.losses) if (result.wins + result.losses) > 0 else 0
        )
        for result in results
    ]


def get_top_players_by_clan(db: Session, clan_id: int, limit: int = 10) -> List[PlayerRatingModel]:
    """Get top players for a specific clan"""
    query = (
        db.query(
            Player.username,
            PlayerClanRating.rating,
            PlayerClanRating.wins,
            PlayerClanRating.losses
        )
        .join(PlayerClanRating, Player.id == PlayerClanRating.player_id)
        .filter(PlayerClanRating.clan_id == clan_id)
        .order_by(desc(PlayerClanRating.rating))
        .limit(limit)
    )
    
    results = query.all()
    
    return [
        PlayerRatingModel(
            username=result.username,
            rating=result.rating,
            wins=result.wins,
            losses=result.losses,
            win_rate=result.wins / (result.wins + result.losses) if (result.wins + result.losses) > 0 else 0
        )
        for result in results
    ]


def get_top_clan_player_title(db: Session, clan_id: int) -> Optional[ClanTopPlayerModel]:
    """Get top player of a clan with title"""
    clan = db.query(Clan).filter(Clan.id == clan_id).first()
    if not clan:
        return None
    
    top_player_rating = (
        db.query(
            Player.username,
            PlayerClanRating.rating
        )
        .join(PlayerClanRating, Player.id == PlayerClanRating.player_id)
        .filter(PlayerClanRating.clan_id == clan_id)
        .order_by(desc(PlayerClanRating.rating))
        .first()
    )
    
    if not top_player_rating:
        return None
    
    title_prefix = {
        1: "Старейшина",  # Bear
        2: "Архимаг",     # Rabbit
        3: "Командующий", # Rat
        4: "Предводитель" # Wolf
    }.get(clan_id, "Лидер")
    
    return ClanTopPlayerModel(
        username=top_player_rating.username,
        title=f"{title_prefix} {clan.name}"
    )


def get_top_heroes(db: Session, limit: int = 24) -> List[HeroRatingModel]:
    """Get top heroes by overall rating"""
    query = (
        db.query(
            Hero.id,
            Hero.name,
            GeneralHeroRating.rating,
            GeneralHeroRating.wins,
            GeneralHeroRating.losses
        )
        .join(GeneralHeroRating, Hero.id == GeneralHeroRating.hero_id)
        .order_by(desc(GeneralHeroRating.rating))
        .limit(limit)
    )
    
    results = query.all()
    
    return [
        HeroRatingModel(
            id=result.id,
            name=result.name,
            rating=result.rating,
            wins=result.wins,
            losses=result.losses,
            win_rate=result.wins / (result.wins + result.losses) if (result.wins + result.losses) > 0 else 0.0
        )
        for result in results
    ]


def get_top_clans(db: Session, limit: int = 6) -> List[ClanRatingModel]:
    """Get top clans by overall rating"""
    query = (
        db.query(
            Clan.id,
            Clan.name,
            GeneralClanRating.rating,
            GeneralClanRating.wins,
            GeneralClanRating.losses
        )
        .join(GeneralClanRating, Clan.id == GeneralClanRating.clan_id)
        .order_by(desc(GeneralClanRating.rating))
        .limit(limit)
    )
    
    results = query.all()
    
    return [
        ClanRatingModel(
            id=result.id,
            name=result.name,
            rating=result.rating,
            wins=result.wins,
            losses=result.losses,
            win_rate=result.wins / (result.wins + result.losses) if (result.wins + result.losses) > 0 else 0.0
        )
        for result in results
    ]


def read_clans(db: Session):
    """Read all clans"""
    return db.query(Clan).all()