import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..rating.models import (
    PlayerOverallRating,
    PlayerHeroRating,
    PlayerClanRating,
    GeneralHeroRating,
    GeneralClanRating,
    WinTypeEnum
)
from ..match.models import Player, Hero, Clan


def get_top_players(
    db: Session,
    limit: int = 10,
    offset: int = 0,
    sort_by: str = "rating",
    clan_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get top players based on their overall rating.
    
    Args:
        db: Database session
        limit: Number of players to return
        offset: Offset for pagination
        sort_by: Field to sort by (rating, wins, win_rate)
        clan_id: Filter by clan ID
        
    Returns:
        List of player data dictionaries
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Getting top {limit} players sorted by {sort_by}")
    
    query = db.query(
        PlayerOverallRating,
        Player
    ).join(
        Player, PlayerOverallRating.player_id == Player.id
    )
    
    if clan_id:
        # Filter by players who have played the specified clan
        clan_players = db.query(PlayerClanRating.player_id).filter_by(clan_id=clan_id)
        query = query.filter(PlayerOverallRating.player_id.in_(clan_players))
    
    # Apply sorting
    if sort_by == "win_rate":
        # For win rate sorting, we need to calculate it in the query
        # We only consider players with at least 10 games for win rate ranking
        query = query.filter((PlayerOverallRating.wins + PlayerOverallRating.losses) >= 10)
        query = query.order_by(desc(PlayerOverallRating.wins / (PlayerOverallRating.wins + PlayerOverallRating.losses)))
    elif sort_by == "wins":
        query = query.order_by(desc(PlayerOverallRating.wins))
    else:  # Default to rating
        query = query.order_by(desc(PlayerOverallRating.rating))
    
    # Apply pagination
    results = query.limit(limit).offset(offset).all()
    
    # Format results
    top_players = []
    for rating, player in results:
        top_players.append({
            "player_id": player.id,
            "username": player.username,
            "rating": rating.rating,
            "wins": rating.wins,
            "losses": rating.losses,
            "win_rate": round(rating.win_rate * 100, 1),
            "prestige_wins": rating.prestige_wins,
            "murder_wins": rating.murder_wins,
            "decay_wins": rating.decay_wins,
            "stones_wins": rating.stones_wins,
            "titles": rating.titles,
            "custom_titles": rating.custom_titles
        })
    
    return top_players


def get_top_heroes(
    db: Session,
    limit: int = 10,
    offset: int = 0,
    sort_by: str = "rating",
    min_games: int = 10
) -> List[Dict[str, Any]]:
    """
    Get top heroes based on their general rating.
    
    Args:
        db: Database session
        limit: Number of heroes to return
        offset: Offset for pagination
        sort_by: Field to sort by (rating, wins, win_rate)
        min_games: Minimum number of games required for ranking
        
    Returns:
        List of hero data dictionaries
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Getting top {limit} heroes sorted by {sort_by}")
    
    query = db.query(
        GeneralHeroRating,
        Hero
    ).join(
        Hero, GeneralHeroRating.hero_id == Hero.id
    ).filter(
        (GeneralHeroRating.wins + GeneralHeroRating.losses) >= min_games
    )
    
    # Apply sorting
    if sort_by == "win_rate":
        query = query.order_by(desc(GeneralHeroRating.wins / (GeneralHeroRating.wins + GeneralHeroRating.losses)))
    elif sort_by == "wins":
        query = query.order_by(desc(GeneralHeroRating.wins))
    else:  # Default to rating
        query = query.order_by(desc(GeneralHeroRating.rating))
    
    # Apply pagination
    results = query.limit(limit).offset(offset).all()
    
    # Format results
    top_heroes = []
    for rating, hero in results:
        total_games = rating.wins + rating.losses
        win_rate = rating.win_rate * 100 if total_games > 0 else 0
        
        top_heroes.append({
            "hero_id": hero.id,
            "name": hero.name,
            "rating": rating.rating,
            "wins": rating.wins,
            "losses": rating.losses,
            "total_games": total_games,
            "win_rate": round(win_rate, 1),
            "clan_id": hero.clan_id
        })
    
    return top_heroes


def get_top_clans(
    db: Session,
    limit: int = 4,  # Default to 4 since there are 4 clans in Armello
    sort_by: str = "rating"
) -> List[Dict[str, Any]]:
    """
    Get top clans based on their general rating.
    
    Args:
        db: Database session
        limit: Number of clans to return
        sort_by: Field to sort by (rating, wins, win_rate)
        
    Returns:
        List of clan data dictionaries
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Getting top {limit} clans sorted by {sort_by}")
    
    query = db.query(
        GeneralClanRating,
        Clan
    ).join(
        Clan, GeneralClanRating.clan_id == Clan.id
    )
    
    # Apply sorting
    if sort_by == "win_rate":
        query = query.order_by(desc(GeneralClanRating.wins / (GeneralClanRating.wins + GeneralClanRating.losses)))
    elif sort_by == "wins":
        query = query.order_by(desc(GeneralClanRating.wins))
    else:  # Default to rating
        query = query.order_by(desc(GeneralClanRating.rating))
    
    # Apply limit
    results = query.limit(limit).all()
    
    # Format results
    top_clans = []
    for rating, clan in results:
        total_games = rating.wins + rating.losses
        win_rate = rating.win_rate * 100 if total_games > 0 else 0
        
        top_clans.append({
            "clan_id": clan.id,
            "name": clan.name,
            "rating": rating.rating,
            "wins": rating.wins,
            "losses": rating.losses,
            "total_games": total_games,
            "win_rate": round(win_rate, 1),
            "prestige_wins": rating.prestige_wins,
            "murder_wins": rating.murder_wins,
            "decay_wins": rating.decay_wins,
            "stones_wins": rating.stones_wins
        })
    
    return top_clans


def get_player_hero_rankings(
    db: Session,
    player_id: int,
    min_games: int = 3
) -> List[Dict[str, Any]]:
    """
    Get a player's personal hero rankings.
    
    Args:
        db: Database session
        player_id: ID of the player
        min_games: Minimum number of games required for a hero to be ranked
        
    Returns:
        List of hero data dictionaries for this player, sorted by rating
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Getting hero rankings for player {player_id}")
    
    query = db.query(
        PlayerHeroRating,
        Hero
    ).join(
        Hero, PlayerHeroRating.hero_id == Hero.id
    ).filter(
        PlayerHeroRating.player_id == player_id,
        (PlayerHeroRating.wins + PlayerHeroRating.losses) >= min_games
    ).order_by(
        desc(PlayerHeroRating.rating)
    )
    
    results = query.all()
    
    # Format results
    hero_rankings = []
    for rating, hero in results:
        total_games = rating.wins + rating.losses
        win_rate = rating.win_rate * 100 if total_games > 0 else 0
        
        hero_rankings.append({
            "hero_id": hero.id,
            "name": hero.name,
            "rating": rating.rating,
            "wins": rating.wins,
            "losses": rating.losses,
            "total_games": total_games,
            "win_rate": round(win_rate, 1),
            "prestige_wins": rating.prestige_wins,
            "murder_wins": rating.murder_wins,
            "decay_wins": rating.decay_wins,
            "stones_wins": rating.stones_wins,
            "clan_id": hero.clan_id
        })
    
    return hero_rankings


def get_player_clan_rankings(
    db: Session,
    player_id: int
) -> List[Dict[str, Any]]:
    """
    Get a player's personal clan rankings.
    
    Args:
        db: Database session
        player_id: ID of the player
        
    Returns:
        List of clan data dictionaries for this player, sorted by rating
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Getting clan rankings for player {player_id}")
    
    query = db.query(
        PlayerClanRating
    ).filter(
        PlayerClanRating.player_id == player_id
    ).order_by(
        desc(PlayerClanRating.rating)
    )
    
    results = query.all()
    
    # Format results
    clan_rankings = []
    for rating in results:
        total_games = rating.wins + rating.losses
        win_rate = rating.win_rate * 100 if total_games > 0 else 0
        
        clan_rankings.append({
            "clan_id": rating.clan_id,
            "name": rating.clan_name,
            "rating": rating.rating,
            "wins": rating.wins,
            "losses": rating.losses,
            "total_games": total_games,
            "win_rate": round(win_rate, 1),
            "prestige_wins": rating.prestige_wins,
            "murder_wins": rating.murder_wins,
            "decay_wins": rating.decay_wins,
            "stones_wins": rating.stones_wins
        })
    
    return clan_rankings


def get_win_type_distribution(
    db: Session,
    clan_id: Optional[int] = None,
    hero_id: Optional[int] = None
) -> Dict[str, int]:
    """
    Get win type distribution (prestige, murder, etc.) overall or for a specific clan/hero.
    
    Args:
        db: Database session
        clan_id: Optional clan ID to filter by
        hero_id: Optional hero ID to filter by
        
    Returns:
        Dictionary mapping win types to their counts
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Getting win type distribution for clan_id={clan_id}, hero_id={hero_id}")
    
    if hero_id:
        # Query win types for a specific hero
        hero_ratings = db.query(GeneralHeroRating).filter_by(hero_id=hero_id).first()
        if not hero_ratings:
            return {win_type.value: 0 for win_type in WinTypeEnum}
            
        return {
            # GeneralHeroRating doesn't have win type columns, so we need to query differently
            # This is a placeholder - you'll need to adjust based on your actual data structure
            "prestige": 0,
            "murder": 0,
            "decay": 0,
            "stones": 0
        }
        
    elif clan_id:
        # Query win types for a specific clan
        clan_ratings = db.query(GeneralClanRating).filter_by(clan_id=clan_id).first()
        if not clan_ratings:
            return {win_type.value: 0 for win_type in WinTypeEnum}
            
        return {
            "prestige": clan_ratings.prestige_wins,
            "murder": clan_ratings.murder_wins,
            "decay": clan_ratings.decay_wins,
            "stones": clan_ratings.stones_wins
        }
        
    else:
        # Query overall win type distribution
        # Aggregate across all PlayerOverallRating records
        totals = db.query(
            func.sum(PlayerOverallRating.prestige_wins).label("prestige"),
            func.sum(PlayerOverallRating.murder_wins).label("murder"),
            func.sum(PlayerOverallRating.decay_wins).label("decay"),
            func.sum(PlayerOverallRating.stones_wins).label("stones")
        ).first()
        
        return {
            "prestige": totals.prestige or 0,
            "murder": totals.murder or 0,
            "decay": totals.decay or 0,
            "stones": totals.stones or 0
        }


def get_player_position(
    db: Session,
    player_id: int,
    sort_by: str = "rating"
) -> Tuple[int, int]:
    """
    Get a player's position in the overall rankings.
    
    Args:
        db: Database session
        player_id: ID of the player
        sort_by: Field to sort by (rating, wins, win_rate)
        
    Returns:
        Tuple containing (position, total players)
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Getting ranking position for player {player_id}")
    
    # Get the player's rating
    player_rating = db.query(PlayerOverallRating).filter_by(player_id=player_id).first()
    if not player_rating:
        return (0, 0)
    
    # Count total players
    total_players = db.query(PlayerOverallRating).count()
    
    # Query to find position
    if sort_by == "win_rate":
        # Only consider players with at least 10 games for win rate ranking
        min_games_filter = (PlayerOverallRating.wins + PlayerOverallRating.losses) >= 10
        player_win_rate = player_rating.win_rate
        
        # Count players with higher win rate
        higher_ranked = db.query(PlayerOverallRating).filter(
            PlayerOverallRating.player_id != player_id,
            min_games_filter,
            (PlayerOverallRating.wins / (PlayerOverallRating.wins + PlayerOverallRating.losses)) > player_win_rate
        ).count()
        
        position = higher_ranked + 1
        
    elif sort_by == "wins":
        # Count players with more wins
        higher_ranked = db.query(PlayerOverallRating).filter(
            PlayerOverallRating.player_id != player_id,
            PlayerOverallRating.wins > player_rating.wins
        ).count()
        
        position = higher_ranked + 1
        
    else:  # Default to rating
        # Count players with higher rating
        higher_ranked = db.query(PlayerOverallRating).filter(
            PlayerOverallRating.player_id != player_id,
            PlayerOverallRating.rating > player_rating.rating
        ).count()
        
        position = higher_ranked + 1
    
    return (position, total_players)