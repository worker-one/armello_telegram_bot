import logging
import logging.config
from pathlib import Path

from omegaconf import OmegaConf
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_rating_menu_markup(lang, include_other_player=True):
    """Create rating type selection markup"""
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(strings[lang].overall_rating, callback_data="rating_overall"),
        InlineKeyboardButton(strings[lang].hero_rating, callback_data="rating_hero"),
        InlineKeyboardButton(strings[lang].clan_rating, callback_data="rating_clan"),
    )
    if include_other_player:
        markup.add(InlineKeyboardButton(strings[lang].other_player, callback_data="rating_other_player"))
    markup.add(InlineKeyboardButton(strings[lang].delete, callback_data="cancel"))
    return markup


def create_hero_selection_markup(lang, heroes):
    """Create hero selection markup"""
    markup = InlineKeyboardMarkup(row_width=2)
    for hero in heroes:
        markup.add(InlineKeyboardButton(hero.name, callback_data=f"hero_{hero.id}"))
    markup.add(InlineKeyboardButton(strings[lang].back, callback_data="rating_back"))
    return markup


def create_clan_selection_markup(lang, clans):
    """Create clan selection markup"""
    markup = InlineKeyboardMarkup(row_width=2)
    for clan in clans:
        markup.add(InlineKeyboardButton(clan.name, callback_data=f"player_clan_rating_{clan.id}"))
    markup.add(InlineKeyboardButton(strings[lang].back, callback_data="rating_back"))
    return markup
