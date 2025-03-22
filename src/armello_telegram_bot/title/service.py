import logging
from typing import List, Optional, Tuple

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..match.models import Clan, Player
from ..rating.models import PlayerClanRating, PlayerOverallRating
from .models import Title

logger = logging.getLogger(__name__)

CLAN_CATEGORIES = {
    'wolf': 'Волки',
    'rabbit': 'Кролики',
    'rat': 'Крысы',
    'bear': 'Медведи',
    'bandit': 'Разбойники',
    'dragon': 'Драконы'
}

def read_clan_title(session: Session, clan_id: str) -> Title:
    """Read the title of the clan"""
    title = session.query(Title).filter(Title.clan_id == clan_id).first()
    return title


def is_top_player_overall(session: Session, player_id: int) -> bool:
    """Check if the player is #1 in the overall rating"""
    top_player = session.query(PlayerOverallRating)\
        .order_by(desc(PlayerOverallRating.rating))\
        .first()

    return top_player is not None and top_player.player_id == player_id


def is_top_player_in_clan(session: Session, player_id: int, clan_name: str) -> bool:
    """Check if the player is #1 in the specified clan"""
    logger.debug(f"Checking if player {player_id} is top in clan {clan_name}")
    
    clan = session.query(Clan).filter(Clan.name == clan_name).first()
    if not clan:
        logger.info(f"Clan {clan_name} not found")
        return False
    
    top_player = session.query(PlayerClanRating)\
        .filter(PlayerClanRating.clan_id == clan.id)\
        .order_by(desc(PlayerClanRating.rating))\
        .first()
    
    is_top = top_player is not None and top_player.player_id == player_id
    logger.info(f"Player {player_id} is{' ' if is_top else ' not '}top in clan {clan_name}")
    return is_top


def get_title(session: Session, category: str = None, clan_id: int = None) -> Optional[str]:
    """Get the current title for a category"""
    if category:
        title = session.query(Title).filter(Title.category == category).first()
    elif clan_id:
        title = session.query(Title).filter(Title.clan_id == clan_id).first()
    else:
        title = None
    if not title:
        # Create default title if none exists
        default_title = "Best Player" if category == "overall" else f"Best {category.capitalize()} Player"
        title = Title(category=category, title=default_title)
        session.add(title)
        session.commit()
    
    return title.title


def update_title(session: Session, category: str, new_title: str) -> None:
    """Update or create a title for a category"""
    title = session.query(Title).filter(Title.category == category).first()
    
    if title:
        title.title = new_title
    else:
        title = Title(category=category, title=new_title)
        session.add(title)
    
    session.commit()


def get_available_titles(
    session: Session, player_id: int,
    is_channel_owner: bool
    ) -> List[Tuple[str, str]]:
    """Get list of titles available for the player to change
    
    Returns a list of tuples: (category, display_name)
    """
    available_titles = []
    
    # Channel owner can change any title
    if is_channel_owner:
        available_titles.append(("overall", "Лучший игрок комьюнити"))
        for cat_id, cat_name in CLAN_CATEGORIES.items():
            available_titles.append((cat_id, cat_name))
        return available_titles
    
    # Check if player is top in overall rating
    if is_top_player_overall(session, player_id):
        available_titles.append(("overall", "Лучший игрок комьюнити"))
    
    # Check for each clan
    for cat_id, cat_name in CLAN_CATEGORIES.items():
        if is_top_player_in_clan(session, player_id, cat_name):
            available_titles.append((cat_id, cat_name))

    return available_titles


def assign_title_to_player(session: Session, player_id: int, category: str) -> bool:
    """
    Assign a title to a player by adding a record to the player_titles table
    
    Args:
        session: Database session
        player_id: Player ID to assign the title to
        category: Title category ('overall', 'wolf', 'rabbit', etc.)
        
    Returns:
        bool: True if title was successfully assigned, False otherwise
    """
    logger.debug(f"Assigning {category} title to player {player_id}")
    
    player = session.query(Player).filter(Player.id == player_id).first()
    if not player:
        logger.error(f"Player with ID {player_id} not found")
        return False
    
    title = session.query(Title).filter(Title.category == category).first()
    if not title:
        logger.info(f"Title for category {category} not found, creating default")
        default_title = "Best Player" if category == "overall" else f"Best {category.capitalize()} Player"
        title = Title(category=category, title=default_title)
        session.add(title)
        session.flush()
    
    # Check if player already has this title
    if title in player.titles:
        logger.info(f"Player {player_id} already has title {category}")
        return True
    
    # Assign title to player
    player.titles.append(title)
    session.commit()
    logger.info(f"Successfully assigned {category} title to player {player_id}")
    return True



def update_titles_after_match(db_session: Session):
    """ Updata associative table 
    titles = Table(
    'player_titles',
    Base.metadata,
    Column('player_id', Integer, ForeignKey('players.id')),
    Column('title_id', Integer, ForeignKey('titles.id'))
)
    """
    players = db_session.query(Player).all()
    for player in players:
        available_titles = get_available_titles(db_session, player.id, False)
        for category, display_name in available_titles:
            assign_title_to_player(
                db_session, player.id, category
            )
    db_session.commit()
