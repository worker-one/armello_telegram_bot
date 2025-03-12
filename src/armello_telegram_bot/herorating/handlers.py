import logging
from pathlib import Path

from omegaconf import OmegaConf
from telebot import TeleBot, types
from telebot.states import State, StatesGroup

from ..database.core import get_session
from .service import read_hero, format_hero_stats, get_hero_stats

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

# Load the database session
db_session = get_session()

# Define States
class HeroratingState(StatesGroup):
    """ Herorating states """
    waiting_for_hero_name = State()


def register_handlers(bot: TeleBot):
    """Register hero rating handlers"""
    logger.info("Registering hero rating handlers")

    @bot.message_handler(commands=['herorating'])
    def start_herorating(message):
        """Start the hero rating process"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        markup.add(types.KeyboardButton("Выход"))

        bot.send_message(
            message.chat.id,
            "Какой герой вас интересует? Напишите его имя. Если вы закончили, нажмите кнопку выхода",
            reply_markup=markup
        )
        bot.set_state(message.from_user.id, HeroratingState.waiting_for_hero_name, message.chat.id)

    @bot.message_handler(state=HeroratingState.waiting_for_hero_name, content_types=['text'])
    def handle_hero_name(message: types.Message, data: dict):
        """Handle hero name input"""
        user = data["user"]
        if message.text.lower() == "выход":
            bot.send_message(message.chat.id, "До свидания!", reply_markup=types.ReplyKeyboardRemove())
            bot.delete_state(message.from_user.id, message.chat.id)
            return

        # Try to find hero
        hero = read_hero(db_session, message.text)

        if not hero:
            bot.send_message(
                message.chat.id,
                strings[user.lang].hero_not_found.format(name=message.text)
            )
            return

        # Get hero stats
        stats = get_hero_stats(db_session, hero.id)

        # Format and send response
        stats_message = format_hero_stats(hero, stats)
        bot.send_message(message.chat.id, stats_message)

        # Ask for next hero
        bot.send_message(
            message.chat.id,
            "Какой еще герой вас интересует? Напишите его имя или нажмите кнопку выхода."
        )

    # Timeout handler
    @bot.middleware_handler(update_types=['message'])
    def timeout_middleware(bot_instance, update):
        user_id = update.message.from_user.id
        chat_id = update.message.chat.id

        state = bot_instance.get_state(user_id, chat_id)
        if state and state.startswith('HeroratingState:'):
            # Check if the state is more than 2 minutes old
            last_activity = bot_instance.get_state_data(user_id, chat_id).get('last_activity', 0)
            current_time = int(update.message.date)

            if current_time - last_activity > 120:  # 2 minutes
                bot_instance.send_message(chat_id, strings["ru"].goodbye_message, reply_markup=types.ReplyKeyboardRemove())
                bot_instance.delete_state(user_id, chat_id)
            else:
                # Update last activity
                state_data = bot_instance.get_state_data(user_id, chat_id)
                state_data['last_activity'] = current_time
                bot_instance.set_state_data(user_id, chat_id, state_data)
