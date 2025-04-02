import logging
from typing import Optional

from sqlalchemy.orm import Session

from ..match.models import Clan, Match, Player
from .models import (
    GeneralClanRating,
    GeneralHeroRating,
    PlayerClanRating,
    PlayerHeroRating,
    PlayerOverallRating,
    WinTypeEnum,
)


def update_player_ratings_for_match(db: Session, match, player_id: int):
    """
    Update ratings for a specific player based on a single match.
    This is a specialized version of update_ratings_after_match that only
    affects the specified player's ratings.
    
    Args:
        db: Database session
        match: The match object containing participant data
        player_id: The player ID to update ratings for
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Updating ratings for player_id={player_id} for match {match.id}")

    winner_points = 4
    loser_points = -1
    
    # Find the player's participation in this match
    participant = next((p for p in match.participants if p.player_id == player_id), None)
    
    if not participant:
        logger.warning(f"Player {player_id} not found in match {match.id}")
        return
    
    hero_id = participant.hero_id
    clan_id = participant.hero.clan_id
    clan = db.query(Clan).filter_by(id=clan_id).first()
    
    logger.info(f"Processing participant: player_id={player_id}, hero_id={hero_id}, clan_id={clan.id}")

    # Update overall rating
    overall = db.query(PlayerOverallRating).filter_by(player_id=player_id).first()
    if not overall:
        logger.info(f"Creating new overall rating for player {player_id}")
        overall = PlayerOverallRating(
            player_id=player_id, rating=0, wins=0,
            losses=0, prestige_wins=0, murder_wins=0, stones_wins=0, decay_wins=0
        )
        db.add(overall)
    
    if participant.is_winner:
        overall.rating += winner_points
        overall.wins += 1

        # kind of win
        if participant.win_type == WinTypeEnum.prestige:
            overall.prestige_wins += 1
        elif participant.win_type == WinTypeEnum.murder:
            overall.murder_wins += 1
        elif participant.win_type == WinTypeEnum.decay:
            overall.decay_wins += 1
        elif participant.win_type == WinTypeEnum.stones:
            overall.stones_wins += 1
    else:
        overall.rating += loser_points
        overall.losses += 1
    
    logger.info(f"Updated overall rating for player {player_id}: rating={overall.rating}")

    # Update hero rating
    ph = db.query(PlayerHeroRating).filter_by(player_id=player_id, hero_id=hero_id).first()
    if not ph:
        logger.info(f"Creating new hero rating for player {player_id}, hero {hero_id}")
        ph = PlayerHeroRating(
            player_id=player_id, hero_id=hero_id, rating=0, wins=0,
            losses=0, prestige_wins=0, murder_wins=0, stones_wins=0, decay_wins=0
        )
        db.add(ph)
        db.flush()
    if participant.is_winner:
        ph.rating += winner_points
        ph.wins += 1

        # kind of win
        if participant.win_type == WinTypeEnum.prestige:
            ph.prestige_wins += 1
        elif participant.win_type == WinTypeEnum.murder:
            ph.murder_wins += 1
        elif participant.win_type == WinTypeEnum.decay:
            ph.decay_wins += 1
        elif participant.win_type == WinTypeEnum.stones:
            ph.stones_wins += 1
    else:
        ph.rating += loser_points
        ph.losses += 1

    # Update clan rating
    pc = db.query(PlayerClanRating).filter_by(player_id=player_id, clan_id=clan_id).first()
    if not pc:
        logger.info(f"Creating new clan rating for player {player_id}, clan {clan.id}")
        pc = PlayerClanRating(
            player_id=player_id, clan_id=clan_id, clan_name=clan.name, rating=0, wins=0,
            losses=0, prestige_wins=0, murder_wins=0, stones_wins=0, decay_wins=0
        )
        db.add(pc)

    if participant.is_winner:
        pc.rating += winner_points
        pc.wins += 1
        
        # kind of win
        if participant.win_type == WinTypeEnum.prestige:
            pc.prestige_wins += 1
        elif participant.win_type == WinTypeEnum.murder:
            pc.murder_wins += 1
        elif participant.win_type == WinTypeEnum.decay:
            pc.decay_wins += 1
        elif participant.win_type == WinTypeEnum.stones:
            pc.stones_wins += 1
    else:
        pc.rating += loser_points
        pc.losses += 1

    try:
        db.commit()
        logger.info(f"Successfully committed rating updates for player {player_id}")
    except Exception as e:
        logger.error(f"Error committing rating updates for player {player_id}: {e}")
        raise


def rebuild_player_ratings(db: Session, player_id: int):
    """
    Rebuild all ratings for a specific player based on their match history.
    This is useful when correcting a player's ratings without affecting the entire database.
    
    Steps:
    1. Reset all ratings for the specific player
    2. Process all their matches in chronological order
    3. Return statistics about the rebuild
    
    Args:
        db: Database session
        player_id: The ID of the player whose ratings should be rebuilt
        
    Returns:
        Dictionary with statistics about the rebuild process
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Starting rating rebuild for player_id={player_id}")
    
    # Check if player exists
    player = db.query(Player).filter_by(id=player_id).first()
    if not player:
        logger.error(f"Player with ID {player_id} not found")
        return {"error": f"Player with ID {player_id} not found"}
    
    # Clear current ratings for this player
    logger.info(f"Clearing existing ratings for player_id={player_id}")
    db.query(PlayerOverallRating).filter_by(player_id=player_id).delete()
    db.query(PlayerHeroRating).filter_by(player_id=player_id).delete()
    db.query(PlayerClanRating).filter_by(player_id=player_id).delete()
    db.commit()
    
    # Get all matches for this player ordered by date
    from ..match.models import Match, MatchParticipant
    matches_query = (
        db.query(Match)
        .join(MatchParticipant, Match.id == MatchParticipant.match_id)
        .filter(MatchParticipant.player_id == player_id)
        .order_by(Match.timestamp)
    )
    matches = matches_query.all()
    
    logger.info(f"Processing {len(matches)} matches for player_id={player_id}")
    processed_count = 0
    
    # Create initial rating objects for this player
    # Will be modified during match processing
    overall = PlayerOverallRating(
        player_id=player_id, rating=0, wins=0,
        losses=0, prestige_wins=0, murder_wins=0, stones_wins=0, decay_wins=0
    )
    db.add(overall)
    db.commit()
    
    # Process each match
    for match in matches:
        try:
            # For player rebuilds, we need a specialized function that only updates the target player
            update_player_ratings_for_match(db, match, player_id)
            processed_count += 1
            
            # Log progress periodically
            if processed_count % 10 == 0:
                logger.info(f"Processed {processed_count}/{len(matches)} matches for player_id={player_id}")
                
        except Exception as e:
            logger.error(f"Error processing match {match.id} for player_id={player_id}: {e}")
    
    # Gather statistics
    hero_ratings_count = db.query(PlayerHeroRating).filter_by(player_id=player_id).count()
    clan_ratings_count = db.query(PlayerClanRating).filter_by(player_id=player_id).count()
    
    logger.info(f"Rating rebuild complete for player_id={player_id}. Processed {processed_count} matches.")
    logger.info(f"Statistics: {hero_ratings_count} hero ratings, {clan_ratings_count} clan ratings")
    
    return {
        "player_id": player_id,
        "player_name": player.username,
        "matches_processed": processed_count,
        "matches_total": len(matches),
        "hero_ratings": hero_ratings_count,
        "clan_ratings": clan_ratings_count
    }


def rebuild_all_ratings(db: Session):
    """
    Rebuild all ratings based on complete match history.
    Resets all rating tables and recalculates from scratch.
    
    Args:
        db: Database session
    
    Returns:
        Dictionary with statistics about the rebuild process
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting complete rating rebuild")
    
    # Clear all rating tables
    logger.info("Clearing existing ratings")
    db.query(PlayerOverallRating).delete()
    db.query(PlayerHeroRating).delete()
    db.query(PlayerClanRating).delete()
    db.query(GeneralHeroRating).delete()
    db.query(GeneralClanRating).delete()
    db.commit()
    
    # Get all matches ordered by date
    matches = db.query(Match).order_by(Match.timestamp).all()
    
    logger.info(f"Processing {len(matches)} matches")
    processed_count = 0
    
    # Process each match
    for match in matches:
        try:
            update_ratings_after_match(db, match)
            processed_count += 1

            if processed_count % 10 == 0:
                logger.info(f"Processed {processed_count}/{len(matches)} matches")

        except Exception as e:
            logger.error(f"Error processing match {match.id}: {e}")

    # Gather statistics
    stats = {
        "matches_processed": processed_count,
        "matches_total": len(matches),
        "player_ratings": db.query(PlayerOverallRating).count(),
        "hero_ratings": db.query(PlayerHeroRating).count(),
        "clan_ratings": db.query(PlayerClanRating).count(),
        "general_hero_ratings": db.query(GeneralHeroRating).count(),
        "general_clan_ratings": db.query(GeneralClanRating).count()
    }

    logger.info(f"Rating rebuild complete. Stats: {stats}")
    return stats


def update_ratings_after_match(db: Session, match):
    """
    Обновление рейтингов на основании результатов матча.
    Для простоты предположим, что победителю начисляется +4 очков, а проигравшим – -1 очков.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Updating ratings for match {match.id}")

    winner_points = 4
    loser_points = -1

    for participant in match.participants:
        player_id = participant.player_id
        hero_id = participant.hero_id
        clan_id = participant.hero.clan_id

        clan = db.query(Clan).filter_by(id=clan_id).first()

        logger.info(f"Processing participant: player_id={player_id}, hero_id={hero_id}, clan_id={clan.id}")

        # Обновляем общий рейтинг игрока
        overall = db.query(PlayerOverallRating).filter_by(player_id=player_id).first()
        if not overall:
            logger.info(f"Creating new overall rating for player {player_id}")
            overall = PlayerOverallRating(
                player_id=player_id, rating=0, wins=0,
                losses=0, prestige_wins=0, murder_wins=0, stones_wins=0, decay_wins=0
            )
            db.add(overall)
            db.flush()  # Use flush instead of commit to get the ID without committing transaction

        if participant.is_winner:
            overall.rating += winner_points
            overall.wins += 1

            # kind of win
            if participant.win_type == WinTypeEnum.prestige:
                overall.prestige_wins += 1
            elif participant.win_type == WinTypeEnum.murder:
                overall.murder_wins += 1
            elif participant.win_type == WinTypeEnum.decay:
                overall.decay_wins += 1
            elif participant.win_type == WinTypeEnum.stones:
                overall.stones_wins += 1
        else:
            overall.rating += loser_points
            overall.losses += 1
        logger.info(f"Updated overall rating for player {player_id}: rating={overall.rating}")

        # Рейтинг игрока на конкретном герое
        ph = db.query(PlayerHeroRating).filter_by(player_id=player_id, hero_id=hero_id).first()
        if not ph:
            logger.info(f"Creating new hero rating for player {player_id}, hero {hero_id}")
            ph = PlayerHeroRating(player_id=player_id, hero_id=hero_id, rating=0, wins=0,
                losses=0, prestige_wins=0, murder_wins=0, stones_wins=0, decay_wins=0
            )
            db.add(ph)
            db.flush()
        if participant.is_winner:
            ph.rating += winner_points
            ph.wins += 1

            # kind of win
            if participant.win_type == WinTypeEnum.prestige:
                ph.prestige_wins += 1
            elif participant.win_type == WinTypeEnum.murder:
                ph.murder_wins += 1
            elif participant.win_type == WinTypeEnum.decay:
                ph.decay_wins += 1
            elif participant.win_type == WinTypeEnum.stones:
                ph.stones_wins += 1

        else:
            ph.rating += loser_points
            ph.losses += 1

        # Рейтинг игрока в конкретном клане
        pc = db.query(PlayerClanRating).filter_by(player_id=player_id, clan_id=clan_id).first()
        if not pc:
            logger.info(f"Creating new clan rating for player {player_id}, clan {clan.id}")
            pc = PlayerClanRating(
                player_id=player_id, clan_id=clan_id, clan_name=clan.name,
                rating=0, wins=0, losses=0, prestige_wins=0, murder_wins=0, stones_wins=0, decay_wins=0
            )
            db.add(pc)
            db.flush()
        if participant.is_winner:
            pc.rating += winner_points
            pc.wins += 1

            # kind of win
            if participant.win_type == WinTypeEnum.prestige:
                pc.prestige_wins += 1
            elif participant.win_type == WinTypeEnum.murder:
                pc.murder_wins += 1
            elif participant.win_type == WinTypeEnum.decay:
                pc.decay_wins += 1
            elif participant.win_type == WinTypeEnum.stones:
                pc.stones_wins += 1

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
