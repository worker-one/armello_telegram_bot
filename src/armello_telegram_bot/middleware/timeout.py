import logging

from telebot import TeleBot
from telebot.handler_backends import BaseMiddleware
from telebot.types import CallbackQuery, Message

from armello_telegram_bot.common.service import cancel_timeout

from ..common.service import cancel_timeout

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MessageTimeoutMiddleware(BaseMiddleware):
    """Middleware to log user messages"""

    def __init__(self, bot: TeleBot) -> None:
        self.bot = bot
        self.update_types = ["message"]

    def pre_process(self, message: Message, data: dict):
        """Pre-process the message"""
        cancel_timeout(message.chat.id)

    def post_process(self, message, data, exception):
        pass


class CallbackTimeoutMiddleware(BaseMiddleware):
    """Middleware to log user callbacks"""

    def __init__(self, bot: TeleBot) -> None:
        self.bot = bot
        self.update_types = ["callback_query"]

    def pre_process(self, callback_query: CallbackQuery, data: dict):
        """Pre-process the callback query"""
        cancel_timeout(callback_query.message.chat.id)

    def post_process(self, callback_query, data, exception):
        pass
