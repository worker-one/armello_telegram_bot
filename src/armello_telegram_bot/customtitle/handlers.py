import logging
from pathlib import Path

from omegaconf import OmegaConf
from telebot import TeleBot, types
from telebot.states import State, StatesGroup

from ..common.service import start_timeout
from ..database.core import get_session
from ..match.models import Player
from .service import (
    CLAN_CATEGORIES,
    create_custom_title,
    delete_custom_title,
    get_available_titles,
    get_player_by_username,
    update_title,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

# Define States
class TitleState(StatesGroup):
    """Title states"""
    select_title = State()
    enter_title = State()


class CustomTitleState(StatesGroup):
    """Custom title states"""
    action_selection = State()  # Create or delete
    enter_custom_title = State()  # Enter new title text
    select_player_for_creation = State()  # Enter player for title
    select_player_for_deletion = State()  # Enter player to remove title
    confirm_title_deletion = State()  # Confirm title to delete


def register_handlers(bot: TeleBot):
    """Register title handlers"""
    logger.info("Registering title handlers")

    @bot.message_handler(commands=["title"])
    def title_command(message: types.Message, data: dict):
        """Handle /title command - start title selection process"""
        user = data["user"]
        with get_session() as session:
            # Check if user has a player profile
            player = session.query(Player).filter(Player.user_id == user.id).first()
            if not player:
                bot.reply_to(message, "У вас нет профиля игрока. Сначала зарегистрируйтесь.")
                return

            # Check if user is channel owner
            is_channel_owner = user.role_id in {0, 1}

            # Get titles available for this player
            available_titles = get_available_titles(session, player.id, is_channel_owner)

            if not available_titles:
                bot.reply_to(message, "Вы не занимаете первое место ни в одном из рейтингов. "
                                     "Вы не можете изменить титулы.")
                return

            # Create keyboard with available titles
            markup = types.InlineKeyboardMarkup(row_width=1)
            for category, display_name in available_titles:
                markup.add(types.InlineKeyboardButton(
                    display_name,
                    callback_data=f"title_select:{category}"
                ))

            sent_message = bot.send_message(message.chat.id, strings[user.lang].title_prompt, reply_markup=markup)
            data["state"].set(TitleState.select_title)
            start_timeout(bot, message.chat.id, sent_message.message_id)


    @bot.callback_query_handler(func=lambda call: call.data.startswith("title_select:"), state=TitleState.select_title)
    def title_selected(call: types.CallbackQuery, data: dict):
        """Handle title category selection"""
        # Extract the category from callback data
        category = call.data.split(":")[1]
        user = data["user"]

        # Store selected category in user data for next step
        data["state"].add_data(title_category=category)

        # Determine display name for category
        if category == "overall":
            display_name = "Лучший игрок комьюнити"
        else:
            display_name = CLAN_CATEGORIES.get(category, category.capitalize())

        # Ask user for new title
        bot.edit_message_text(
            text=strings[user.lang].enter_title,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

        # Move to next state
        data["state"].set(TitleState.enter_title)


    @bot.message_handler(state=TitleState.enter_title)
    def save_title(message: types.Message, data: dict):
        """Save the new title"""
        user = data["user"]
        with data["state"].data() as state_data:
            category = state_data["title_category"]
        new_title = message.text.strip()

        # Check title length
        if len(new_title) > 50:  # Set a reasonable limit
            bot.reply_to(message, strings[user.lang].title_too_long)
            return

        with get_session() as session:
            update_title(session, category, new_title)

        bot.reply_to(message, strings[user.lang].title_updated)
        # Clear state
        data["state"].delete()

    # New handlers for custom titles

    @bot.message_handler(commands=["customtitle"])
    def custom_title_command(message: types.Message, data: dict):
        """Handle /customtitle command - start custom title process"""
        user = data["user"]
        
        # Check if user is channel owner
        is_channel_owner = user.role_id in {0, 1}
        
        if not is_channel_owner:
            bot.reply_to(message, "Доступ запрещен")
            return
        
        # Create keyboard with options
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Создать титул", callback_data="customtitle_action:create"),
            types.InlineKeyboardButton("Удалить титул", callback_data="customtitle_action:delete")
        )
        
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)
        data["state"].set(CustomTitleState.action_selection)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("customtitle_action:"), 
                              state=CustomTitleState.action_selection)
    def custom_title_action_selected(call: types.CallbackQuery, data: dict):
        """Handle custom title action selection"""
        action = call.data.split(":")[1]
        data["state"].add_data(action=action)
        
        if action == "create":
            bot.edit_message_text(
                text="Какой титул вы хотите создать?",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            data["state"].set(CustomTitleState.enter_custom_title)
        elif action == "delete":
            bot.edit_message_text(
                text="Какого игрока вы хотите лишить титула? Упомяните его через @",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            data["state"].set(CustomTitleState.select_player_for_deletion)

    @bot.message_handler(state=CustomTitleState.enter_custom_title)
    def enter_custom_title(message: types.Message, data: dict):
        """Handle custom title text input"""
        title = message.text.strip()
        
        # Check title length
        if len(title) > 50:  # Set a reasonable limit
            bot.reply_to(message, "Титул слишком длинный. Максимум 50 символов.")
            return
        
        # Save the title in state
        data["state"].add_data(title=title)
        
        # Ask for player
        bot.reply_to(message, "Какому игроку вы хотите дать этот титул? Упомяните его через @")
        data["state"].set(CustomTitleState.select_player_for_creation)

    @bot.message_handler(state=CustomTitleState.select_player_for_creation)
    def select_player_for_creation(message: types.Message, data: dict):
        """Handle player selection for custom title creation"""
        # Extract username from the message
        if not message.text.strip().startswith('@'):
            bot.reply_to(message, "Пожалуйста, упомяните пользователя через @")
            return
        
        username = message.text.strip()[1:]  # Remove @ symbol
        
        with get_session() as session:
            player = get_player_by_username(session, username)
            
            if not player:
                bot.reply_to(message, "Игрок не найден")
                return
            
            with data["state"].data() as state_data:
                title = state_data["title"]
                
            # Create custom title for player
            create_custom_title(session, player.id, title)
            
        bot.reply_to(message, "Титул выдан")
        # Clear state
        data["state"].delete()

    @bot.message_handler(state=CustomTitleState.select_player_for_deletion)
    def select_player_for_deletion(message: types.Message, data: dict):
        """Handle player selection for custom title deletion"""
        # Extract username from the message
        if not message.text.strip().startswith('@'):
            bot.reply_to(message, "Пожалуйста, упомяните пользователя через @")
            return
        
        username = message.text.strip()[1:]  # Remove @ symbol
        
        with get_session() as session:
            player = get_player_by_username(session, username)
            
            if not player:
                bot.reply_to(message, "Игрок не найден")
                return
            
            # Save player_id in state
            data["state"].add_data(player_id=player.id)
            
        bot.reply_to(message, "Напишите название удаляемого титула точно так, как он написан")
        data["state"].set(CustomTitleState.confirm_title_deletion)

    @bot.message_handler(state=CustomTitleState.confirm_title_deletion)
    def confirm_title_deletion(message: types.Message, data: dict):
        """Handle title deletion confirmation"""
        title = message.text.strip()
        
        with data["state"].data() as state_data:
            player_id = state_data["player_id"]
        
        with get_session() as session:
            # Try to delete the title
            success = delete_custom_title(session, player_id, title)
            
            if success:
                bot.reply_to(message, "Титул удален")
            else:
                bot.reply_to(message, "Титул не найден")
        
        # Clear state
        data["state"].delete()
