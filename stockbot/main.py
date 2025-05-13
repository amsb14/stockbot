import os
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler
from stockbot.handlers.commands import start, status, grant_premium, help_command, refresh_cf_db, refresh_is_db
from stockbot.handlers.callbacks import button
from stockbot.handlers.base import with_subscription_check, start_activation, handle_activation_code, cancel_activation
from stockbot.handlers.errors import global_error_handler
from stockbot.handlers import messages

from apscheduler.schedulers.background import BackgroundScheduler
from stockbot.services.subscription import reset_daily_usage
def main() -> None:
    updater = Updater(os.getenv("BOT_TOKEN"))
    dispatcher = updater.dispatcher

    # run in Asia/Riyadh at 00:00
    scheduler = BackgroundScheduler(timezone="Asia/Riyadh")
    scheduler.add_job(
        reset_daily_usage,
        trigger="cron",
        hour=0,
        minute=0,
        # minute="*/2", # reset every two mintues for testing
        id="daily_usage_reset"
    )
    scheduler.start()


    # Activation Conversation
    activation_conv = ConversationHandler(
        entry_points=[CommandHandler("activate", start_activation)],
        states={
            1: [MessageHandler(Filters.text & ~Filters.command, handle_activation_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel_activation)],
        allow_reentry=True,
    )
    dispatcher.add_handler(activation_conv)

    # Other command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("status", status))
    dispatcher.add_handler(CommandHandler("grant_premium", grant_premium))
    dispatcher.add_handler(CallbackQueryHandler(button, run_async=True))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("refresh_cf_db", refresh_cf_db, run_async=True))
    dispatcher.add_handler(CommandHandler("refresh_is_db", refresh_is_db, run_async=True))

    # General message handler
    dispatcher.add_handler(
        MessageHandler(
            (Filters.text & ~Filters.command)
            | (Filters.command & Filters.regex(r"^/[A-Za-z0-9\.]{1,10}$")),
            messages.handle_message,
        )
    )

    # Set the Top-Level Command Menu
    updater.bot.set_my_commands([
        ("start", "🔄 ابدأ البوت وأظهر القائمة الرئيسية"),
        ("status", "📊 اعرض حالة اشتراكك الحالية"),
        ("activate", "🔑 فعّل اشتراك بريميوم باستخدام الكود"),
        ("help", "📚 تعليمات ومساعدة حول استخدام البوت"),
    ])

    dispatcher.add_error_handler(global_error_handler)

    updater.start_polling()
    # (Scheduler will keep running in background)
    updater.idle()

if __name__ == '__main__':
    main()
