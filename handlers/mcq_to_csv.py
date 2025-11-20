import asyncio
import logging
from io import StringIO
from telegram import Update
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler,
    filters, ConversationHandler
)

import requests

logging.basicConfig(level=logging.INFO)

COLLECT_MCQS = range(1)   # Only 1 state now (no ASK_CUSTOM)

def clean_csv_text(text: str) -> str:
    text = text.replace("```csv", "").replace("```", "").strip()
    while text.endswith(("}", "]")):
        text = text[:-1].strip()
    return text

def convert_to_csv_via_ai_sync(text: str, extra_instruction: str = "") -> str:
    prompt = f"""
Convert the following MCQs into proper CSV format with headers:
"Question","Option A","Option B","Option C","Option D","Answer","Description"

Rules:
- Ignore numbering
- Use A/B/C/D only
- Description max 240 characters

MCQs:
{text}
"""

    try:
        url = "https://api.deepinfra.com/v1/openai/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer xkFIN7Nxr9hueQUIKZCH3tW9PLQxZsHC"
        }

        payload = {
            "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }

        res = requests.post(url, headers=headers, json=payload, timeout=30)

        if res.ok:
            return clean_csv_text(res.json()["choices"][0]["message"]["content"].strip())
        return "Error generating CSV."

    except Exception as e:
        return f"Error: {e}"

async def convert_to_csv_via_ai(text: str) -> str:
    return await asyncio.to_thread(convert_to_csv_via_ai_sync, text)


# ------------------ HANDLERS ------------------

async def mcq_csv_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 MCQ to CSV Converter Ready!\nUse /convert to start.")


async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mcqs"] = []
    await update.message.reply_text("✏️ Send MCQs (max 4 messages). Send /done when finished.")
    return COLLECT_MCQS


async def handle_mcq_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mcqs = context.user_data.get("mcqs", [])

    if len(mcqs) >= 4:
        await update.message.reply_text("⚠️ Limit reached (4). Send /done.")
        return COLLECT_MCQS

    mcqs.append(update.message.text.strip())
    context.user_data["mcqs"] = mcqs

    await update.message.reply_text(f"📝 Saved ({len(mcqs)}/4). Send /done.")
    return COLLECT_MCQS


async def process_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mcqs = context.user_data.get("mcqs", [])

    if not mcqs:
        await update.message.reply_text("❌ No MCQs found. Start again with /convert.")
        return ConversationHandler.END

    await update.message.reply_text("🤖 Converting...")

    csv_text = await convert_to_csv_via_ai("\n\n".join(mcqs))

    header = "Question,Option A,Option B,Option C,Option D,Answer,Description"
    lines = csv_text.strip().splitlines()

    if lines and "Question" in lines[0]:
        lines = lines[1:]

    lines.insert(0, header)

    file = StringIO("\n".join(lines))
    file.name = "mcqs.csv"

    await update.message.reply_document(file)
    await update.message.reply_text("✅ CSV Ready!")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


def add_mcq_csv_handlers(app):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("convert", convert_command)],
        states={
            COLLECT_MCQS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mcq_text),
                CommandHandler("done", process_done),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("mcqcsv", mcq_csv_start))
    app.add_handler(conv_handler)
