import logging
from pathlib import Path

from omegaconf import OmegaConf
from telebot import TeleBot, types
from telebot.states import State, StatesGroup

from ..common.service import cancel_timeout, start_timeout
from ..database.core import get_session
from ..herorating import service as hero_service
from .markup import (
    create_top_selection_markup,
)
from .service import (
    get_top_players_by_hero,
    get_top_players_overall,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

# Load the database session
db_session = get_session()

# Define States
class TopState(StatesGroup):
    """Top list states"""
    select_top_type = State()
    enter_hero_name = State()
    select_clan = State()
    all = [select_top_type, enter_hero_name, select_clan]


def register_handlers(bot: TeleBot):
    """Register top list handlers"""
    logger.info("Registering top list handlers")


    @bot.message_handler(commands=["top"])
    def top_command(message: types.Message, data: dict):
        user = data["user"]
        data["state"].set(TopState.select_top_type)

        sent_message = bot.reply_to(
            message,
            text=strings[user.lang].select_top_type,
            reply_markup=create_top_selection_markup(user.lang)
        )
        start_timeout(bot, message.chat.id, sent_message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == "top_players_overall", state=TopState.select_top_type)
    def show_top_players_overall(call: types.CallbackQuery, data: dict):
        user = data["user"]
        top_players = get_top_players_overall(db_session)

        message_lines = [strings[user.lang].top_players_overall_header]
        for i, player in enumerate(top_players, 1):
            message_lines.append(
                f"{i}. @{player.username} – {int(player.rating)}: {player.wins}-{player.losses}-{int(player.win_rate*100)}%"
            )
        message_lines.append("\n" + strings[user.lang].top_players_explanation)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="\n".join(message_lines),
            reply_markup=create_top_selection_markup(user.lang)
        )
        start_timeout(bot, call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == "top_players_by_hero", state=TopState.select_top_type)
    def ask_for_hero_name(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(TopState.enter_hero_name)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=strings[user.lang].enter_hero_name
        )

    @bot.message_handler(state=TopState.enter_hero_name)
    def show_top_players_by_hero(message: types.Message, data: dict):
        user = data["user"]
        hero_name = message.text
        hero = hero_service.read_hero(db_session, hero_name=hero_name)
        if not hero:
            bot.reply_to(
                message,
                text=strings[user.lang].hero_not_found,
                reply_markup=types.ForceReply(selective=True)
            )
            return

        top_players = get_top_players_by_hero(db_session, hero.id)
        message_lines = [strings[user.lang].top_players_by_hero_header.format(hero_name=hero.name)]
        for i, player in enumerate(top_players, 1):
            message_lines.append(
                f"{i}. @{player.username} – {int(player.rating)}: {player.wins}-{player.losses}-{int(player.win_rate*100)}%"
            )
        bot.reply_to(
            message,
            text="\n".join(message_lines),
            reply_markup=create_top_selection_markup(user.lang)
        )
        data["state"].set(TopState.select_top_type)

    @bot.callback_query_handler(func=lambda call: call.data == "top_exit", state=TopState.select_top_type)
    def exit_top_command(call: types.CallbackQuery, data: dict):
        user = data["user"]
        cancel_timeout(call.message.chat.id)
        data["state"].delete()

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=strings[user.lang].goodbye
        )
