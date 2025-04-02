from difflib import get_close_matches

from sqlalchemy import func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from ..match.models import Clan, Hero, MatchParticipant, WinTypeEnum
from ..top import service as top_services
from ..title import service as title_services
from .models import ClanStats


def get_clan_stats(session: Session, clan_name: str):
    """
    Get statistics for a specific clan
    """
    try:
        print(f"Getting stats for clan: {clan_name}")
        
        clan = session.query(Clan).filter(Clan.name == clan_name).one()
        
        print(f"Clan found: {clan.name}")
        
        # Get all heroes for the clan
        heroes = session.query(Hero).filter(Hero.clan.has(name=clan_name)).all()
        print(f"Found {len(heroes)} heroes for clan {clan_name}")
        
        if not heroes:
            print(f"No heroes found for clan {clan_name}")
            return None
        
        hero_ids = [hero.id for hero in heroes]
        print(f"Hero IDs: {hero_ids}")
        
        # Clalculate score as a sum of all participants' scores for the clan
        clan_score = session.query(func.sum(MatchParticipant.score))\
            .filter(MatchParticipant.hero_id.in_(hero_ids)).scalar() or 0
        print(f"Clan score: {clan_score}")
        
        # Calculate total games, wins and losses for the clan
        wins = session.query(func.count(MatchParticipant.id))\
            .filter(MatchParticipant.hero_id.in_(hero_ids))\
            .filter(MatchParticipant.is_winner == True).scalar() or 0
        print(f"Total wins: {wins}")
            
        total_games = session.query(func.count(MatchParticipant.id))\
            .filter(MatchParticipant.hero_id.in_(hero_ids)).scalar() or 0
        print(f"Total games: {total_games}")
            
        losses = total_games - wins
        print(f"Total losses: {losses}")
        
        # Calculate win types
        print("Calculating win types...")
        prestige_wins = session.query(func.count(MatchParticipant.id))\
            .filter(MatchParticipant.hero_id.in_(hero_ids))\
            .filter(MatchParticipant.is_winner == True)\
            .filter(MatchParticipant.win_type == WinTypeEnum.prestige).scalar() or 0
        print(f"Prestige wins: {prestige_wins}")
            
        murder_wins = session.query(func.count(MatchParticipant.id))\
            .filter(MatchParticipant.hero_id.in_(hero_ids))\
            .filter(MatchParticipant.is_winner == True)\
            .filter(MatchParticipant.win_type == WinTypeEnum.murder).scalar() or 0
        print(f"King slayer wins: {murder_wins}")

        decay_wins = session.query(func.count(MatchParticipant.id))\
            .filter(MatchParticipant.hero_id.in_(hero_ids))\
            .filter(MatchParticipant.is_winner == True)\
            .filter(MatchParticipant.win_type == WinTypeEnum.decay).scalar() or 0
        print(f"Rot wins: {decay_wins}")

        stones_wins = session.query(func.count(MatchParticipant.id))\
            .filter(MatchParticipant.hero_id.in_(hero_ids))\
            .filter(MatchParticipant.is_winner == True)\
            .filter(MatchParticipant.win_type == WinTypeEnum.stones).scalar() or 0
        print(f"Spirit stone wins: {stones_wins}")

        best_player = top_services.get_top_players_by_clan(session, clan_id=clan.id, limit=1)[0]

        # get title associated with this clan
        clan_title = title_services.read_clan_title(session, clan_id=clan.id)

        print("Updating clan stats in database...")
        # Create or update clan stats
        clan_stats, created = get_or_create_clan_stats(session, clan_name)

        # Update stats
        clan_stats.total_games = total_games
        clan_stats.wins = wins
        clan_stats.losses = losses
        clan_stats.prestige_wins = prestige_wins
        clan_stats.murder_wins = murder_wins
        clan_stats.decay_wins = decay_wins
        clan_stats.stones_wins = stones_wins
        clan_stats.best_player_username = best_player.username
        clan_stats.best_player_title = clan_title.title
        clan_stats.score = clan_score

        session.commit()
        print("Stats updated successfully")

        return clan_stats
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        session.rollback()
        raise e


def get_or_create_clan_stats(session: Session, clan_name: str):
    """
    Get or create clan stats record
    """
    try:
        clan_stats = session.query(ClanStats).filter(ClanStats.clan_name == clan_name).one()
        return clan_stats, False
    except NoResultFound:
        clan_stats = ClanStats(clan_name=clan_name)
        session.add(clan_stats)
        session.commit()
        return clan_stats, True


def find_clan_by_name(session: Session, clan_name: str):
    """
    Find clan by name with fuzzy matching
    """
    # Get all unique clan names from heroes table
    clan_names = session.query(Hero.clan).distinct().all()
    clan_names = [c[0] for c in clan_names]
    
    # Try to find a close match
    matches = get_close_matches(clan_name, clan_names, n=1, cutoff=0.6)
    
    if matches:
        return matches[0]
    return None


def format_clan_stats(clan_name, stats):
    """
    Format clan stats for display
    """
    if not stats:
        return f"Статистика для клана {clan_name} не найдена."
    
    win_rate = (stats.wins / stats.total_games * 100) if stats.total_games > 0 else 0
    
    result = [
        f"Общий рейтинг клана {clan_name}: {stats.score}",
        f"Победы: {stats.wins}",
        f"Поражения: {stats.losses}",
        f"Винрейт: {win_rate:.1f}%",
        "",
        f"Победы через Престиж: {stats.prestige_wins}",
        f"Победы через убийство Короля: {stats.murder_wins}",
        f"Победы через Гниль: {stats.decay_wins}",
        f"Победы через Камни Духа: {stats.stones_wins}\n",
        f"Топ-1 Клана: @{stats.best_player_username}",
        f"Титул @{stats.best_player_username}: {stats.best_player_title}"
    ]

    return "\n".join(result)


def read_clans(db_session: Session):
    """
    Read all clans from the database
    """
    return db_session.query(Clan).all()

