import logging
from typing import List, Optional, Dict

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..match.models import Clan, Player, Hero
from ..rating.models import PlayerClanRating, PlayerOverallRating, PlayerHeroRating
from .models import Title

logger = logging.getLogger(__name__)

# Define clan categories constants
CLAN_CATEGORIES = {
    "overall": "Лучший игрок комьюнити",
    "wolf": "Клан Волков",
    "rabbit": "Клан Кроликов",
    "rat": "Клан Крыс",
    "bear": "Клан Медведей",
    "bandit": "Клан Разбойников",
    "dragon": "Клан Драконов"
}

CATEGORY_TO_CLAN_ID = {
    "wolf": 1,
    "rabbit": 2,
    "rat": 3,
    "bear": 4,
    "bandit": 5,
    "dragon": 6,
}

def read_clans(session: Session) -> List[Clan]:
    """Read all clans from the database"""
    clans = session.query(Clan).all()
    return clans

def read_clan_title(session: Session, clan_id: str) -> Title:
    """Read the title of the clan"""
    title = session.query(Title).filter(Title.clan_id == clan_id).first()
    return title

def is_top_player_overall(session: Session, player_id: int) -> bool:
    """Check if player is top-1 in overall rating"""
    top_player = session.query(PlayerOverallRating).order_by(
        desc(PlayerOverallRating.rating)
    ).first()
    
    return top_player and top_player.player_id == player_id

def is_top_player_in_clan(session: Session, player_id: int, clan_id: int) -> bool:
    """Check if player is top-1 in clan rating"""
    logger.info(f"Checking if player {player_id} is top-1 in clan {clan_id}")
    top_player = session.query(PlayerClanRating).filter(
        PlayerClanRating.clan_id == clan_id
    ).order_by(
        desc(PlayerClanRating.rating)
    ).first()
    
    return top_player and top_player.player_id == player_id

def get_available_titles(session: Session, player_id: int, is_admin: bool) -> Dict[str, str]:
    """Get titles available for a player based on their rankings"""
    available_titles = {}
    
    # If player is admin, they can edit all titles
    if is_admin:
        return CLAN_CATEGORIES
    
    # Check if player is top in overall rating
    if is_top_player_overall(session, player_id):
        available_titles["overall"] = CLAN_CATEGORIES["overall"]
    
    # Check clan ratings
    for category, clan_id in CATEGORY_TO_CLAN_ID.items():
        if is_top_player_in_clan(session, player_id, clan_id):
            available_titles[category] = CLAN_CATEGORIES[category]
    
    return available_titles


def get_title(session: Session, category: str, clan_id: Optional[int] = None) -> Optional[Title]:
    """Get title for a specific category"""
    return session.query(Title).filter(
            Title.category == category,
            Title.clan_id == clan_id
        ).first()


def update_title(session: Session, category: str, title_text: str, clan_id: Optional[int] = None) -> Title:
    """Update or create a title for a specific category"""
    title = get_title(session, category, clan_id)

    if title:
        title.title = title_text
        title.default = False
    else:
        title = Title(
            category=category,
            clan_id=clan_id,
            title=title_text,
            default=False
        )
        session.add(title)
    session.commit()
    return title


def update_player_titles(session: Session, user_id: int):
    """Update player titles based on their rankings"""
    print("Starting update_player_titles for user_id:", user_id)
    
    # Find the player associated with this user_id
    player = session.query(Player).filter(Player.user_id == user_id).first()
    if not player:
        logger.warning(f"No player found for user_id {user_id}")
        return

    print(f"Found player with id: {player.id}")

    # Get current titles assigned to this player
    current_titles = session.query(Title).filter(Title.player_id == player.id).all()
    current_title_categories = {title.category for title in current_titles}
    
    print(f"Current titles for player {player.id}: {current_title_categories}")
    
    # Check if player deserves overall title (top player overall)
    deserves_overall_title = is_top_player_overall(session, player.id)
    print(f"Deserves overall title: {deserves_overall_title}")
    
    # If player deserves overall title but doesn't have it yet
    if deserves_overall_title and "overall" not in current_title_categories:
        print("Processing overall title assignment")
        # Get or create the overall title
        overall_title = get_title(session, "overall")
        if not overall_title:
            print("Creating new overall title")
            # Create default overall title if it doesn't exist
            overall_title = Title(
                category="overall",
                clan_id=None,
                title="Лучший игрок комьюнити",
                default=True
            )
            session.add(overall_title)
            session.flush()
        
        # Assign this title to the player
        overall_title.player_id = player.id
        if not overall_title.player:
            overall_title.player.append(player)
            print("Overall title assigned to player")
    
    # If player no longer deserves overall title but still has it
    elif not deserves_overall_title and "overall" in current_title_categories:
        print("Removing overall title from player")
        # Find and remove the overall title from player
        overall_title = next((t for t in current_titles if t.category == "overall"), None)
        if overall_title:
            if not overall_title.player:
                overall_title.player.remove(player)
            overall_title.player_id = None
    
    # Check clan titles
    for category, clan_id in CATEGORY_TO_CLAN_ID.items():
        print(f"\nChecking clan title for category: {category}, clan_id: {clan_id}")
        deserves_clan_title = is_top_player_in_clan(session, player.id, clan_id)
        print(f"Deserves {category} clan title: {deserves_clan_title}")
        
        # If player deserves clan title but doesn't have it
        if deserves_clan_title and category not in current_title_categories:
            print(f"Assigning {category} clan title")
            clan_title = get_title(session, category=category, clan_id=clan_id)
            if not clan_title:
                # Get clan name for the default title
                clan = session.query(Clan).filter(Clan.id == clan_id).first()
                clan_name = clan.name if clan else CLAN_CATEGORIES.get(category, category.capitalize())
                print(f"Creating new clan title for {clan_name}")
                
                # Create default clan title
                clan_title = Title(
                    category=category,
                    clan_id=clan_id,
                    title=f"Лучший {clan_name}",
                    default=True
                )
                session.add(clan_title)
                session.flush()
            
            # Assign this title to the player
            clan_title.player_id = player.id
            if not clan_title.player:
                clan_title.player.append(player)
                print(f"Clan title {category} assigned to player")
        
        # If player no longer deserves clan title but still has it
        elif not deserves_clan_title and category in current_title_categories:
            print(f"Removing {category} clan title from player")
            clan_title = next((t for t in current_titles if t.category == category), None)
            if clan_title:
                if not clan_title.player:
                    clan_title.player.remove(player)
                clan_title.player_id = None

    print("Committing changes to database")
    # Commit all changes
    session.commit()
    print("Title update completed")

def update_title_for_all_players(session: Session):
    """Update titles for all players"""
    players = session.query(Player).all()
    for player in players:
        update_player_titles(session, player.user_id)
    logger.info(f"Updated titles for all players")
    session.commit()