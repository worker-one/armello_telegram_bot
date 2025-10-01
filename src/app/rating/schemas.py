from typing import Optional
from pydantic import BaseModel


class RatingBase(BaseModel):
    rating: int
    wins: int
    losses: int
    titles: Optional[list[str]] = []

    @property
    def win_rate(self):
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0

class PlayerOverallRatingSchema(RatingBase):
    player_id: int

class PlayerHeroRatingSchema(RatingBase):
    player_id: int
    hero_id: int

class PlayerClanRatingSchema(RatingBase):
    player_id: int
    clan_id: int

class GeneralHeroRatingSchema(RatingBase):
    hero_id: int

class GeneralClanRatingSchema(RatingBase):
    clan_id: int
