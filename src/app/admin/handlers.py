"""Handler to show information about the application configuration."""
import logging
import logging.config
import os
from ast import Call
from datetime import datetime
from pathlib import Path

from omegaconf import OmegaConf
from telebot.types import CallbackQuery, Message

from ..database.core import db_session
from ..database.core import export_all_tables
from .markup import create_admin_menu_markup
from ..title.service import update_title_for_all_players
from ..rating.service import rebuild_all_ratings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
app_strings = config.strings


def register_handlers(bot):
    """Register about handlers"""
    logger.info("Registering `about` handlers")

    @bot.message_handler(commands=["admin"])
    def admin_menu_command(message: Message, data: dict):
        """Handler to show the admin menu."""
        user = data["user"]
        if user.role_id not in {0, 1}:
            # Inform the user that they do not have admin rights
            bot.reply_to(message, app_strings[user.lang].no_rights)
            return

        # Send the admin menu
        bot.reply_to(
            message,
            app_strings[user.lang].menu.title,
            reply_markup=create_admin_menu_markup(user.lang)
        )

    @bot.message_handler(commands=["update"])
    def update_command(message: Message, data: dict):
        sent_message = bot.reply_to(
            message,
            text="Рейтинг игроков обновляется. Пожалуйста, подождите..."
        )
        rebuild_all_ratings(db=db_session)
        bot.edit_message_text(
            chat_id=sent_message.chat.id,
            message_id=sent_message.message_id,
            text="Рейтинг игроков обновлен."
        )

        sent_message = bot.reply_to(
            message,
            text="Титулы игроков обновляется. Пожалуйста, подождите..."
        )
        update_title_for_all_players(session=db_session)
        bot.edit_message_text(
            chat_id=sent_message.chat.id,
            message_id=sent_message.message_id,
            text="Титулы игроков обновлены."
        )


    @bot.callback_query_handler(func=lambda call: call.data == "admin")
    def admin_menu_handler(call: CallbackQuery, data: dict):
        """Handler to show the admin menu."""
        user = data["user"]
        if user.role_id not in {0, 1}:
            # Inform the user that they do not have admin rights
            bot.send_message(call.message.from_user.id, app_strings[user.lang].no_rights)
            return

        # Edit message instead
        bot.edit_message_text(
            app_strings[user.lang].menu.title,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_admin_menu_markup(user.lang)
        )

    @bot.callback_query_handler(func=lambda call: call.data == "about")
    def about_handler(call: Call, data: dict):
        user_id = call.from_user.id

        config_str = OmegaConf.to_yaml(config)

        # Send config
        bot.send_message(user_id, f"```yaml\n{config_str}\n```", parse_mode="Markdown")


    @bot.callback_query_handler(func=lambda call: call.data == "export_data")
    def export_data_handler(call, data):
        user = data["user"]

        if user.role_id != 0:
            # inform that the user does not have rights
            bot.send_message(call.from_user.id, app_strings.users.no_rights[user.lang])
            return

        # Export data
        export_dir = f'./data/{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        os.makedirs(export_dir)
        try:
            export_all_tables(export_dir)
            for table in config.db.tables:
                # save as excel in temp folder and send to a user
                filename = f"{export_dir}/{table}.csv"
                bot.send_document(user.id, open(filename, "rb"))
                # remove the file
                os.remove(filename)
        except Exception as e:
            bot.send_message(user.id, str(e))
            logger.error(f"Error exporting data: {e}")


