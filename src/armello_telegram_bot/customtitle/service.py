import logging
from sqlalchemy.orm import Session

from ..match.models import Player
from .models import CustomTitle

logger = logging.getLogger(__name__)

# Clan categories for reference (used in the existing code)
CLAN_CATEGORIES = {
    "rat": "Крысиный клан",
    "rabbit": "Кроличий клан",
    "bear": "Медвежий клан",
    "wolf": "Волчий клан",
    # другие категории...
}


def get_available_titles(session: Session, player_id: int, is_channel_owner: bool) -> list:
    """Get available titles for a player based on their rankings"""
    # Existing implementation
    # ...
    return []


def update_title(session: Session, category: str, new_title: str) -> None:
    """Update a title for a specific category"""
    # Existing implementation
    # ...
    pass


def get_player_by_username(session: Session, username: str) -> Player:
    """Find player by Telegram username"""
    return session.query(Player).filter(Player.username == username).first()


def create_custom_title(session: Session, player_id: int, title: str) -> CustomTitle:
    """Create a custom title for a player"""
    custom_title = CustomTitle(player_id=player_id, title=title)
    session.add(custom_title)
    session.commit()
    return custom_title


def delete_custom_title(session: Session, player_id: int, title: str) -> bool:
    """Delete a custom title for a player
    
    Returns:
        bool: True if title was found and deleted, False otherwise
    """
    custom_title = session.query(CustomTitle).filter(
        CustomTitle.player_id == player_id, 
        CustomTitle.title == title
    ).first()
    
    if not custom_title:
        return False
    
    session.delete(custom_title)
    session.commit()
    return True


def get_player_custom_titles(session: Session, player_id: int) -> list[CustomTitle]:
    """Get all custom titles for a player"""
    return session.query(CustomTitle).filter(CustomTitle.player_id == player_id).all()