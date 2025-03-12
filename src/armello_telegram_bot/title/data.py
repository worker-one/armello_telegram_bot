from sqlalchemy.orm import Session
from .models import Title

def init_titles(session: Session):
    """
    Initialize the titles table with default titles for each category.
    
    Args:
        session: SQLAlchemy session object
    """
    # Define the titles and their corresponding categories
    default_titles = [
        {"category": "overall", "title": "Лучший игрок ру-комьюнити"},
        {"category": "wolf", "title": "Вожак Волков", "clan_id": 1},
        {"category": "rabbit", "title": "Архимаг Кроликов", "clan_id": 2},
        {"category": "rat", "title": "Командующий Крыс", "clan_id": 3},
        {"category": "bear", "title": "Старейшина Медведей", "clan_id": 4},
        {"category": "bandit", "title": "Главарь Разбойников", "clan_id": 5},
        {"category": "dragon", "title": "Владыка Драконов", "clan_id": 6}
    ]

    # Check if titles already exist to avoid duplicates
    existing_titles = session.query(Title).all()
    if existing_titles:
        print("Titles table already contains data. Skipping initialization.")
        return

    # Add all titles to the session
    for title_data in default_titles:
        title = Title(category=title_data["category"], title=title_data["title"], clan_id=title_data.get("clan_id"))
        session.add(title)

    # Commit the changes
    session.commit()
    print("Titles table initialized with default values.")
