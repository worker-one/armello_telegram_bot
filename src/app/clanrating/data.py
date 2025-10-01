from sqlalchemy.orm import Session

from .models import HeroStats


def init_hero_rating_table(db_session: Session):
    # Insert data into the item categories table
    fake_stats = [
            HeroStats(
                hero_id=1,
                total_matches=42,
                total_wins=18,
                prestige_wins=5,
                murder_wins=6,
                decay_wins=4,
                stones_wins=3
            ),
            HeroStats(
                hero_id=2,
                total_matches=37,
                total_wins=15,
                prestige_wins=3,
                murder_wins=5,
                decay_wins=2,
                stones_wins=5
            )
        ]

    # Add and commit data
    for item in fake_stats:
        db_session.add(item)

    db_session.commit()
