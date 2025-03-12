import logging
import logging.config
from pathlib import Path

from omegaconf import OmegaConf
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

#from .models import Item

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_cancel_button(lang: str) -> InlineKeyboardMarkup:
    """ Create a cancel button for the items menu """
    cancel_button = InlineKeyboardMarkup(row_width=1)
    cancel_button.add(
        InlineKeyboardButton(strings[lang].cancel, callback_data="match"),
    )
    return cancel_button
