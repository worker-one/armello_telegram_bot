import logging
from pathlib import Path

from omegaconf import OmegaConf
from telebot import TeleBot, types
from telebot.states import State, StatesGroup

from ..common.service import cancel_timeout, user_messages
from ..database.core import db_session
from ..herorating import service as hero_service
from ..rating.service import read_clans
from ..title import service as title_service
from .markup import (
    create_clan_selection_markup,
    create_top_selection_markup,
)
from .service import get_player_clan_ratings, get_player_hero_ratings, get_top_clans, get_top_heroes, get_top_players

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

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
        # start_timeout(bot, message.chat.id, sent_message.message_id)
        # user_messages[message.chat.id] = sent_message.message_id

    @bot.callback_query_handler(func=lambda call: call.data == "top_players_overall", state=TopState.select_top_type)
    def show_top_players_overall(call: types.CallbackQuery, data: dict):
        user = data["user"]
        # Use the new service function
        top_players = get_top_players(db_session, limit=10, sort_by="rating")

        message_lines = [strings[user.lang].top_players_overall_header]
        for i, player in enumerate(top_players, 1):
            message_lines.append(
                f"{i}. @{player['username']} – {player['rating']}: {player['wins']}-{player['losses']}-{player['win_rate']}%"
            )
        message_lines.append("\n" + strings[user.lang].top_players_explanation)
        
        title = title_service.get_title(db_session, category="overall")
        top_player_string = f"@{title.player.username} – {title.title}"
        message_lines.append(top_player_string)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="\n".join(message_lines),
            reply_markup=create_top_selection_markup(user.lang)
        )
        # user_messages[call.message.chat.id] = call.message.message_id
        # start_timeout(bot, call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == "top_players_by_hero", state=TopState.select_top_type)
    def ask_for_hero_name(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(TopState.enter_hero_name)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=strings[user.lang].enter_hero_name
        )
        user_messages[call.message.chat.id] = call.message.message_id

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

        # Use the new service function - filter player rankings by hero's associated heroes
        top_players = get_player_hero_ratings(
            db_session,
            limit=10,
            sort_by="rating",
            hero_id=hero.id  # Filter by clan instead of specific hero for better results
        )
        
        message_lines = [strings[user.lang].top_players_by_hero_header.format(hero_name=hero.name)]
        for i, player in enumerate(top_players, 1):
            message_lines.append(
                f"{i}. @{player['username']} – {player['rating']}: {player['wins']}-{player['losses']}-{player['win_rate']}%"
            )
        sent_message = bot.reply_to(
            message,
            text="\n".join(message_lines),
            reply_markup=create_top_selection_markup(user.lang)
        )
        user_messages[message.chat.id] = sent_message.message_id
        data["state"].set(TopState.select_top_type)


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
        user_messages[call.message.chat.id] = call.message.message_id

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

        # Get player clan ratings
        top_players = get_player_clan_ratings(db_session, sort_by="rating", clan_id=clan_id, limit=10)

        # For the top player title, get the highest-rated player
        top_player_title = None
        if top_players:
            top_player = top_players[0]
            clan_name = clan.name.split(' ')[1]  # Extract clan name
            title = title_service.read_clan_title(db_session, clan_id=clan.id)
            top_player_title = {"player": top_player, "title": title.title}

        # Format the list
        message_lines = [strings[user.lang].top_players_by_clan_header.format(clan_name=clan.name.split(' ')[1])]

        for i, player in enumerate(top_players, 1):
            message_lines.append(
                f'{i}. {player["username"]} – {player["rating"]}: {player["wins"]}-{player["losses"]}-{player["win_rate"]}%'
            )

        message_lines.append("")
        if top_player_title:
            message_lines.append(f"{top_player_title['player']['username']} – {top_player_title['title']}")

        data["state"].set(TopState.select_top_type)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="\n".join(message_lines),
            reply_markup=create_top_selection_markup(user.lang)
        )
        user_messages[call.message.chat.id] = call.message.message_id

    @bot.callback_query_handler(func=lambda call: call.data == "top_heroes", state=TopState.select_top_type)
    def show_top_heroes(call: types.CallbackQuery, data: dict):
        user = data["user"]
        # Use the new service function
        top_heroes = get_top_heroes(db_session, limit=100, sort_by="rating")
        
        # Format the list
        message_lines = [strings[user.lang].top_heroes_header]
        
        for i, hero in enumerate(top_heroes, 1):
            message_lines.append(
                f"{i}. {hero['name']} – {hero['rating']}: {hero['wins']}-{hero['losses']}-{hero['win_rate']}%"
            )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="\n".join(message_lines),
            reply_markup=create_top_selection_markup(user.lang)
        )
        user_messages[call.message.chat.id] = call.message.message_id

    @bot.callback_query_handler(func=lambda call: call.data == "top_clans", state=TopState.select_top_type)
    def show_top_clans(call: types.CallbackQuery, data: dict):
        user = data["user"]
        # Use the new service function
        top_clans = get_top_clans(db_session, sort_by="rating")
        
        # Format the list
        message_lines = [strings[user.lang].top_clans_header]
        
        for i, clan in enumerate(top_clans, 1):
            # Extract clan name - assumes format "Clan {Name}"
            clan_name = clan['name'].split(' ')[1] if ' ' in clan['name'] else clan['name']
            message_lines.append(
                f"{i}. Клан {clan_name} – {clan['rating']}: {clan['wins']}-{clan['losses']}-{clan['win_rate']}%"
            )
        
        # # Add win type distribution for all clans
        # message_lines.append("\n🏆 Распределение типов побед:")
        # for clan in top_clans:
        #     clan_name = clan['name'].split(' ')[1] if ' ' in clan['name'] else clan['name']
        #     win_types = []
        #     if clan['prestige_wins'] > 0:
        #         win_types.append(f"Prestige: {clan['prestige_wins']}")
        #     if clan['murder_wins'] > 0:
        #         win_types.append(f"Murder: {clan['murder_wins']}")
        #     if clan['decay_wins'] > 0:
        #         win_types.append(f"Decay: {clan['decay_wins']}")
        #     if clan['stones_wins'] > 0:
        #         win_types.append(f"Stones: {clan['stones_wins']}")
                
        #     message_lines.append(f"Клан {clan_name}: {', '.join(win_types)}")
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="\n".join(message_lines),
            reply_markup=create_top_selection_markup(user.lang)
        )
        user_messages[call.message.chat.id] = call.message.message_id

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
        user_messages[call.message.chat.id] = call.message.message_id

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
        user_messages[call.message.chat.id] = call.message.message_id