import os
import logging
import numpy as np
import easyocr

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

from pdf2image import convert_from_path

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN", "")

DPI = 400
# ==========================================

logging.basicConfig(level=logging.ERROR)

# EasyOCR Hindi Reader
reader = easyocr.Reader(['hi'], gpu=False, verbose=False)

async def pdf_to_hindi_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        document = update.message.document

        if not document.file_name.lower().endswith(".pdf"):
            await update.message.reply_text("❌ Sirf PDF file bheje")
            return

        chat_id = update.message.chat_id
        pdf_path = f"input_{chat_id}.pdf"
        txt_path = f"output_{chat_id}.txt"

        tg_file = await document.get_file()
        await tg_file.download_to_drive(pdf_path)

        await update.message.reply_text("📄 PDF process ho rahi hai, wait karein...")

        images = convert_from_path(pdf_path, dpi=DPI)

        full_text = ""

        for page_no, img in enumerate(images, start=1):
            img_np = np.array(img)
            results = reader.readtext(img_np)

            full_text += f"\n===== Page {page_no} =====\n"
            for _, text, _ in results:
                full_text += text + "\n"

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        await update.message.reply_document(
            document=open(txt_path, "rb"),
            caption="✅ Hindi TXT ready"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if os.path.exists(txt_path):
            os.remove(txt_path)

# ================= MAIN =================
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(
        MessageHandler(filters.Document.PDF, pdf_to_hindi_txt)
    )

    print("🤖 Bot Running...")
    app.run_polling()
