import asyncio
import logging
from pathlib import Path

from omegaconf import OmegaConf
from telebot import TeleBot, types
from telebot.states import State, StatesGroup

from ..database.core import get_session
from ..herorating import service as hero_service
from .markup import (
    create_clan_selection_markup,
    create_top_selection_markup,
)
from .service import (
    get_top_clan_player_title,
    get_top_clans,
    get_top_heroes,
    get_top_players_by_clan,
    get_top_players_by_hero,
    get_top_players_overall,
    read_clans,
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

        bot.reply_to(
            message,
            text=strings[user.lang].select_top_type,
            reply_markup=create_top_selection_markup(user.lang)
        )

    @bot.callback_query_handler(func=lambda call: call.data == "top_players_overall", state=TopState.select_top_type)
    def show_top_players_overall(call: types.CallbackQuery, data: dict):
        user = data["user"]
        top_players = get_top_players_overall(db_session)

        # Format the list
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
        
        # Format the list
        message_lines = [strings[user.lang].top_players_by_hero_header.format(hero_name=hero.name)]
        
        for i, player in enumerate(top_players, 1):
            message_lines.append(
                f"{i}. @{player.username} – {int(player.rating)}: {player.wins}-{player.losses}-{int(player.win_rate*100)}%"
            )
        
        message_lines.append("\n" + strings[user.lang].top_players_explanation)
        
        data["state"].set(TopState.select_top_type)
        
        bot.reply_to(
            message,
            text="\n".join(message_lines),
            reply_markup=create_top_selection_markup(user.lang)
        )

    @bot.callback_query_handler(func=lambda call: call.data == "top_players_by_clan", state=TopState.select_top_type)
    def select_clan_for_top(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(TopState.select_clan)
        
        clans = read_clans(db_session)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=strings[user.lang].select_clan,
            reply_markup=create_clan_selection_markup(user.lang, clans)
        )

    @bot.callback_query_handler(
        func=lambda call: call.data.startswith("top_clan_"),
        state=TopState.select_clan
    )
    def show_top_players_by_clan(call: types.CallbackQuery, data: dict):
        user = data["user"]
        clan_id = int(call.data.split("_")[2])
        
        clans = read_clans(db_session)
        clan = next((c for c in clans if c.id == clan_id), None)
        if not clan:
            bot.answer_callback_query(
                call.id,
                text=strings[user.lang].clan_not_found
            )
            return
            
        top_players = get_top_players_by_clan(db_session, clan_id)
        top_player_title = get_top_clan_player_title(db_session, clan_id)
        
        # Format the list
        message_lines = [strings[user.lang].top_players_by_clan_header.format(clan_name=clan.name)]
        
        for i, player in enumerate(top_players, 1):
            message_lines.append(
                f"{i}. @{player.username} – {int(player.rating)}: {player.wins}-{player.losses}-{int(player.win_rate*100)}%"
            )
        
        message_lines.append("")
        if top_player_title:
            message_lines.append(f"@{top_player_title.username} – {top_player_title.title}")
        
        data["state"].set(TopState.select_top_type)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="\n".join(message_lines),
            reply_markup=create_top_selection_markup(user.lang)
        )

    @bot.callback_query_handler(func=lambda call: call.data == "top_heroes", state=TopState.select_top_type)
    def show_top_heroes(call: types.CallbackQuery, data: dict):
        user = data["user"]
        top_heroes = get_top_heroes(db_session)
        
        # Format the list
        message_lines = [strings[user.lang].top_heroes_header]
        
        for i, hero in enumerate(top_heroes, 1):
            message_lines.append(
                f"{i}. {hero.name} – {int(hero.rating)}: {hero.wins}-{hero.losses}-{int(hero.win_rate*100)}%"
            )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="\n".join(message_lines),
            reply_markup=create_top_selection_markup(user.lang)
        )

    @bot.callback_query_handler(func=lambda call: call.data == "top_clans", state=TopState.select_top_type)
    def show_top_clans(call: types.CallbackQuery, data: dict):
        user = data["user"]
        top_clans = get_top_clans(db_session)
        
        # Format the list
        message_lines = [strings[user.lang].top_clans_header]
        
        for i, clan in enumerate(top_clans, 1):
            message_lines.append(
                f"{i}. Клан {clan.name} – {int(clan.rating)}: {clan.wins}-{clan.losses}-{int(clan.win_rate*100)}%"
            )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="\n".join(message_lines),
            reply_markup=create_top_selection_markup(user.lang)
        )

    @bot.callback_query_handler(func=lambda call: call.data == "top_back", state=TopState.select_clan)
    def back_to_top_selection(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(TopState.select_top_type)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=strings[user.lang].select_top_type,
            reply_markup=create_top_selection_markup(user.lang)
        )

    @bot.callback_query_handler(func=lambda call: call.data == "top_exit", state=TopState.select_top_type)
    def exit_top_command(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].finish()
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=strings[user.lang].goodbye
        )

    # Set timeout for top command
    @bot.middleware_handler(update_types=['message', 'callback_query'])
    def timeout_handler(bot_instance, update):
        if hasattr(update, 'message'):
            message = update.message
        elif hasattr(update, 'callback_query'):
            message = update.callback_query.message
        else:
            return

        # Check if the user is in a top state
        state_data = bot_instance.current_states.get_state(message.chat.id, message.from_user.id)
        if not state_data or not state_data.startswith('TopState'):
            return
            
        # Create task to check timeout
        async def check_timeout():
            await asyncio.sleep(120)  # 2 minutes
            current_state = bot_instance.current_states.get_state(message.chat.id, message.from_user.id)
            if current_state and current_state.startswith('TopState'):
                bot_instance.current_states.finish(message.chat.id, message.from_user.id)
                bot_instance.send_message(
                    chat_id=message.chat.id,
                    text=strings.get(message.from_user.language_code, strings['en']).timeout
                )
                
        asyncio.create_task(check_timeout())
