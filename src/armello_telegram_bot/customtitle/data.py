from sqlalchemy.orm import Session

from ..match.models import Player
from .models import CustomTitle


def init_custom_titles(session: Session):
    """
    Initialize the titles table with default titles for each category.
    
    Args:
        session: SQLAlchemy session object
    """
    # Define the titles and their corresponding categories
    default_titles = [
        {"title": "Best Artist", "player_id": 1}
    ]

    # Check if titles already exist to avoid duplicates
    existing_titles = session.query(CustomTitle).all()
    if existing_titles:
        print("Titles table already contains data. Skipping initialization.")
        return

    # Add all titles to the session
    for title_data in default_titles:
        title = CustomTitle(title=title_data["title"], player_id=title_data["player_id"])
        player = session.query(Player).filter(Player.id == title_data["player_id"]).first()
        player.custom_titles.append(title)
        session.add(title)

    # Commit the changes
    session.commit()
    print("Titles table initialized with default values.")
