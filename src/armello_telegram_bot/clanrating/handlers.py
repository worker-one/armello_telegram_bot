from ast import In
import logging
from pathlib import Path
from tracemalloc import start

from armello_telegram_bot.top import markup
from omegaconf import OmegaConf
from telebot import TeleBot, types
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from telebot.states import State, StatesGroup

from ..common.service import cancel_timeout, start_timeout, user_messages
from ..database.core import db_session
from .markup import create_clan_selection_menu_markup
from .service import format_clan_stats, get_clan_stats, read_clans


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

# Define States
class ClanratingState(StatesGroup):
    """ Clanrating states """
    waiting_for_clan_name = State()
    watching_clan_stats = State()


def register_handlers(bot: TeleBot):
    """Register clan rating handlers"""
    logger.info("Registering clan rating handlers")

    @bot.message_handler(commands=['clanrating'])
    def start_clanrating(message: types.Message, data: dict):
        """Start the clan rating process"""
        user = data['user']
        data["state"].set(ClanratingState.waiting_for_clan_name)
        chat_id = message.chat.id

        clans = read_clans(db_session)

        # Create keyboard with clan buttons
        markup = create_clan_selection_menu_markup(user.lang, clans)

        # Send message with keyboard
        sent_message = bot.reply_to(
            message,
            strings[user.lang].welcome_message,
            reply_markup=markup
        )

        # Set timer
        # user_messages[message.chat.id] = sent_message.message_id
        # start_timeout(bot, message.chat.id, sent_message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == "clanrating", state=ClanratingState.watching_clan_stats)
    def clanrating_callback(call: types.CallbackQuery, data: dict):
        """Handle the clan rating callback"""
        start_clanrating(call.message, data)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("clan_"), state=ClanratingState.waiting_for_clan_name)
    def process_clan_callback(call: types.CallbackQuery, data: dict):
        """Process the selected clan from callback"""
        user = data["user"]
        data["state"].set(ClanratingState.watching_clan_stats)
        chat_id = call.message.chat.id
        clan_name = call.data.replace("clan_", "")

        # Get clan statistics
        try:
            clan_stats = get_clan_stats(db_session, clan_name)
            stats_text = format_clan_stats(clan_name.split(' ')[1], clan_stats)

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("Назад", callback_data="clanrating")
            )

            # Send formatted stats
            bot.edit_message_text(
                text=stats_text,
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )

        except Exception as e:
            logger.error(f"Error getting clan stats: {str(e)}")
            bot.answer_callback_query(
                call.id,
                "Произошла ошибка при получении статистики клана. Пожалуйста, попробуйте позже."
            )

        # Answer callback to remove loading state
        bot.answer_callback_query(call.id)


    @bot.callback_query_handler(func=lambda call: call.data.startswith("exit"))
    def exit_clanrating(call: types.CallbackQuery, data: dict):
        """Exit the clan rating process"""
        user = data["user"]
        cancel_timeout(call.message.chat.id)
        data["state"].delete()

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=strings[user.lang].goodbye_message
        )
        user_messages[call.message.chat.id] = call.message.message_id
