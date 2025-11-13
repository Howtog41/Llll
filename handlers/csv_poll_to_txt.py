import csv
import os
import tempfile
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters


# ✅ /start command
async def start_csv_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📂 Send a *CSV file* or an *Anonymous Quiz Poll*.\n"
        "I will convert it into a `.txt` file format.",
        parse_mode="Markdown"
    )


async def handle_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    csv_file = tempfile.mktemp(suffix=".csv")
    txt_file = tempfile.mktemp(suffix=".txt")

    await file.download_to_drive(csv_file)

    with open(csv_file, "r", encoding="utf-8-sig") as f, open(txt_file, "w", encoding="utf-8") as out:
        reader = csv.DictReader(f)

        for idx, row in enumerate(reader, start=1):
            # Convert all keys to lowercase for flexible matching
            row_lower = {k.strip().lower(): v for k, v in row.items()}

            q = row_lower.get("question", "")
            a = row_lower.get("option a", "")
            b = row_lower.get("option b", "")
            c = row_lower.get("option c", "")
            d = row_lower.get("option d", "")
            ans = row_lower.get("answer", "")
            desc = row_lower.get("description", "")

            out.write(f"{idx}. {q}\n")
            out.write(f"A. {a}\n")
            out.write(f"B. {b}\n")
            out.write(f"C. {c}\n")
            out.write(f"D. {d}\n")
            out.write(f"{ans}\n")
            out.write(f"{desc}\n\n")

    await update.message.reply_document(open(txt_file, "rb"))
    os.remove(csv_file)
    os.remove(txt_file)



# ✅ Handle Poll → TXT
async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll = update.message.poll
    if not poll or poll.type != "quiz":
        return

    txt_file = tempfile.mktemp(suffix=".txt")
    with open(txt_file, "w", encoding="utf-8") as out:
        out.write(f"1. {poll.question}\n")
        for i, opt in enumerate(poll.options):
            out.write(f"{chr(65+i)}. {opt.text}\n")
        out.write(f"{poll.correct_option_id + 1}\n\n")

    await update.message.reply_document(open(txt_file, "rb"))
    os.remove(txt_file)


# ✅ Export handler registration function
def setup_csv_poll_handlers(application):
    application.add_handler(CommandHandler("csvpoll", start_csv_poll))
    application.add_handler(MessageHandler(filters.Document.FileExtension("csv"), handle_csv))
    application.add_handler(MessageHandler(filters.POLL, handle_poll))
