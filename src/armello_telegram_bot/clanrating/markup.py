import logging
import logging.config
from pathlib import Path

from omegaconf import OmegaConf
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..match.models import Clan

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_clan_selection_menu_markup(lang: str, clans: list[Clan]) -> InlineKeyboardMarkup:
    """ Create the items menu markup """
    # Get all available clans
    markup = InlineKeyboardMarkup(row_width=1)

    # Add buttons for each clan
    
    print(clans, len(clans))
    for clan in clans:
        markup.add(InlineKeyboardButton(clan.name, callback_data=f"clan_{clan.name}"))

    # Add exit button
    markup.add(InlineKeyboardButton("Выход", callback_data="exit"))

    return markup


def create_cancel_button(lang: str) -> InlineKeyboardMarkup:
    """ Create a cancel button for the items menu """
    cancel_button = InlineKeyboardMarkup(row_width=1)
    cancel_button.add(
        InlineKeyboardButton(strings[lang].cancel, callback_data="item"),
    )
    return cancel_button
