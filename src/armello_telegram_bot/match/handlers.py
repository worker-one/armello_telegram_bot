import logging
import re
import time
from pathlib import Path
from threading import Timer

from omegaconf import OmegaConf
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException
from telebot.states import State, StatesGroup

from ..database.core import get_session
from ..auth.service import read_user
from .models import Hero, Player
from .schemas import MatchCreate, ParticipantCreate
from .service import create_match, read_hero, read_player
from ..rating import service as rating_service
from ..title import service as title_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

# Load the database session
db_session = get_session()

# Define States
class MatchState(StatesGroup):
    """ Match states """
    upload_screenshot = State()
    enter_players = State()
    enter_winner = State()
    enter_win_type = State()
    enter_hero = State()
    confirm_match = State()
    all = [upload_screenshot, enter_players, enter_winner, enter_win_type, enter_hero, confirm_match]


# Dictionary to store timeout timers for match reports
match_timeout_timers = {}


def register_handlers(bot: TeleBot):
    """Register match handlers"""
    logger.info("Registering match handlers")

    def cancel_match_due_to_timeout(chat_id, message_id, data):
        """Cancel match creation due to timeout"""
        # Check if the state is still active
        if data["state"] and not data["state"].is_finished():
            user = data.get("user")
            lang = user.lang if user else "en"

            bot.send_message(
                chat_id,
                strings[lang].match_timeout,
                reply_to_message_id=message_id
            )
            
            # Reset the state
            if data["state"]:
                data["state"].delete()
            
            # Clean up the timer reference
            if chat_id in match_timeout_timers:
                del match_timeout_timers[chat_id]

    def reset_timeout_timer(chat_id, message_id, data):
        """Reset the timeout timer for the match report"""
        # Cancel existing timer if any
        if chat_id in match_timeout_timers and match_timeout_timers[chat_id]:
            match_timeout_timers[chat_id].cancel()
        
        # Create a new timer (5 minutes timeout)
        match_timeout_timers[chat_id] = Timer(
            300,  # 5 minutes in seconds
            cancel_match_due_to_timeout,
            args=[chat_id, message_id, data]
        )
        match_timeout_timers[chat_id].start()
    
    @bot.message_handler(commands=["match"])
    def start_match_report(message: types.Message, data: dict):
        """Start match report process"""
        # Only allow in group chats
        if message.chat.type not in ["group", "supergroup"]:
            bot.reply_to(message, "This command only works in group chats.")
            return

        user = data["user"]
        msg = bot.reply_to(
            message,
            strings[user.lang].upload_screenshot_prompt
        )

        # Initialize the state
        data["state"].set(MatchState.upload_screenshot)
        data["state"].add_data(
            original_message_id=message.message_id,
            messages_to_delete=[msg.message_id]
        )

        # Start timeout timer
        reset_timeout_timer(message.chat.id, message.message_id, data)

    @bot.message_handler(commands=["cancel"], state=[
        MatchState.upload_screenshot, MatchState.enter_players, 
        MatchState.enter_winner, MatchState.enter_win_type, 
        MatchState.enter_hero, MatchState.confirm_match
    ])
    def cancel_match_command(message: types.Message, data: dict):
        """Cancel match report with /cancel command"""
        user = data["user"]

        # Get messages to delete
        with data["state"].data() as state_data:
            messages_to_delete = state_data.get("messages_to_delete", [])
            original_message_id = state_data.get("original_message_id")
        
        # Send cancellation message
        bot.reply_to(
            message, 
            strings[user.lang].process_cancelled,
            reply_to_message_id=original_message_id
        )
        
        # Clean up the timer
        if message.chat.id in match_timeout_timers:
            match_timeout_timers[message.chat.id].cancel()
            del match_timeout_timers[message.chat.id]
        
        # Reset the state
        data["state"].delete()
        
        # Delete all intermediate messages
        for msg_id in messages_to_delete:
            try:
                bot.delete_message(message.chat.id, msg_id)
            except ApiTelegramException:
                logger.warning(f"Failed to delete message {msg_id}")
        
        # Also delete the cancel command
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except ApiTelegramException:
            pass

    @bot.message_handler(content_types=['photo'], state=MatchState.upload_screenshot)
    def process_screenshot(message: types.Message, data: dict):
        """Process uploaded screenshot"""
        user = data["user"]
        # Get the photo with highest resolution
        photo = message.photo[-1]
        
        # Save file_id to state
        data["state"].add_data(screenshot=photo.file_id)
        
        # Ask for players
        msg = bot.reply_to(
            message,
            strings[user.lang].enter_players_prompt
        )
        
        # Track message for later deletion
        with data["state"].data() as state_data:
            messages_to_delete = state_data.get("messages_to_delete", [])
            messages_to_delete.append(msg.message_id)
            messages_to_delete.append(message.message_id)
            data["state"].add_data(messages_to_delete=messages_to_delete)

        # Update state
        data["state"].set(MatchState.enter_players)

        # Reset timeout timer
        reset_timeout_timer(message.chat.id, message.message_id, data)

    @bot.message_handler(state=MatchState.enter_players)
    def process_players(message: types.Message, data: dict):
        """Process the list of players participating in the match"""
        user = data["user"]
        # Extract usernames using regex to find @ mentions
        usernames = re.findall(r'@(\w+)', message.text)

        if not usernames or len(usernames) != 4:
            msg = bot.reply_to(message, strings[user.lang].invalid_players_count)

            # Track message for later deletion
            with data["state"].data() as state_data:
                messages_to_delete = state_data.get("messages_to_delete", [])
                messages_to_delete.append(msg.message_id)
                messages_to_delete.append(message.message_id)
                data["state"].add_data(messages_to_delete=messages_to_delete)
            return

        # Check that players exist in the database if not create them
        for username in usernames:
            player = read_player(db_session, username=username)
            if not player:
                # Check if the user exists in the database
                retrieved_user = read_user(db_session, username=username)
                if retrieved_user:
                    # Create player
                    player = Player(user_id=retrieved_user.id, username=username)
                else:
                    player = Player(username=username)
                db_session.add(player)
                db_session.commit()

        # Save players to state
        data["state"].add_data(players=usernames)

        # Ask for winner
        msg = bot.reply_to(message, strings[user.lang].select_winner_prompt)
        
        # Track messages for later deletion
        with data["state"].data() as state_data:
            messages_to_delete = state_data.get("messages_to_delete", [])
            messages_to_delete.append(msg.message_id)
            messages_to_delete.append(message.message_id)
            data["state"].add_data(messages_to_delete=messages_to_delete)
        
        # Update state
        data["state"].set(MatchState.enter_winner)
        
        # Reset timeout timer
        reset_timeout_timer(message.chat.id, message.message_id, data)

    @bot.message_handler(state=MatchState.enter_winner)
    def process_winner(message: types.Message, data: dict):
        """Process winner selection"""
        user = data["user"]
        
        # Extract username using regex
        winner_match = re.search(r'@(\w+)', message.text)
        if not winner_match:
            msg = bot.reply_to(message, strings[user.lang].invalid_winner_format)
            
            # Track message for later deletion
            with data["state"].data() as state_data:
                messages_to_delete = state_data.get("messages_to_delete", [])
                messages_to_delete.append(msg.message_id)
                messages_to_delete.append(message.message_id)
                data["state"].add_data(messages_to_delete=messages_to_delete)
            return
        
        winner_username = winner_match.group(1)
        
        # Check if winner is in players list
        with data["state"].data() as state_data:
            players = state_data.get("players", [])
            if winner_username not in players:
                msg = bot.reply_to(message, strings[user.lang].winner_not_in_players)
                
                # Track message for later deletion
                messages_to_delete = state_data.get("messages_to_delete", [])
                messages_to_delete.append(msg.message_id)
                messages_to_delete.append(message.message_id)
                data["state"].add_data(messages_to_delete=messages_to_delete)
                return
        
        # Save winner to state
        data["state"].add_data(winner_username=winner_username)
        
        # Ask for win type with inline keyboard
        markup = types.InlineKeyboardMarkup(row_width=2)
        win_types = {
            "prestige": "Престиж",
            "murder": "Убийство",
            "decay": "Гниль",
            "stones": "Камни Духа"
        }
        
        for win_type, label in win_types.items():
            markup.add(types.InlineKeyboardButton(label, callback_data=f"wintype:{win_type}"))
        
        msg = bot.reply_to(
            message, 
            strings[user.lang].select_win_type,
            reply_markup=markup
        )
        
        # Track messages for later deletion
        with data["state"].data() as state_data:
            messages_to_delete = state_data.get("messages_to_delete", [])
            messages_to_delete.append(msg.message_id)
            messages_to_delete.append(message.message_id)
            data["state"].add_data(messages_to_delete=messages_to_delete)
        
        # Update state
        data["state"].set(MatchState.enter_win_type)
        
        # Reset timeout timer
        reset_timeout_timer(message.chat.id, message.message_id, data)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("wintype:"), state=MatchState.enter_win_type)
    def process_win_type(call: types.CallbackQuery, data: dict):
        """Process win type selection"""
        user = data["user"]
        win_type = call.data.split(':')[1]
        data["state"].add_data(win_type=win_type)
        
        # Setup for hero selection
        with data["state"].data() as state_data:
            players = state_data.get("players", [])
            data["state"].add_data(
                hero_selection={},
                current_player_index=0
            )
        
        # Ask for first hero
        msg = bot.send_message(
            call.message.chat.id,
            f"За какого героя играл @{players[0]}?"
        )
        
        # Track messages for later deletion
        with data["state"].data() as state_data:
            messages_to_delete = state_data.get("messages_to_delete", [])
            messages_to_delete.append(msg.message_id)
            messages_to_delete.append(call.message.message_id)
            data["state"].add_data(messages_to_delete=messages_to_delete)
        
        # Update state
        data["state"].set(MatchState.enter_hero)
        
        # Reset timeout timer
        reset_timeout_timer(call.message.chat.id, call.message.message_id, data)
        
        # Answer callback to remove loading state
        bot.answer_callback_query(call.id)

    @bot.message_handler(state=MatchState.enter_hero)
    def process_hero_selection(message: types.Message, data: dict):
        """Process hero selection one player at a time"""
        user = data["user"]
        
        # Get current state data
        with data["state"].data() as state_data:
            players = state_data.get("players", [])
            current_index = state_data.get("current_player_index", 0)
            hero_selection = state_data.get("hero_selection", {})
            current_player = players[current_index]
        
        # Try to find hero in database
        hero_name = message.text.strip()
        hero = read_hero(db_session, hero_name)
        if not hero:
            msg = bot.reply_to(
                message, 
                f"Герой '{hero_name}' не найден. Пожалуйста, проверьте имя и попробуйте снова."
            )

            # Track message for later deletion
            with data["state"].data() as state_data:
                messages_to_delete = state_data.get("messages_to_delete", [])
                messages_to_delete.append(msg.message_id)
                messages_to_delete.append(message.message_id)
                data["state"].add_data(messages_to_delete=messages_to_delete)
            return
        
        # Save hero for current player
        hero_selection[current_player] = hero.id
        current_index += 1
        
        # Update state data
        data["state"].add_data(
            hero_selection=hero_selection,
            current_player_index=current_index
        )
        
        # Track message for deletion
        with data["state"].data() as state_data:
            messages_to_delete = state_data.get("messages_to_delete", [])
            messages_to_delete.append(message.message_id)
            data["state"].add_data(messages_to_delete=messages_to_delete)
        
        # Check if all heroes are selected
        if current_index < len(players):
            # Ask for next hero
            msg = bot.send_message(
                message.chat.id,
                f"За какого героя играл @{players[current_index]}?"
            )
            
            # Track message for later deletion
            with data["state"].data() as state_data:
                messages_to_delete = state_data.get("messages_to_delete", [])
                messages_to_delete.append(msg.message_id)
                data["state"].add_data(messages_to_delete=messages_to_delete)
        else:
            # All heroes selected, create match report preview
            msg = bot.send_message(
                message.chat.id,
                "Принято. Формирую отчет о матче..."
            )
            
            # Track message for deletion
            with data["state"].data() as state_data:
                messages_to_delete = state_data.get("messages_to_delete", [])
                messages_to_delete.append(msg.message_id)
                data["state"].add_data(messages_to_delete=messages_to_delete)
            
            # Generate match preview
            with data["state"].data() as state_data:
                players = state_data.get("players", [])
                hero_selection = state_data.get("hero_selection", {})
                winner = state_data.get("winner_username", "")
                win_type = state_data.get("win_type", "")
                screenshot = state_data.get("screenshot", "")
            
            # Translate win type
            win_type_display = {
                "prestige": "Престиж",
                "murder": "Убийство Короля",
                "decay": "Гниль",
                "stones": "Камни Духа"
            }.get(win_type, win_type.capitalize())
            
            # Generate match ID (in a real implementation, this would be from DB)
            # Using timestamp as temporary ID
            match_id = str(int(time.time()))[-6:]
            data["state"].add_data(match_id=match_id)
            
            # Create summary
            summary = f"Матч №{match_id}\n"
            summary += f"Победа через {win_type_display}\n\n"
            
            # Add player info
            for username in players:
                hero_id = hero_selection.get(username)
                hero_name = db_session.query(Hero.name).filter(Hero.id == hero_id).scalar()

                winner_mark = " 🏆" if username == winner else ""
                summary += f"@{username} - {hero_name}{winner_mark}\n"

            # Send match preview with confirmation buttons
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("Да", callback_data="match:confirm"),
                types.InlineKeyboardButton("Нет", callback_data="match:cancel")
            )

            try:
                msg = bot.send_photo(
                    message.chat.id,
                    screenshot,
                    caption=f"{summary}\n\nВсе верно?",
                    reply_markup=markup
                )
            except ApiTelegramException:
                msg = bot.send_message(
                    message.chat.id,
                    f"{summary}\n\n(Ошибка загрузки скриншота)\n\nВсе верно?",
                    reply_markup=markup
                )

            # Track message for special handling (this one won't be deleted on confirm)
            data["state"].add_data(final_report_message_id=msg.message_id)

            # Update state
            data["state"].set(MatchState.confirm_match)

        # Reset timeout timer
        reset_timeout_timer(message.chat.id, message.message_id, data)


    @bot.callback_query_handler(func=lambda call: call.data == "match:confirm", state=MatchState.confirm_match)
    def confirm_match(call: types.CallbackQuery, data: dict):
        """Save match to database"""
        user = data["user"]

        with data["state"].data() as match_data:
            players = match_data.get("players", [])
            hero_selection = match_data.get("hero_selection", {})
            winner = match_data.get("winner_username", "")
            win_type = match_data.get("win_type", "")
            screenshot = match_data.get("screenshot", "")
            messages_to_delete = match_data.get("messages_to_delete", [])
            original_message_id = match_data.get("original_message_id")
            final_report_message_id = match_data.get("final_report_message_id")
            match_id = match_data.get("match_id", "1")

        try:
            # Prepare data for match creation
            participants = []
            for username in players:
                hero_id = hero_selection.get(username)
                participants.append(ParticipantCreate(username=username, hero_id=hero_id))

            # Create match
            match_create = MatchCreate(
                screenshot=screenshot,
                win_type=win_type,
                participants=participants,
                winner_username=winner
            )
            match = create_match(db_session, match_create)

            # Update ratings
            rating_service.update_ratings_after_match(db_session, match)

            # Update titles
            title_service.update_titles_after_match(db_session)

            # Clean up the timer
            if call.message.chat.id in match_timeout_timers:
                match_timeout_timers[call.message.chat.id].cancel()
                del match_timeout_timers[call.message.chat.id]

            # Delete all intermediate messages
            for msg_id in messages_to_delete:
                try:
                    bot.delete_message(call.message.chat.id, msg_id)
                except ApiTelegramException:
                    logger.warning(f"Failed to delete message {msg_id}")

            # Also delete original /match command
            try:
                bot.delete_message(call.message.chat.id, original_message_id)
            except ApiTelegramException:
                pass
            
            # Update the final report message (remove the confirmation buttons)
            win_type_display = {
                "prestige": "Престиж",
                "murder": "Убийство Короля",
                "decay": "Гниль",
                "stones": "Камни Духа"
            }.get(win_type, win_type.capitalize())

            final_report = f"Матч №{match_id}\n"
            final_report += f"Победа через {win_type_display}\n\n"

            for username in players:
                hero_id = hero_selection.get(username)
                hero_name = db_session.query(Hero.name).filter(Hero.id == hero_id).scalar()

                winner_mark = " 🏆" if username == winner else ""
                final_report += f"@{username} - {hero_name}{winner_mark}\n"

            # Update the message without buttons
            try:
                bot.edit_message_caption(
                    caption=final_report,
                    chat_id=call.message.chat.id,
                    message_id=final_report_message_id
                )
                # Send notification
                bot.answer_callback_query(
                    call.id,
                    text=strings[user.lang].match_recorded_success
                )
            except ApiTelegramException:
                bot.edit_message_text(
                    text=final_report,
                    chat_id=call.message.chat.id,
                    message_id=final_report_message_id
                )

            # Reset state
            data["state"].delete()

        except Exception as e:
            logger.error(f"Error saving match: {e}")
            bot.answer_callback_query(
                call.id,
                text="Ошибка при сохранении матча. Пожалуйста, попробуйте снова."
            )

            # Clean up the timer
            if call.message.chat.id in match_timeout_timers:
                match_timeout_timers[call.message.chat.id].cancel()
                del match_timeout_timers[call.message.chat.id]

            data["state"].delete()

    @bot.callback_query_handler(func=lambda call: call.data == "match:cancel", state=MatchState.confirm_match)
    def cancel_match_confirmation(call: types.CallbackQuery, data: dict):
        """Cancel match creation at the confirmation stage"""
        user = data["user"]

        with data["state"].data() as match_data:
            messages_to_delete = match_data.get("messages_to_delete", [])
            original_message_id = match_data.get("original_message_id")
            final_report_message_id = match_data.get("final_report_message_id")

        # Send cancellation message
        msg = bot.send_message(
            call.message.chat.id,
            strings[user.lang].match_cancelled,
            reply_to_message_id=original_message_id
        )

        # Clean up the timer
        if call.message.chat.id in match_timeout_timers:
            match_timeout_timers[call.message.chat.id].cancel()
            del match_timeout_timers[call.message.chat.id]

        # Delete all intermediate messages
        for msg_id in messages_to_delete:
            try:
                bot.delete_message(call.message.chat.id, msg_id)
            except ApiTelegramException:
                logger.warning(f"Failed to delete message {msg_id}")

        # Delete the final report message
        try:
            bot.delete_message(call.message.chat.id, final_report_message_id)
        except ApiTelegramException:
            pass

        # Reset state
        data["state"].delete()

        # Answer callback
        bot.answer_callback_query(call.id)


    # Handler for /cancel command
    @bot.message_handler(commands=["cancel"], state=MatchState.all)
    def cancel_handler(message: types.Message, data: dict):
        """Cancel match creation with /cancel command"""
        user = data["user"]

        # Get messages to delete
        with data["state"].data() as state_data:
            messages_to_delete = state_data.get("messages_to_delete", [])
            original_message_id = state_data.get("original_message_id")

        # Send cancellation message
        bot.reply_to(
            message, 
            strings[user.lang].process_cancelled,
            reply_to_message_id=original_message_id
        )

        # Clean up the timer
        if message.chat.id in match_timeout_timers:
            match_timeout_timers[message.chat.id].cancel()
            del match_timeout_timers[message.chat.id]

        # Reset the state
        data["state"].delete()

        # Delete all intermediate messages
        for msg_id in messages_to_delete:
            try:
                bot.delete_message(message.chat.id, msg_id)
            except ApiTelegramException:
                logger.warning(f"Failed to delete message {msg_id}")

        # Also delete the cancel command
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except ApiTelegramException:
            pass