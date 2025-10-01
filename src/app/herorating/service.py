from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

from ..match.models import Hero, Match, MatchParticipant, WinTypeEnum
from .models import HeroStats
from difflib import get_close_matches


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
    matches = get_close_matches(search_term, hero_names + hero_aliases, n=1, cutoff=0.4)

    if matches:
        closest_match = matches[0]
        # Find hero with matching name or alias
        return db.query(Hero).filter(
            (Hero.name.ilike(closest_match)) |
            (Hero.alias.ilike(closest_match))
        ).first()

    return None


def get_hero_stats(db_session: Session, hero_id: int):
    """
    Get or create hero stats
    """
    stats = calculate_hero_stats(db_session, hero_id)
    return stats

def calculate_hero_stats(db_session: Session, hero_id: int):
    """
    Calculate hero statistics from matches
    """
    # Get hero
    hero = db_session.query(Hero).filter(Hero.id == hero_id).one()
    
    # Get all participations of this hero
    participations = db_session.query(MatchParticipant).filter(MatchParticipant.hero_id == hero_id).all()
    
    # Calculate stats
    total_matches = len(participations)
    total_wins = sum(1 for p in participations if p.is_winner)
    
    # Clalculate score as a sum of all participants' scores for the hero
    score = sum(p.score for p in participations)
    
    # Calculate wins by type
    win_types = {
        WinTypeEnum.prestige: 0,
        WinTypeEnum.murder: 0,
        WinTypeEnum.decay: 0,
        WinTypeEnum.stones: 0
    }
    
    for p in participations:
        if p.is_winner:
            match = db_session.query(Match).filter(Match.id == p.match_id).one()
            win_types[match.win_type] += 1
    
    # Create or update stats object
    stats = db_session.query(HeroStats).filter(HeroStats.hero_id == hero_id).first()
    if not stats:
        stats = HeroStats(
            hero_id=hero_id,
            total_matches=total_matches,
            score=score,
            total_wins=total_wins,
            prestige_wins=win_types[WinTypeEnum.prestige],
            murder_wins=win_types[WinTypeEnum.murder],
            decay_wins=win_types[WinTypeEnum.decay],
            stones_wins=win_types[WinTypeEnum.stones]
        )
        db_session.add(stats)
        db_session.commit()
    else:
        stats.total_matches = total_matches
        stats.score = score
        stats.total_wins = total_wins
        stats.prestige_wins = win_types[WinTypeEnum.prestige]
        stats.murder_wins = win_types[WinTypeEnum.murder]
        stats.decay_wins = win_types[WinTypeEnum.decay]
        stats.stones_wins = win_types[WinTypeEnum.stones]
        db_session.commit()
    return stats

def format_hero_stats(hero, stats):
    """
    Format hero stats for display
    """
    winrate = 0 if stats.total_matches == 0 else (stats.total_wins / stats.total_matches) * 100
    
    message = f"Общий рейтинг героя {hero.name}: {stats.score}\n\n"
    message += f"Победы: {stats.total_wins}\n"
    message += f"Поражения: {stats.total_matches - stats.total_wins}\n"
    message += f"Винрейт: {winrate:.1f}%\n\n"
    
    message += f"Победы через престиж: {stats.prestige_wins}\n"
    message += f"Победы через убийство Короля: {stats.murder_wins}\n"
    message += f"Победы через Гниль: {stats.decay_wins}\n"
    message += f"Победы через Камни Духа: {stats.stones_wins}"
    
    return message
