import logging
from telegram.ext import CallbackContext

def global_error_handler(update: object, context: CallbackContext) -> None:
    logging.exception("Error occurred:", exc_info=context.error)
    if update and getattr(update, "effective_chat", None):
        try:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ A minor error occurred, please try again."
            )
        except Exception:
            logging.exception("Failed to send error message to user.")
