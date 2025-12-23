import os
import re
import csv
import json
import logging
from io import StringIO

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

import g4f
from PyPDF2 import PdfReader

# ================== STATES ==================
WAIT_PDF, ASK_SPLIT, ASK_PAGE_MODE, WAIT_PAGE_RANGE = range(4)


# ================== START COMMAND ==================
async def start_pdf2csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📄 PDF bheje\n\n"
        "⚠️ Sirf is command ke baad PDF accept hoga"
    )
    return WAIT_PDF


# ================== RECEIVE PDF ==================
async def receive_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document

    if not doc.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("❌ Sirf PDF file allowed")
        return WAIT_PDF

    file = await doc.get_file()
    path = f"/tmp/{doc.file_name}"
    await file.download_to_drive(path)

    context.user_data["pdf_path"] = path

    keyboard = [
        [
            InlineKeyboardButton("✅ Haan (Split)", callback_data="split_yes"),
            InlineKeyboardButton("❌ Nahi", callback_data="split_no"),
        ]
    ]

    await update.message.reply_text(
        "Kya aap PDF pages ko Left / Right 2 part me todna chahte ho?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return ASK_SPLIT


# ================== SPLIT CHOICE ==================
async def handle_split(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["split"] = query.data == "split_yes"

    keyboard = [
        [
            InlineKeyboardButton("📄 First 4 Pages", callback_data="first"),
            InlineKeyboardButton("🔢 Page Range", callback_data="range"),
        ]
    ]

    await query.message.reply_text(
        "Pure PDF convert karna hai ya specific page range?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return ASK_PAGE_MODE


# ================== PAGE MODE ==================
async def handle_page_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "first":
        context.user_data["pages"] = (1, 4)
        await process_pdf(update, context)
        return ConversationHandler.END

    await query.message.reply_text(
        "Page range bheje (example: 2-5, max 4 pages)"
    )
    return WAIT_PAGE_RANGE


# ================== PAGE RANGE ==================
async def handle_page_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    match = re.match(r"(\d+)\s*-\s*(\d+)", text)
    if not match:
        await update.message.reply_text("❌ Galat format (2-5)")
        return WAIT_PAGE_RANGE

    start, end = map(int, match.groups())
    if end < start or (end - start + 1) > 4:
        await update.message.reply_text("❌ Max 4 pages allowed")
        return WAIT_PAGE_RANGE

    context.user_data["pages"] = (start, end)
    await process_pdf(update, context)
    return ConversationHandler.END


# ================== CORE PROCESS ==================
async def process_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("⏳ PDF process ho rahi hai...")

    pdf_path = context.user_data["pdf_path"]
    split = context.user_data["split"]
    start, end = context.user_data["pages"]

    reader = PdfReader(pdf_path)
    extracted_text = ""

    for i in range(start - 1, min(end, len(reader.pages))):
        page_text = reader.pages[i].extract_text() or ""

        if split:
            mid = len(page_text) // 2
            page_text = page_text[:mid] + "\n" + page_text[mid:]

        extracted_text += page_text + "\n"

    if not extracted_text.strip():
        await update.effective_message.reply_text("❌ Text extract nahi ho paya")
        return

    # ================== AI PROMPT ==================
    prompt = f"""
Return ONLY valid JSON array.

Each item format:
{{
  "question": "",
  "options": ["A","B","C","D"],
  "answer": "A",
  "description": ""
}}

Rules:
- No extra text
- Answer only A/B/C/D
- Description under 200 characters
- Commas allowed inside text

TEXT:
{extracted_text}
"""

    try:
        ai_response = g4f.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
        )

        data = json.loads(ai_response)

    except Exception as e:
        logging.error(e)
        await update.effective_message.reply_text("❌ AI response error")
        return

    # ================== CSV SAFE WRITE ==================
    output = StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    writer.writerow(
        ["Question", "Option A", "Option B", "Option C", "Option D", "Answer", "Description"]
    )

    for item in data:
        writer.writerow([
            item["question"],
            item["options"][0],
            item["options"][1],
            item["options"][2],
            item["options"][3],
            item["answer"],
            item["description"],
        ])

    output.seek(0)

    await update.effective_message.reply_document(
        document=output,
        filename="pdf_to_csv_mcq.csv",
        caption="✅ PDF → CSV conversion complete",
    )

    os.remove(pdf_path)


# ================== SETUP HANDLER ==================
def setup_pdf_to_csv_handlers(application):
    conv = ConversationHandler(
        entry_points=[CommandHandler("pdf2csv", start_pdf2csv)],
        states={
            WAIT_PDF: [MessageHandler(filters.Document.PDF, receive_pdf)],
            ASK_SPLIT: [CallbackQueryHandler(handle_split)],
            ASK_PAGE_MODE: [CallbackQueryHandler(handle_page_mode)],
            WAIT_PAGE_RANGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_page_range)
            ],
        },
        fallbacks=[],
    )

    application.add_handler(conv)
