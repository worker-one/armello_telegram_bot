from typing import Optional
from pydantic import BaseModel


class PlayerRatingModel(BaseModel):
    """Player rating model for top lists"""
    username: str
    rating: float
    wins: int
    losses: int
    win_rate: float
    titles: Optional[list[str]] = []

class HeroRatingModel(BaseModel):
    """Hero rating model for top lists"""
    id: int
    name: str
    rating: float
    wins: int
    losses: int
    win_rate: float


class ClanRatingModel(BaseModel):
    """Clan rating model for top lists"""
    id: int
    name: str
    rating: float
    wins: int
    losses: int
    win_rate: float


class ClanTopPlayerModel(BaseModel):
    """Top player of a clan model"""
    username: str
    title: str