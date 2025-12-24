import os
import logging
import numpy as np
import easyocr
import cv2

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from pdf2image import convert_from_path
from PIL import Image

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN", "")

DPI = 500
# ==========================================

logging.basicConfig(level=logging.ERROR)

reader = easyocr.Reader(['hi'], gpu=False, verbose=False)

def preprocess_image(pil_image):
    """
    Image cleaning for better Hindi OCR
    """
    img = np.array(pil_image)

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

    _, thresh = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return thresh


async def pdf_to_hindi_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        document = update.message.document

        if not document.file_name.lower().endswith(".pdf"):
            await update.message.reply_text("❌ Sirf PDF bheje")
            return

        chat_id = update.message.chat_id
        pdf_path = f"input_{chat_id}.pdf"
        txt_path = f"output_{chat_id}.txt"

        tg_file = await document.get_file()
        await tg_file.download_to_drive(pdf_path)

        await update.message.reply_text("📄 PDF → Image → OCR start ho gaya...")

        images = convert_from_path(pdf_path, dpi=DPI)

        full_text = ""

        for page_no, pil_img in enumerate(images, start=1):
            processed_img = preprocess_image(pil_img)

            results = reader.readtext(processed_img, detail=0)

            full_text += f"\n========== Page {page_no} ==========\n"
            for text in results:
                full_text += text + "\n"

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        await update.message.reply_document(
            document=open(txt_path, "rb"),
            caption="✅ Hindi TXT ready (clean OCR)"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if os.path.exists(txt_path):
            os.remove(txt_path)


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.Document.PDF, pdf_to_hindi_txt))

    print("🤖 Bot Running...")
    app.run_polling()
