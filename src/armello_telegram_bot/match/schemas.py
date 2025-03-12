from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel


class WinTypeEnum(str, Enum):
    prestige = "prestige"
    murder = "murder"
    decay = "decay"
    stones = "stones"

class ParticipantCreate(BaseModel):
    username: str
    hero_id: int

class MatchCreate(BaseModel):
    screenshot: str
    win_type: WinTypeEnum
    participants: List[ParticipantCreate]
    winner_username: str  # указываем username победителя

class ParticipantReport(BaseModel):
    username: str
    hero: str
    is_winner: bool

class MatchReport(BaseModel):
    match_id: int
    timestamp: datetime
    screenshot: str
    win_type: WinTypeEnum
    participants: List[ParticipantReport]
