import logging
from pathlib import Path

from omegaconf import OmegaConf
from telebot import TeleBot, types
from telebot.states import State, StatesGroup

from ..database.core import db_session
from ..herorating import service as hero_service
from .markup import (
    create_clan_selection_markup,
    create_rating_menu_markup,
)
from .service import (
    get_player_clan_rating,
    get_player_hero_rating,
    get_player_overall_rating,
    read_clan,
    read_clans,
    read_general_hero_rating,
    read_player,
    rebuild_all_ratings,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

# Load the database session
 

# Define States
class RatingState(StatesGroup):
    """Rating states"""
    select_player = State()
    select_rating_type = State()
    enter_hero_name = State()
    select_clan = State()


def register_handlers(bot: TeleBot):
    """Register rating handlers"""
    logger.info("Registering rating handlers")



    @bot.message_handler(commands=["rating"])
    def rating_command(message: types.Message, data: dict):
        user = data["user"]
        data["state"].set(RatingState.select_player)

        sent_message = bot.reply_to(
            message,
            text=strings[user.lang].mention_player
            #reply_markup=types.ForceReply(selective=True)
        )
        # start_timeout(bot, message.chat.id, sent_message.message_id)
        # user_messages[message.chat.id] = sent_message.message_id

    @bot.message_handler(commands=["myrating"])
    def myrating_command(message: types.Message, data: dict):
        user = data["user"]

        player = read_player(db_session, user_id=user.id)

        if not player:
            player = read_player(db_session, username=user.username)

        if player:

            # Store the selected player in state data
            data["state"].set(RatingState.select_rating_type)
            data["state"].add_data(selected_player=player.id)
            data["state"].add_data(selected_player_username=user.username)


            sent_message = bot.reply_to(
                message,
                text=strings[user.lang].select_rating_type,
                reply_markup=create_rating_menu_markup(user.lang, include_other_player=False)
            )
            # user_messages[message.chat.id] = sent_message.message_id
            # start_timeout(bot, message.chat.id, sent_message.message_id)
        else:
            bot.reply_to(
                message,
                text=strings[user.lang].myrating_not_found
            )


    @bot.message_handler(state=RatingState.select_player)
    def process_player_selection(message: types.Message, data: dict):
        user = data["user"]

        # Check if the message contains username mentions
        if message.entities and any(entity.type == "mention" for entity in message.entities):
            for entity in message.entities:
                if entity.type == "mention":
                    # Extract username (removing @ symbol)
                    username = message.text[entity.offset+1:entity.offset+entity.length]
                    player = read_player(db_session, username=username)

                    if player:
                        # Store the selected player in state data
                        data["state"].add_data(selected_player=player.id)
                        data["state"].add_data(selected_player_username=username)
                        data["state"].set(RatingState.select_rating_type)

                        bot.reply_to(
                            message,
                            text=strings[user.lang].select_rating_type,
                            reply_markup=create_rating_menu_markup(user.lang)
                        )
                    else:
                        bot.reply_to(
                            message,
                            text=strings[user.lang].player_not_found
                        )
                    return

        # If no valid mention was found
        bot.reply_to(
            message,
            text=strings[user.lang].invalid_mention,
            reply_markup=types.ForceReply(selective=True)
        )

    @bot.callback_query_handler(func=lambda call: call.data == "rating_overall", state=RatingState.select_rating_type)
    def show_overall_rating(call: types.CallbackQuery, data: dict):
        user = data["user"]

        with data["state"].data() as state_data:
            player_id = state_data.get("selected_player")
            username = state_data.get("selected_player_username")

        rating = get_player_overall_rating(db_session, player_id)

        if rating:
            player = read_player(db_session, player_id=player_id)
            titles = ""
            if player.titles:
                titles = "; ".join([title.title for title in player.titles]).strip("; ")
            if player.custom_titles:
                titles += "; " + "; ".join([title.title for title in player.custom_titles]).strip("; ")
            if not titles:
                titles = strings[user.lang].no_titles
            message_text = strings[user.lang].player_overall_rating.format(
                username=username,
                rating=rating.rating,
                wins=rating.wins,
                losses=rating.losses,
                win_rate=f"{rating.win_rate*100:.1f}%",
                prestige_wins=rating.prestige_wins,
                murder_wins=rating.murder_wins,
                decay_wins=rating.decay_wins,
                stones_wins=rating.stones_wins,
                titles=titles,
            )
        else:
            message_text = strings[user.lang].no_rating_data.format(username=username)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            reply_markup=create_rating_menu_markup(user.lang)
        )
        # user_messages[call.message.chat.id] = call.message.message_id
        # start_timeout(bot, call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == "rating_hero", state=RatingState.select_rating_type)
    def enter_hero_name_for_rating(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(RatingState.enter_hero_name)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=strings[user.lang].enter_hero_name
        )
        # user_messages[call.message.chat.id] = call.message.message_id
        # start_timeout(bot, call.message.chat.id, call.message.message_id)

    @bot.message_handler(state=RatingState.enter_hero_name)
    def process_hero_name(message: types.Message, data: dict):
        user = data["user"]
        hero_name = message.text

        with data["state"].data() as state_data:
            player_id = state_data.get("selected_player")
            username = state_data.get("selected_player_username")

        hero = hero_service.read_hero(db_session, hero_name=hero_name)

        if not hero:
            bot.reply_to(
                message,
                text=strings[user.lang].hero_not_found,
                reply_markup=types.ForceReply(selective=True)
            )
            return

        rating = get_player_hero_rating(db_session, player_id, hero.id)

        data["state"].set(RatingState.select_rating_type)

        if rating:
            message_text = strings[user.lang].player_hero_rating.format(
                username=username,
                hero_name=hero.name,
                rating=rating.rating,
                wins=rating.wins,
                losses=rating.losses,
                prestige_wins=rating.prestige_wins,
                murder_wins=rating.murder_wins,
                decay_wins=rating.decay_wins,
                stones_wins=rating.stones_wins,
                win_rate=f"{rating.win_rate*100:.1f}%"
            )
        else:
            message_text = strings[user.lang].no_hero_rating_data.format(
                username=username,
                hero_name=hero.name
            )

        bot.reply_to(
            message,
            text=message_text,
            reply_markup=create_rating_menu_markup(user.lang)
        )


    @bot.callback_query_handler(func=lambda call: call.data == "rating_clan", state=RatingState.select_rating_type)
    def select_clan_for_rating(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(RatingState.select_clan)

        clans = read_clans(db_session)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=strings[user.lang].select_clan,
            reply_markup=create_clan_selection_markup(user.lang, clans)
        )
        # user_messages[call.message.chat.id] = call.message.message_id
        # start_timeout(bot, call.message.chat.id, call.message.message_id)


    @bot.callback_query_handler(
        func=lambda call: call.data.startswith("player_clan_rating_"),
        state=RatingState.select_clan
    )
    def show_clan_rating(call: types.CallbackQuery, data: dict):
        user = data["user"]
        clan_id = int(call.data.split("_")[3])
        clan = read_clan(db_session, clan_id)

        with data["state"].data() as state_data:
            player_id = int(state_data.get("selected_player"))
            username = state_data.get("selected_player_username")

        rating = get_player_clan_rating(db_session, player_id, clan_id)

        data["state"].set(RatingState.select_rating_type)

        if rating:
            message_text = strings[user.lang].player_clan_rating.format(
                username=username,
                clan_name=rating.clan_name.split(" ")[1],
                rating=rating.rating,
                wins=rating.wins,
                prestige_wins=rating.prestige_wins,
                murder_wins=rating.murder_wins,
                decay_wins=rating.decay_wins,
                stones_wins=rating.stones_wins,
                losses=rating.losses,
                win_rate=f"{rating.win_rate*100:.1f}%"
            )
        else:
            message_text = strings[user.lang].no_clan_rating_data.format(
                username=username,
                clan_name=clan.clan_name
            )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            reply_markup=create_rating_menu_markup(user.lang)
        )

    @bot.callback_query_handler(func=lambda call: call.data == "rating_other_player", state=RatingState.select_rating_type)
    def select_another_player(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(RatingState.select_player)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=strings[user.lang].mention_player
        )

        # Force user to reply with a username mention
        bot.reply_to(
            call.message,
            text=strings[user.lang].mention_player_prompt,
            reply_markup=types.ForceReply(selective=True)
        )

        # user_messages[call.message.chat.id] = call.message.message_id
        # start_timeout(bot, call.message.chat.id, call.message.message_id)


    @bot.callback_query_handler(func=lambda call: call.data == "rating_back",
                               state=[RatingState.enter_hero_name, RatingState.select_clan])
    def back_to_rating_selection(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(RatingState.select_rating_type)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=strings[user.lang].select_rating_type,
            reply_markup=create_rating_menu_markup(user.lang)
        )
        # user_messages[call.message.chat.id] = call.message.message_id
        # start_timeout(bot, call.message.chat.id, call.message.message_id)


    @bot.callback_query_handler(func=lambda call: call.data == "cancel", state=RatingState.select_rating_type)
    def cancel_rating_selection(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].delete()

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=strings[user.lang].rating_cancelled
        )

