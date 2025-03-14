import threading
from pathlib import Path

from omegaconf import OmegaConf


# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

# Timeout duration in seconds
TIMEOUT_DURATION = 30
user_timers = {}

def start_timeout(bot, chat_id, message_id):
    """Start a timeout for the menu."""
    timer = threading.Timer(TIMEOUT_DURATION, timeout_handler, args=(chat_id, message_id, bot))
    timer.start()
    user_timers[chat_id] = timer

def cancel_timeout(chat_id):
    """Cancel an active timeout."""
    if chat_id in user_timers:
        user_timers[chat_id].cancel()
        del user_timers[chat_id]

def timeout_handler(chat_id, message_id, bot):
    """Handle menu timeout."""
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=strings["ru"].timeout
    )

    try:
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
    except Exception as e:
        print(f"Failed to remove reply markup: {e}")
        pass

