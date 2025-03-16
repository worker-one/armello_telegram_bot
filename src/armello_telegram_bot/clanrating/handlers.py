import logging
from pathlib import Path

from omegaconf import OmegaConf
from telebot import TeleBot, types
from telebot.states import State, StatesGroup

from ..common.service import cancel_timeout, start_timeout, user_messages
from ..database.core import get_session
from .markup import create_clan_selection_menu_markup
from .service import format_clan_stats, get_clan_stats, read_clans

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

# Load the database session
db_session = get_session()

# Define States
class ClanratingState(StatesGroup):
    """ Clanrating states """
    waiting_for_clan_name = State()


def register_handlers(bot: TeleBot):
    """Register clan rating handlers"""
    logger.info("Registering clan rating handlers")

    @bot.message_handler(commands=['clanrating'])
    def start_clanrating(message: types.Message, data: dict):
        """Start the clan rating process"""
        user = data['user']
        chat_id = message.chat.id

        clans = read_clans(db_session)

        # Create keyboard with clan buttons
        markup = create_clan_selection_menu_markup(user.lang, clans)

        # Send message with keyboard
        sent_message = bot.send_message(
            chat_id,
            strings[user.lang].welcome_message,
            reply_markup=markup
        )

        # Set state
        bot.set_state(message.from_user.id, ClanratingState.waiting_for_clan_name, message.chat.id)

        # Set timer
        user_messages[message.chat.id] = sent_message.message_id
        start_timeout(bot, message.chat.id, sent_message.message_id)


    @bot.callback_query_handler(func=lambda call: call.data.startswith("clan_"))
    def process_clan_callback(call: types.CallbackQuery, data: dict):
        """Process the selected clan from callback"""
        user = data["user"]
        chat_id = call.message.chat.id
        clan_name = call.data.replace("clan_", "")

        # Get clan statistics
        try:
            clan_stats = get_clan_stats(db_session, clan_name)
            stats_text = format_clan_stats(clan_name, clan_stats)

            # Send formatted stats
            bot.edit_message_text(
                text=stats_text,
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=None
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
        chat_id = call.message.chat.id

        # Send message with keyboard
        bot.send_message(
            chat_id,
            strings[user.lang].goodbye_message,
            reply_markup=None
        )

        # Reset state
        bot.reset_state(data["user"].id)
