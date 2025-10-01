import logging
from pathlib import Path

from omegaconf import OmegaConf
from telebot import TeleBot, types

from ..common.service import cancel_timeout

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings


def register_handlers(bot: TeleBot):
    """Register common handlers"""
    logger.info("Registering common handlers")

    @bot.message_handler(commands=['cancel'])
    def cancel_handler(message: types.Message, data: dict):
        """Cancel the current operation"""
        user = data["user"]
        bot.delete_state(message.from_user.id, message.chat.id)
        data["state"].delete()
        bot.reply_to(message, strings[user.lang].operation_cancelled)

