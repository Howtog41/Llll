import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from handlers.pdf_to_csv import setup_pdf_to_csv_handlers

from handlers.start_handler import start, help_menu
from handlers.authorization_handler import authorize
from handlers.myplan import myplan
from handlers.csv_poll_to_txt import setup_csv_poll_handlers
from handlers.mcq_to_csv import add_mcq_csv_handlers

from config import TOKEN


def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("authorize", authorize))
    application.add_handler(CommandHandler("myplan", myplan))
    application.add_handler(CallbackQueryHandler(help_menu, pattern="^help_menu$"))

    # CSV → TXT + Poll system
    setup_csv_poll_handlers(application)

    # MCQ → CSV system
    add_mcq_csv_handlers(application)

    # PDF → CSV (AI based)
    setup_pdf_to_csv_handlers(application)


    logging.info("🚀 Bot started successfully!")
    application.run_polling()


if __name__ == "__main__":
    print("Bot is running...")
    main()
