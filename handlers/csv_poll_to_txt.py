import csv
import os
import tempfile
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters


# ✅ /csvpoll command
async def start_csv_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📂 Send a *CSV file* or an *Anonymous Quiz Poll*.\n"
        "I will convert it into a `.txt` file format.",
        parse_mode="Markdown"
    )


# ✅ CSV → TXT
async def handle_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    csv_file = tempfile.mktemp(suffix=".csv")
    txt_file = tempfile.mktemp(suffix=".txt")

    await file.download_to_drive(csv_file)

    with open(csv_file, "r", encoding="utf-8") as f, open(txt_file, "w", encoding="utf-8") as out:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            out.write(f"{idx}. {row.get('Question', row.get('question', '')).strip()}\n")
            out.write(f"A. {row.get('Option A', row.get('A', '')).strip()}\n")
            out.write(f"B. {row.get('Option B', row.get('B', '')).strip()}\n")
            out.write(f"C. {row.get('Option C', row.get('C', '')).strip()}\n")
            out.write(f"D. {row.get('Option D', row.get('D', '')).strip()}\n")
            out.write(f"Answer: {row.get('Answer', row.get('answer', '')).strip()}\n")
            out.write(f"{row.get('Description', row.get('description', '@SecondCoaching')).strip()}\n\n")

    await update.message.reply_document(open(txt_file, "rb"))

    os.remove(csv_file)
    os.remove(txt_file)


# ✅ Poll → TXT
async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll = update.message.poll
    if not poll or poll.type != "quiz":
        return

    txt_file = tempfile.mktemp(suffix=".txt")
    with open(txt_file, "w", encoding="utf-8") as out:
        out.write(f"1. {poll.question}\n")
        for i, opt in enumerate(poll.options):
            out.write(f"{chr(65+i)}. {opt.text}\n")

        correct_letter = chr(65 + poll.correct_option_id)
        out.write(f"Answer: {correct_letter}\n")
        out.write("@SecondCoaching\n\n")

    await update.message.reply_document(open(txt_file, "rb"))
    os.remove(txt_file)


# ✅ Handler setup
def setup_csv_poll_handlers(application):
    application.add_handler(CommandHandler("csvpoll", start_csv_poll))
    application.add_handler(MessageHandler(filters.Document.FileExtension("csv"), handle_csv))
    application.add_handler(MessageHandler(filters.POLL, handle_poll))
