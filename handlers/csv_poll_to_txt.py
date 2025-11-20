import csv
import io
import os
import tempfile
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters


async def start_csv_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📂 Send a *CSV file* or paste CSV-style text.\n"
        "I will convert it into `.txt` MCQ format.",
        parse_mode="Markdown"
    )


def convert_csv_to_text(reader):
    output = io.StringIO()
    for idx, row in enumerate(reader, start=1):
        if isinstance(row, dict):
            q = row.get('Question', '').strip()
            a = row.get('Option A', '').strip()
            b = row.get('Option B', '').strip()
            c = row.get('Option C', '').strip()
            d = row.get('Option D', '').strip()
            ans = row.get('Answer', '').strip()
            desc = row.get('Description', '').strip() or '@SecondCoaching'
        else:
            q, a, b, c, d, ans, *desc = row + [""] * (7 - len(row))
            desc = desc[0].strip() if desc else "@SecondCoaching"

        output.write(f"{idx}. {q}\n")
        output.write(f"A. {a}\nB. {b}\nC. {c}\nD. {d}\n")
        output.write(f"Answer: {ans}\n")
        output.write(f"{desc or '@SecondCoaching'}\n\n")

    return output.getvalue()


async def handle_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    csv_path = tempfile.mktemp(suffix=".csv")
    txt_path = tempfile.mktemp(suffix=".txt")
    await file.download_to_drive(csv_path)

    with open(csv_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    try:
        f = io.StringIO(content)
        reader = csv.DictReader(f)
        if not reader.fieldnames or "Question" not in reader.fieldnames[0]:
            f.seek(0)
            reader = csv.reader(f)
        text_output = convert_csv_to_text(reader)
    except Exception:
        f = io.StringIO(content)
        text_output = convert_csv_to_text(csv.reader(f))

    with open(txt_path, "w", encoding="utf-8") as out:
        out.write(text_output)

    await update.message.reply_document(open(txt_path, "rb"))

    os.remove(csv_path)
    os.remove(txt_path)


async def handle_text_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get("mcq_mode"):
        return  # ignore text when MCQ converter is running

    text = update.message.text.strip()

    if "," not in text:
        return

    txt_path = tempfile.mktemp(suffix=".txt")

    reader = csv.reader(io.StringIO(text))
    text_output = convert_csv_to_text(reader)

    with open(txt_path, "w", encoding="utf-8") as out:
        out.write(text_output)

    await update.message.reply_document(open(txt_path, "rb"))
    os.remove(txt_path)


async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll = update.message.poll
    if not poll or poll.type != "quiz":
        return

    txt_file = tempfile.mktemp(suffix=".txt")
    with open(txt_file, "w", encoding="utf-8") as out:
        out.write(f"1. {poll.question}\n")
        for i, opt in enumerate(poll.options):
            out.write(f"{chr(65+i)}. {opt.text}\n")

        correct = chr(65 + poll.correct_option_id)
        out.write(f"Answer: {correct}\n@SecondCoaching\n\n")

    await update.message.reply_document(open(txt_file, "rb"))
    os.remove(txt_file)


def setup_csv_poll_handlers(app):
    app.add_handler(CommandHandler("csvpoll", start_csv_poll))
    app.add_handler(MessageHandler(filters.Document.FileExtension("csv"), handle_csv))
    app.add_handler(MessageHandler(filters.POLL, handle_poll))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_csv))
