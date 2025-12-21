import os
import logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

import g4f
from PyPDF2 import PdfReader
import csv
from io import StringIO


async def pdf_to_csv_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("❌ Sirf PDF file bheje")
        return

    file = await document.get_file()
    pdf_path = f"/tmp/{document.file_name}"
    await file.download_to_drive(pdf_path)

    # 🔹 PDF → Text
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    if not text.strip():
        await update.message.reply_text("❌ PDF me readable text nahi mila")
        return

    await update.message.reply_text("⏳ PDF analyze ho rahi hai...")

    # 🔹 g4f AI call
    prompt = f"""
    Neeche diye gaye text se MCQ ko CSV format me convert karo.

    Format:
    Question,Option A,Option B,Option C,Option D,Answer,Description

    Rules:
    - Answer A/B/C/D me ho
    - Description 200 characters se kam
    - Extra text mat likhna

    TEXT:
    {text}
    """

    response = g4f.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    csv_text = response

    # 🔹 CSV file create
    csv_file = StringIO()
    csv_file.write(csv_text)
    csv_file.seek(0)

    await update.message.reply_document(
        document=csv_file,
        filename="converted_mcq.csv",
        caption="✅ PDF → CSV conversion complete"
    )

    os.remove(pdf_path)


def setup_pdf_to_csv_handlers(application):
    application.add_handler(
        MessageHandler(filters.Document.PDF, pdf_to_csv_handler)
    )
