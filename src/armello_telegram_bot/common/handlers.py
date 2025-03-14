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
        bot.send_message(message.chat.id, strings[user.lang].operation_cancelled)


    @bot.callback_query_handler(func=lambda call: True, state="*")
    def handle_any_callback(call: types.CallbackQuery, data: dict):
        """Cancel timeout on any user interaction."""
        cancel_timeout(call.message.chat.id)
        bot.answer_callback_query(call.id)
