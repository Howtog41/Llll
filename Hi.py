import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)
from pdf2image import convert_from_path
import easyocr

BOT_TOKEN = "YOUR_BOT_TOKEN"

reader = easyocr.Reader(['hi'], gpu=False)

async def pdf_to_hindi_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document

    if not file.file_name.endswith(".pdf"):
        await update.message.reply_text("❌ Sirf PDF bheje")
        return

    pdf_path = f"input_{update.message.chat_id}.pdf"
    txt_path = f"output_{update.message.chat_id}.txt"

    telegram_file = await file.get_file()
    await telegram_file.download_to_drive(pdf_path)

    await update.message.reply_text("📄 PDF process ho rahi hai...")

    images = convert_from_path(pdf_path, dpi=300)

    full_text = ""

    for img in images:
        result = reader.readtext(img)
        for _, text, _ in result:
            full_text += text + "\n"

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    await update.message.reply_document(
        document=open(txt_path, "rb"),
        caption="✅ Hindi TXT ready"
    )

    os.remove(pdf_path)
    os.remove(txt_path)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.Document.PDF, pdf_to_hindi_txt))

    print("🤖 Bot Running...")
    app.run_polling()
