import threading
from pathlib import Path

from omegaconf import OmegaConf


# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

# Timeout duration in seconds
TIMEOUT_DURATION = 120
user_timers = {}
user_messages = {}  # Store the last message_id for each user


def start_timeout(bot, chat_id, message_id):
    """Start a timeout for the menu."""
    timer = threading.Timer(TIMEOUT_DURATION, timeout_handler, args=(chat_id, message_id, bot))
    timer.start()
    user_timers[chat_id] = timer
    user_messages[chat_id] = message_id  # Store the message_id


def cancel_timeout(chat_id):
    """Cancel an active timeout."""
    if chat_id in user_timers:
        user_timers[chat_id].cancel()
        del user_timers[chat_id]
        if chat_id in user_messages:
            del user_messages[chat_id]


def timeout_handler(chat_id: int, message_id: int, bot):
    """Handle menu timeout."""
    # Use the stored message_id
    if chat_id in user_messages:
        message_id = user_messages[chat_id]
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=strings["ru"].timeout
            )
        except Exception as e:
            print(f"Failed to edit message: {e}")

        try:
            bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
        except Exception as e:
            print(f"Failed to remove reply markup: {e}")
            pass
    
    # Remove state
    bot.delete_state(chat_id)

    # Clean up stored message_id
    if chat_id in user_messages:
        del user_messages[chat_id]