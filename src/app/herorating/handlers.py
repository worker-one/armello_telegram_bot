import logging
from pathlib import Path

from omegaconf import OmegaConf
from telebot import TeleBot, types
from telebot.states import State, StatesGroup

from ..database.core import db_session
from .service import format_hero_stats, get_hero_stats, read_hero

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

# Define States
class HeroratingState(StatesGroup):
    """ Herorating states """
    waiting_for_hero_name = State()


def register_handlers(bot: TeleBot):
    """Register hero rating handlers"""
    logger.info("Registering hero rating handlers")

    @bot.message_handler(commands=['herorating'])
    def start_herorating(message, data: dict):
        """Start the hero rating process"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Выход", callback_data="exit_herorating"))
        data["state"].set(HeroratingState.waiting_for_hero_name)
        sent_message = bot.reply_to(
            message,
            "Введите имя героя, используя «Ответить» на это сообщение. Если вы закончили, нажмите кнопку выхода",
            reply_markup=markup
        )
        # start_timeout(bot, message.chat.id, sent_message.message_id)
        # user_messages[message.chat.id] = sent_message.message_id


    @bot.message_handler(state=HeroratingState.waiting_for_hero_name, content_types=['text'])
    def handle_hero_name(message: types.Message, data: dict):
        """Handle hero name input"""
        user = data["user"]
        if message.text.lower() == "выход":
            bot.reply_to(message, "До свидания!", reply_markup=types.ReplyKeyboardRemove())
            bot.delete_state(message.from_user.id, message.chat.id)
            return

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Выход", callback_data="exit_herorating"))

        # Try to find hero
        hero = read_hero(db_session, message.text)

        if not hero:
            bot.reply_to(
                message,
                strings[user.lang].hero_not_found.format(name=message.text),
                reply_markup=markup
            )
            return

        # Get hero stats
        stats = get_hero_stats(db_session, hero.id)

        # Format and send response
        stats_message = format_hero_stats(hero, stats)
        bot.reply_to(message, stats_message)

        # Ask for next hero
        bot.reply_to(
            message,
            "Введите имя героя, используя «Ответить» на это сообщение или нажмите кнопку выхода.",
            reply_markup=markup
        )
        # start_timeout(bot, message.chat.id, sent_message.message_id)
        # user_messages[message.chat.id] = sent_message.message_id
