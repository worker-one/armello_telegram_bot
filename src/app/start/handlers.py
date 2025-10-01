import logging.config
from pathlib import Path

from omegaconf import OmegaConf
from telebot.states import State, StatesGroup
from telebot.types import Message

from ..database.core import db_session
from ..auth import service as auth_services

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

# Constants
ADMIN_CODE = "feral"

 

class AppStates(StatesGroup):
    menu = State()
    admin = State()
    waiting_for_hello_message = State()

def get_string_for_user(user, key, default="Message not available"):
    try:
        return strings[user.lang][key]
    except (KeyError, AttributeError):
        logger.warning(f"Missing string for lang '{user.lang}', key '{key}'")
        return default

def register_handlers(bot):
    """Register menu handlers"""
    logger.info("Registering start handlers")

    @bot.message_handler(content_types=["new_chat_members"])
    def handle_new_member(message: Message, data: dict):
        user = data["user"]
        bot.send_message(message.chat.id, get_string_for_user(user, "start_message"))

    @bot.message_handler(commands=["start"])
    def menu_start_command(message: Message, data: dict):
        user = data["user"]
        bot.send_message(message.chat.id, get_string_for_user(user, "start_message"))

    @bot.message_handler(commands=["get_admin"])
    def handle_admin_request(message: Message, data: dict):
        user = data["user"]
        
        parts = message.text.split(" ")
        if len(parts) < 2:
            bot.send_message(message.chat.id, get_string_for_user(user, "admin_grant_failed"))
            return
            
        code = parts[1]
        if code == ADMIN_CODE:
            # grant the user admin privileges
            auth_services.grant_admin(db_session, user)
            bot.send_message(message.chat.id, get_string_for_user(user, "admin_granted"))
        else:
            bot.send_message(message.chat.id, get_string_for_user(user, "admin_grant_failed"))

    @bot.message_handler(commands=["hellomessage"])
    def hello_message_command(message: Message, data: dict):
        user = data["user"]
        data["state"].set(AppStates.waiting_for_hello_message)
        
        # Check if user is admin
        if not auth_services.is_admin(user):
            bot.send_message(message.chat.id, get_string_for_user(user, "not_admin_message"))
            data["state"].delete()
            return
        
        
        bot.send_message(message.chat.id, get_string_for_user(user, "hello_message_prompt"))

    @bot.message_handler(state=AppStates.waiting_for_hello_message)
    def process_hello_message(message: Message, data: dict):
        user = data["user"]
        new_message = message.text

        try:
            # Create a backup of the current config
            backup_config = OmegaConf.create(OmegaConf.to_container(config))
            
            # Update the configuration
            config.strings[user.lang].start_message = new_message

            # Save the updated configuration
            OmegaConf.save(config, CURRENT_DIR / "config.yaml")

            # Update the global config variable
            global strings
            strings = config.strings

            bot.send_message(message.chat.id, get_string_for_user(user, "hello_message_updated"))
            logger.info(f"Start message updated by admin {user.id}")
        except Exception as e:
            bot.send_message(message.chat.id, get_string_for_user(user, "hello_message_error"))
            logger.error(f"Failed to update start message: {e}")

        # Reset state
        data["state"].delete()