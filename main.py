import logging
from telegram.ext import (

    Application, CommandHandler, ConversationHandler,

    CallbackQueryHandler, MessageHandler, filters

)

from handlers.start_handler import start, help_menu
from handlers.authorization_handler import authorize
from handlers.myplan import myplan

from config import TOKEN


def main():
    application = Application.builder().token(TOKEN).build()

    # ✅ Only required handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("authorize", authorize))
    application.add_handler(CommandHandler("myplan", myplan))
    application.add_handler(CallbackQueryHandler(help_menu, pattern="^help_menu$"))
    logging.info("🚀 Bot started successfully!")
    application.run_polling()


if __name__ == "__main__":
    print("Bot is running...")
    main()
